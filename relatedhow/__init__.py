import csv
from itertools import groupby
from urllib.parse import urlencode
import requests
from os.path import exists
from tqdm import tqdm

from subprocess import check_output


def line_count(filename):
    return int(check_output(["wc", "-l", filename]).split()[0])


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
        reader = csv.DictReader(csvfile, delimiter='\t')
        for row in tqdm(reader, total=num_lines):
            yield row


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

    taxon_by_pk = {x.id: x for x in initial_taxons}
    pks_of_taxons_with_ambiguous_parents = set()

    for row in read_csv('names.csv'):
        name = fix_text(row['?label'])
        pk = wikidata_id_as_int(row['?item'])
        if pk not in taxon_by_pk:
            taxon_by_pk[pk] = Taxon(pk=pk)
        taxon_by_pk[pk].name = name

    for row in read_csv('labels.csv'):
        name = fix_text(row['?itemLabel'])
        pk = wikidata_id_as_int(row['?item'])
        if pk not in taxon_by_pk:
            taxon_by_pk[pk] = Taxon(pk=pk)
        taxon_by_pk[pk].english_name = clean_name(name)

    for row in read_csv('taxons.csv'):
        name = fix_text(row['?taxonname'])
        pk = wikidata_id_as_int(row['?item'])
        if pk not in taxon_by_pk:
            taxon_by_pk[pk] = Taxon(pk=pk)
        taxon_by_pk[pk].name = name

    for row in read_csv('parent_taxons.csv'):
        if '_:' in row['?parenttaxon']:
            continue
        pk = wikidata_id_as_int(row['?item'])
        parent_pk = wikidata_id_as_int(row['?parenttaxon'])
        if pk not in taxon_by_pk:
            taxon_by_pk[pk] = Taxon(pk=pk)
        if parent_pk not in taxon_by_pk:
            taxon_by_pk[parent_pk] = Taxon(pk=parent_pk)

        taxon_by_pk[pk].add_parent(parent_pk)

    print('set parents and (non-stored) children')

    for taxon in taxon_by_pk.values():
        taxon._children = set()

    for taxon in tqdm(taxon_by_pk.values()):
        if taxon.parents_string:
            parent_pk = int(taxon.parents_string.partition('\t')[0])
            parent_taxon = taxon_by_pk[parent_pk]
            taxon.parent = parent_taxon
            parent_taxon._children.add(taxon)
            if '\t' in taxon.parents_string:
                pks_of_taxons_with_ambiguous_parents.add(taxon.pk)

    print('set rank')

    def set_rank(taxon, rank):
        taxon.rank = rank
        for child in taxon._children:
            set_rank(child, rank + 1)

    for taxon in tqdm(taxon_by_pk.values()):
        if taxon.rank is None and taxon.parent is None:
            set_rank(taxon, rank=0)

    print('fix ambiguous parents, until stable (%s)' % len(pks_of_taxons_with_ambiguous_parents))
    multiple_parents = set()

    def fix_ambiguous_parents():
        multiple_parents.clear()
        count = 0
        for pk in tqdm(pks_of_taxons_with_ambiguous_parents):
            taxon = taxon_by_pk[pk]
            parents = {taxon_by_pk[int(parent_pk)] for parent_pk in taxon.parents_string.split('\t')}
            max_rank = max([x.rank for x in parents])
            relevant_parents = [p for p in parents if p.rank == max_rank]
            if len(relevant_parents) > 1:
                multiple_parents.add(taxon)
            if taxon.parent != relevant_parents[0]:
                taxon.parent = relevant_parents[0]
                set_rank(taxon, rank=max_rank + 1)
                count += 1
        return count

    while fix_ambiguous_parents():
        continue

    for taxon in multiple_parents:
        print('Warning: %s has multiple parents with the same rank' % taxon)

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

    print('Validating parent')

    print('...inserting %s clades' % len(taxon_by_pk))
    for k, group in groupby(sorted(taxon_by_pk.values(), key=lambda x: x.rank or 0), key=lambda x: x.rank or 0):
        print('inserting rank', k)
        group = list(sorted(group, key=lambda x: x.pk))
        step1 = [x for x in group if x.parent is None or x.parent.pk > x.pk]
        step2 = [x for x in group if x.parent is not None and x.parent.pk < x.pk]
        Taxon.objects.bulk_create(step1, batch_size=100)
        Taxon.objects.bulk_create(step2, batch_size=100)


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
              ?item wdt:P171 ?parenttaxon.
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
