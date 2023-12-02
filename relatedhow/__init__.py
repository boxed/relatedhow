import json
from collections import defaultdict
from datetime import datetime
from itertools import groupby
from time import sleep
from urllib.parse import urlencode

import os
import requests
from os.path import exists
from tqdm import tqdm

from subprocess import check_output

from tri_struct import Struct

biota_pk = 2382443


class FooException(Exception):
    pass


def line_count(filename):
    return int(check_output(["/usr/bin/wc", "-l", filename]).split()[0])


def wikidata_id_as_int(s):
    prefix = '<http://www.wikidata.org/entity/Q'
    suffix = '>'
    if s.startswith(prefix):
        assert s.endswith(suffix), repr(s)
        return int(s[len(prefix):-len(suffix)])
    elif s.startswith('Q'):
        return int(s[1:])
    else:
        assert False, f'Unsupported format for wikidata_as_int: "{s}"'


def fix_text(s):
    return s.encode('ascii', errors='ignore').decode('ascii')


def read_csv(filename):
    # I know the format here, so I don't need to use the csv module. This gives me a bit higher performance
    print('load %s' % filename)
    num_lines = line_count(filename)
    with open(filename, newline='') as csvfile:
        csvfile.readline()  # skip header line
        for row in tqdm(csvfile.readlines(), total=num_lines):
            row = row.split('\t')
            yield wikidata_id_as_int(row[0]), row[1].strip()


class FakeTaxon(Struct):
    def __hash__(self):
        return hash(self.pk)


class TaxonsDict(defaultdict):
    def __missing__(self, key):
        from relatedhow.viewer.models import Taxon
        # t = Taxon(pk=key)
        t = FakeTaxon(pk=key, name=None, parent=None, rank=None, english_name=None, image=None, alias=None, wikipedia_title=None)
        t._children = set()
        t._parents = set()
        self[key] = t
        return t


def create_taxon_from_struct(x):
    from relatedhow.viewer.models import Taxon
    kw = {k: v for k, v in x.items() if not k.startswith('_')}
    p = kw.pop('parent')
    if p:
        kw['parent_id'] = p.pk
    return Taxon(**kw)


def q_id_to_pk(s):
    return int(s[1:])  # [1:] is to drop the Q prefix


def claims_values(c, k):
    try:
        return [x['mainsnak']['datavalue']['value'] for x in c.get(k, [])]
    except KeyError:
        return []


def import_wikidata():
    taxon_by_pk = TaxonsDict()
    pks_of_taxons_with_ambiguous_parents = set()

    init(taxon_by_pk)
    # fix_obsolete_pks = {}  # TODO: use these!
    # read_synonyms(fix_obsolete_pks)
    load_taxon_data(taxon_by_pk)
    set_non_ambigous_parents(pks_of_taxons_with_ambiguous_parents, taxon_by_pk)
    fix_ambigous_parents_until_stable(pks_of_taxons_with_ambiguous_parents, taxon_by_pk)
    break_trivial_loops(taxon_by_pk)
    write_parentless_taxons(taxon_by_pk)
    write_loops(pks_of_taxons_with_ambiguous_parents, taxon_by_pk)
    set_children(taxon_by_pk)
    set_rank_and_num_children(taxon_by_pk)
    remove_non_biota(taxon_by_pk)
    store_to_db(taxon_by_pk)

    # TODO: load images.csv


def init(taxon_by_pk):
    initial_taxons = [
        FakeTaxon(rank=None, parent=None, pk=2382443, name='Biota', english_name='Life'),
        FakeTaxon(rank=None, parent=None, pk=23012932, name='Ichnofossils'),
        FakeTaxon(rank=None, parent=None, pk=24150684, name='Agmata'),
        FakeTaxon(rank=None, parent=None, pk=5381701, name='Eohostimella'),
        FakeTaxon(rank=None, parent=None, pk=23832652, name='Anucleobionta'),
        FakeTaxon(rank=None, parent=None, pk=21078601, name='Yelovichnus'),
        FakeTaxon(rank=None, parent=None, pk=35107213, name='Rhizopodea'),
        FakeTaxon(rank=None, parent=None, pk=46987746, name='Pan-Angiospermae'),
        FakeTaxon(rank=None, parent=None, pk=14868864, name='Enoplotrupes'),
        FakeTaxon(rank=None, parent=None, pk=17290456, name='Erythrophyllum'),
        FakeTaxon(rank=None, parent=None, pk=14868878, name='Chelotrupes'),
    ]
    for t in initial_taxons:
        taxon_by_pk[t.pk] = t
        t._children = set()
        t._parents = set()


