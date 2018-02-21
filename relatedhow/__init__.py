import csv
from collections import defaultdict
from itertools import groupby
from urllib.parse import urlencode

import os
import requests
from os.path import exists
from tqdm import tqdm

from subprocess import check_output

# TODO: Sarcopterygii (160830) should be below Osteichthyes (27207)

class FooException(Exception):
    pass


def line_count(filename):
    return int(check_output(["/usr/bin/wc", "-l", filename]).split()[0])


def wikidata_id_as_int(s):
    prefix = '<http://www.wikidata.org/entity/Q'
    suffix = '>'
    assert s.startswith(prefix), s
    assert s.endswith(suffix), s
    return int(s[len(prefix):-len(suffix)])


def fix_text(s):
    return s.encode('ascii', errors='ignore').decode('ascii')


def read_csv(filename):
    print('load %s' % filename)
    num_lines = line_count(filename)
    with open(filename, newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter='\t')
        next(reader)
        for row in tqdm(reader, total=num_lines):
            yield wikidata_id_as_int(row[0]), row[1]


class TaxonsDict(defaultdict):
    def __missing__(self, key):
        from relatedhow.viewer.models import Taxon
        t = Taxon(pk=key)
        t._children = set()
        t._parents = set()
        self[key] = t
        return t


def import_wikidata():
    from relatedhow.viewer.models import Taxon

    print('Clearing database')
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute('TRUNCATE TABLE `viewer_taxon`')

    initial_taxons = [
        Taxon(id=2382443, name='Biota', english_name='Life'),
        Taxon(id=23012932, name='Ichnofossils'),
        Taxon(id=24150684, name='Agmata'),
        Taxon(id=5381701, name='Eohostimella'),
        Taxon(id=23832652, name='Anucleobionta'),
        Taxon(id=21078601, name='Yelovichnus'),
        Taxon(id=35107213, name='Rhizopodea'),
        Taxon(id=46987746, name='Pan-Angiospermae'),
        Taxon(id=14868864, name='Enoplotrupes'),
        Taxon(id=17290456, name='Erythrophyllum'),
        Taxon(id=14868878, name='Chelotrupes'),
    ]

    taxon_by_pk = TaxonsDict()
    for t in initial_taxons:
        taxon_by_pk[t.pk] = t
        t._children = set()
        t._parents = set()

    pks_of_taxons_with_ambiguous_parents = set()

    for pk, v in read_csv('names.csv'):
        name = fix_text(v)
        if name:
            taxon_by_pk[pk].english_name = clean_name(name)

    for pk, v in read_csv('labels.csv'):
        name = fix_text(v)
        if name:
            taxon_by_pk[pk].english_name = clean_name(name)

    for pk, v in read_csv('taxons.csv'):
        name = fix_text(v)
        if name:
            taxon_by_pk[pk].name = name

    # def check_loop(pk, visited_pks=None):
    #     if visited_pks is None:
    #         visited_pks = []
    #     if pk in visited_pks:
    #         print('loop!', visited_pks, pk)
    #         exit(1)
    #     for p in taxon_by_pk[pk]._parents:
    #         check_loop(p.pk, visited_pks=visited_pks)

    for pk, v in read_csv('parent_taxons.csv'):
        if '_:' in v:
            continue
        parent_pk = wikidata_id_as_int(v)
        parent_taxon = taxon_by_pk[parent_pk]
        taxon = taxon_by_pk[pk]
        taxon._parents.add(parent_taxon)
        # check_loop(pk)

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

    print('fix ambiguous parents, until stable (%s)' % len(pks_of_taxons_with_ambiguous_parents))

    def fix_ambiguous_parents():
        count = 0
        for pk in tqdm(pks_of_taxons_with_ambiguous_parents.copy()):
            taxon = taxon_by_pk[pk]

            def get_all_parents_or_raise(t):
                result = []
                while t._parents:
                    if t.parent:
                        result.append(t.parent)
                    else:
                        raise FooException('Still ambiguous')
                    t = t.parent
                return result

            try:
                taxon.parent = sorted(taxon._parents, key=lambda x: len(get_all_parents_or_raise(x)), reverse=True)[0]
                taxon._parents = {taxon.parent}
                pks_of_taxons_with_ambiguous_parents.remove(pk)
                count += 1
            except FooException:
                continue

        print('\t%s fixed, %s left' % (count, len(pks_of_taxons_with_ambiguous_parents)))
        return len(pks_of_taxons_with_ambiguous_parents)

    while fix_ambiguous_parents():
        continue

    print('set children')
    for taxon in tqdm(taxon_by_pk.values()):
        if taxon.parent:
            taxon.parent._children.add(taxon)

    print('set number of children, direct and indirect')

    def get_count(t):
        t.number_of_direct_children = len(t._children)
        t.number_of_direct_and_indirect_children = sum(get_count(c) for c in t._children) + t.number_of_direct_children
        return t.number_of_direct_and_indirect_children

    biota = taxon_by_pk[2382443]
    get_count(biota)

    print('validating pks')
    for pk, taxon in taxon_by_pk.items():
        if pk != taxon.pk:
            print('invalid pk', pk, taxon)

    print('set ranks')

    for taxon in tqdm(taxon_by_pk.values()):
        taxon.rank = len(taxon.get_all_parents())

    print('...inserting %s clades' % len(taxon_by_pk))
    for k, group in groupby(sorted(taxon_by_pk.values(), key=lambda x: x.rank or 0), key=lambda x: x.rank or 0):
        group = list(group)
        print('inserting rank %s (%s items)' % (k, len(group)))
        for x in group:
            if len(x.get_all_parents()) != k:
                import ipdb; ipdb.set_trace()
        Taxon.objects.bulk_create(group, batch_size=100)


def clean_name(name):
    if name.endswith('@en'):
        if name.startswith('"'):
            assert name.endswith('"@en')
            name = name[1:-len('"@en')]
        else:
            assert name.endswith('@en')
            name = name[:-len('@en')]
    return name


def download(select, filename):
    if exists(filename):
        print('Using existing file %s' % filename)
        return

    print('Downloading %s' % filename)
    result = requests.get('https://query.wikidata.org/sparql?%s' % urlencode([('query', select)]), headers={'Accept': 'text/tab-separated-values'}).text
    if '\tat ' in result:
        print('Error with download of %s, got %sMB' % (filename, len(result) / (1024 * 10424)))
        exit(1)

    with open(filename, 'w') as f:
        f.write(result)


def import_and_process():
    download(
        filename='taxons.csv',
        select="""
            SELECT ?item ?taxonname WHERE {
              ?item wdt:P225 ?taxonname.
              FILTER (!isBLANK(?taxonname)).
            }
            """,
    )

    download(
        filename='parent_taxons.csv',
        select="""
            SELECT ?item ?parenttaxon WHERE {
              ?item p:P171 ?p171stm .
              ?p171stm ps:P171 ?parenttaxon .
            }
            """
    )

    download(
        filename='names.csv',
        select="""
            SELECT DISTINCT ?item ?label WHERE {
              ?item wdt:P31 wd:Q16521.
              ?item wdt:P1843 ?label. 
              FILTER (langMatches( lang(?label), "EN" ) )
            }
            """,
    )

    download(
        filename='labels.csv',
        select="""
            SELECT DISTINCT ?item ?itemLabel WHERE {
              ?item wdt:P31 wd:Q16521.
              ?item wdt:P225 ?taxonname.
              FILTER isBLANK(?taxonname) .
              SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
            }
            """,
    )

    import_wikidata()
    # fast exit because we're using a lot of memory and cleaning that is silly
    os._exit(0)