def read_synonyms(fix_obsolete_pks):
    for pk1, v in read_csv('synonyms.csv'):
        pk2 = wikidata_id_as_int(v)
        use_pk, obsolete_pk = sorted([pk1, pk2])
        fix_obsolete_pks[obsolete_pk] = use_pk


def store_to_db(taxon_by_pk):
    print('Clearing database')
    from django.db import connection
    # cursor = connection.cursor()
    # cursor.execute('TRUNCATE TABLE `viewer_taxon`')

    print('...inserting %s clades' % len(taxon_by_pk))
    from relatedhow.viewer.models import Taxon
    for k, group in groupby(sorted(taxon_by_pk.values(), key=lambda x: x.rank or 0), key=lambda x: x.rank or 0):
        group = [create_taxon_from_struct(x) for x in group]
        start = datetime.now()
        print('inserting rank %s (%s items)' % (k, len(group)), end='', flush=True)
        Taxon.objects.bulk_create(group, batch_size=100)
        print(' .. took %s' % (datetime.now() - start))


def remove_non_biota(taxon_by_pk):
    print('remove non-biota trees')
    non_biota_tree_roots = [t for t in taxon_by_pk.values() if t.pk != biota_pk and t.parent is None]

    def remove_tree(t):
        for child in t._children:
            remove_tree(child)
        del taxon_by_pk[t.pk]

    for t in non_biota_tree_roots:
        if t.name and not t.name.startswith('Category'):
            print('\t', t.name, t.pk)
        remove_tree(t)


def set_rank_and_num_children(taxon_by_pk):
    print('set rank, and number of children (direct and indirect)')

    def get_count(t, rank):
        t.rank = rank
        t.number_of_direct_children = len(t._children)
        t.number_of_direct_and_indirect_children = sum(get_count(c, rank=rank + 1) for c in t._children) + t.number_of_direct_children
        return t.number_of_direct_and_indirect_children

    biota = taxon_by_pk[biota_pk]
    get_count(biota, rank=0)


def set_children(taxon_by_pk):
    print('set children')
    for taxon in tqdm(taxon_by_pk.values()):
        if taxon.parent:
            taxon.parent._children.add(taxon)


def write_loops(pks_of_taxons_with_ambiguous_parents, taxon_by_pk):
    print('write loops')
    if pks_of_taxons_with_ambiguous_parents:
        loop_roots = [pk for pk in pks_of_taxons_with_ambiguous_parents if all(p.pk > pk for p in taxon_by_pk[pk]._parents)]
        with open('loop_roots.txt', 'w') as f:
            f.write('\n'.join(str(x) for x in loop_roots))


def write_parentless_taxons(taxon_by_pk):
    print('write parentless taxons')
    taxons_with_no_parent = [taxon for taxon in taxon_by_pk.values() if not taxon._parents]
    with open('no_parent_taxons.txt', 'w') as f:
        f.write('\n'.join(str(x.pk) for x in taxons_with_no_parent))


def break_trivial_loops(taxon_by_pk):
    print('break trivial loops')
    for taxon in tqdm(taxon_by_pk.values()):
        if taxon.parent and taxon.parent.parent and taxon.parent.parent.pk == taxon.pk:
            taxon.parent = None


def fix_ambigous_parents_until_stable(pks_of_taxons_with_ambiguous_parents, taxon_by_pk):
    print('fix ambiguous parents, until stable (%s)' % len(pks_of_taxons_with_ambiguous_parents))
    while fix_ambiguous_parents(pks_of_taxons_with_ambiguous_parents, taxon_by_pk):
        continue


def fix_ambiguous_parents(pks_of_taxons_with_ambiguous_parents, taxon_by_pk):
    count = 0
    for pk in tqdm(pks_of_taxons_with_ambiguous_parents.copy()):
        taxon = taxon_by_pk[pk]

        def get_all_parents_or_raise(t):
            result = []
            orig = t
            while t._parents:
                if t.parent:
                    result.append(t.parent)
                else:
                    raise FooException('Still ambiguous')
                t = t.parent
            # handle cases where tree is not in biota
            if result and result[-1].pk != biota_pk:
                # print('\t%s is not related to biota' % orig.pk)
                return []
            return result

        try:
            taxon.parent = sorted(taxon._parents, key=lambda x: len(get_all_parents_or_raise(x)), reverse=True)[0]
            taxon._parents = {taxon.parent}
            pks_of_taxons_with_ambiguous_parents.remove(pk)
            count += 1
        except FooException:
            continue

    print('\t%s fixed, %s left' % (count, len(pks_of_taxons_with_ambiguous_parents)))
    return count


def set_non_ambigous_parents(pks_of_taxons_with_ambiguous_parents, taxon_by_pk):
    print('Set non-ambiguous parents')
    top_level = set()
    for taxon in tqdm(taxon_by_pk.values()):
        if len(taxon._parents) == 1:
            taxon.parent = list(taxon._parents)[0]
        elif len(taxon._parents) > 1:
            pks_of_taxons_with_ambiguous_parents.add(taxon.pk)
        elif len(taxon._parents) == 0:
            top_level.add(taxon.pk)
        else:
            assert False


def load_taxon_data(taxon_by_pk):
    print('load taxon_data.json')
    with open('taxon_data.json') as f:
        for line in tqdm(f, total=3490962):
            if line.endswith(',\n'):
                line = line[:-2]
            j = json.loads(line)
            claims = j['claims']
            taxon = taxon_by_pk[q_id_to_pk(j['id'])]
            try:
                taxon.alias = j['aliases']['en'][0]['value'].lower()
            except KeyError:
                pass
            try:
                taxon.name = j['labels']['en']['value'].lower()
            except KeyError:
                pass
            try:
                taxon.english_name = {x['language']: x['text'] for x in claims_values(claims, 'P1843')}['en'].lower()
                # print(j['id'], taxon.name, taxon.english_name)
            except KeyError:
                pass

            try:
                taxon.wikipedia_title = j['sitelinks']['enwiki']['title'].lower()
            except KeyError:
                pass
            taxon.name = taxon.name or taxon.alias or taxon.english_name or taxon.wikipedia_title
            taxon.image = claims_values(claims, 'P2716') or claims_values(claims, 'P18')
            if isinstance(taxon.image, list):
                if taxon.image:
                    taxon.image = taxon.image[0]
                else:
                    taxon.image = None
            taxon._parents = {taxon_by_pk[x['numeric-id']] for x in claims_values(claims, 'P171')}


def clean_name(name):
    name = name.strip()
    if name.endswith('@en'):
        if name.startswith('"'):
            assert name.endswith('"@en')
            name = name[1:-len('"@en')]
        else:
            assert name.endswith('@en')
            name = name[:-len('@en')]
    return name.replace('\t', ' ')


def download(select, filename):
    if exists(filename):
        print('Using existing file %s' % filename)
        return

    print('Downloading %s' % filename)
    result = download_contents(filename, select)

    with open(filename, 'w') as f:
        f.write(result)


def download_contents(filename, select):
    result = requests.get('https://query.wikidata.org/sparql?%s' % urlencode([('query', select)]), headers={'Accept': 'text/tab-separated-values', 'User-agent': 'relatedhow/0.0 (https://github.com/boxed/related_how; boxed@killingar.net) data extraction bot'}).text
    if '\tat ' in result:
        print('Error with download of %s (1), got %sMB' % (filename, len(result) / (1024 * 10424)), result[-500:])
        exit(1)
    if '</html>' in result:
        print('Error with download of %s (2), got %sMB' % (filename, len(result) / (1024 * 10424)), result[-500:])
        exit(1)
    sleep(0.1)
    return result


def fix_base_of_tree():
    from relatedhow.viewer.models import Taxon
    luca = Taxon.objects.get(pk=2382443)

    if luca.name == 'LUCA':
        print('Already fixed base of tree')
        return

    print('Fixing base of tree')
    luca.english_name = 'Cellular life'
    luca.name = 'LUCA'
    luca.save()

    virus = Taxon.objects.get(pk=808)
    virus.parent.number_of_direct_children -= 1
    virus.parent.number_of_direct_and_indirect_children -= virus.number_of_direct_and_indirect_children + 1
    virus.parent.save()
    virus.parent = None
    virus.save()

    archea = Taxon.objects.get(pk=10872)

    eukaryotes = Taxon.objects.get(pk=19088)
    eukaryotes.parent.number_of_direct_children -= 1
    eukaryotes.parent.number_of_direct_and_indirect_children -= eukaryotes.number_of_direct_and_indirect_children + 1
    eukaryotes.parent = archea
    eukaryotes.save()

    archea.number_of_direct_children += 1
    archea.number_of_direct_and_indirect_children += eukaryotes.number_of_direct_and_indirect_children + 1
    archea.save()


# def translate_images_to_urls():
#     from relatedhow.viewer.models import Taxon
#     taxons = list(Taxon.objects.exclude(image__startswith='http').exclude(image=None))
#     for t in tqdm(taxons):
#         t.image = json.loads(requests.get(f'https://commons.wikimedia.org/w/api.php?action=query&format=json&formatversion=2&prop=imageinfo&iiprop=url&iiurlwidth=320&titles=File:{t.image}').text)['query']['pages'][0]['imageinfo'][0]['thumburl']
#         t.save()


def import_and_process():

    import_wikidata()
    # fast exit because we're using a lot of memory and cleaning that is silly
    os._exit(0)
