import csv
from itertools import groupby
from urllib.parse import urlencode
import requests
from os.path import exists
from tqdm import tqdm


def wikidata_id_as_int(s):
    prefix = '<http://www.wikidata.org/entity/Q'
    suffix = '>'
    assert s.startswith(prefix), s
    assert s.endswith(suffix), s
    return int(s[len(prefix):-len(suffix)])


def fix_text(s):
    return s.encode('ascii', errors='ignore').decode('ascii')


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
    pks_of_taxons_with_ambigious_parents = set()

    print('load names.csv')
    english_name_by_pk = load_wikidata_names()

    print('load result.csv')
    with open('result.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter='\t')
        for row in tqdm(reader):
            if '_:' in row['?taxonname'] or '_:' in row['?item'] or '_:' in row['?parenttaxon']:
                print('invalid row for', row['?item'])
                continue
            name = fix_text(row['?taxonname'])
            pk = wikidata_id_as_int(row['?item'])
            if pk not in taxon_by_pk:
                taxon_by_pk[pk] = Taxon(id=pk, name=name, english_name=english_name_by_pk.get(pk))
            taxon_by_pk[pk].add_parent(wikidata_id_as_int(row['?parenttaxon']))

    print('set parents and (non-stored) children')

    for taxon in taxon_by_pk.values():
        taxon._children = set()

    dangling_references = set()

    for taxon in tqdm(taxon_by_pk.values()):
        if taxon.parents_string:
            parent_pk = int(taxon.parents_string.partition('\t')[0])
            if parent_pk not in taxon_by_pk:
                dangling_references.add(parent_pk)
                continue
            parent_taxon = taxon_by_pk[parent_pk]
            taxon.parent = parent_taxon
            parent_taxon._children.add(taxon)
            if '\t' in taxon.parents_string:
                pks_of_taxons_with_ambigious_parents.add(pk)

    for pk in dangling_references:
        print('warning: %s not in taxon_by_pk but was referenced' % pk)

    print('set rank')

    def set_rank(taxon, rank):
        taxon.rank = rank
        for child in taxon._children:
            set_rank(child, rank + 1)

    for taxon in tqdm(taxon_by_pk.values()):
        if taxon.rank is None and taxon.parent is None:
            set_rank(taxon, rank=0)

    print('fix ambiguous parents, until stable (%s)' % len(pks_of_taxons_with_ambigious_parents))

    def fix_ambiguous_parents():
        count = 0
        for pk in tqdm(pks_of_taxons_with_ambigious_parents):
            taxon = taxon_by_pk[pk]
            parents = {taxon_by_pk[int(parent_pk)] for parent_pk in taxon.parents_string.split('\t')}
            max_rank = max([x.rank for x in parents])
            relevant_parents = [p for p in parents if p.rank == max_rank]
            if len(relevant_parents) > 1:
                print('Warning: %s has multiple parents with the same rank' % taxon)
            if taxon.parent != relevant_parents[0]:
                taxon.parent = relevant_parents[0]
                set_rank(taxon, rank=max_rank + 1)
                count += 1
        return count

    while fix_ambiguous_parents():
        continue

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

    print('...inserting %s clades' % len(taxon_by_pk))
    for k, group in groupby(sorted(taxon_by_pk.values(), key=lambda x: x.rank or 0), key=lambda x: x.rank or 0):
        print('inserting rank', k)
        group = list(group)
        Taxon.objects.bulk_create(group, batch_size=1000)


def load_wikidata_names():
    name_by_pk = {}
    with open('names.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter='\t')
        for row in tqdm(reader):
            name = fix_text(row['?label'])
            pk = wikidata_id_as_int(row['?item'])
            if name.endswith('@en'):
                if name.startswith('"'):
                    assert name.endswith('"@en')
                    name = name[1:-len('"@en')]
                else:
                    assert name.endswith('@en')
                    name = name[:-len('@en')]
                name_by_pk[pk] = name
    return name_by_pk


def download_taxons():
    if exists('result.csv'):
        print('\tusing existing file')
        return

    select = """
    SELECT ?item ?parenttaxon ?taxonname WHERE {
      ?item wdt:P225 ?taxonname.
      ?item wdt:P171 ?parenttaxon.
    }
    """

    result = requests.get('https://query.wikidata.org/sparql?%s' % urlencode([('query', select)]), headers={'Accept': 'text/tab-separated-values'}).text
    if '\tat ' in result:
        print('Error with download, got %sMB' % (len(result) / (1024 * 10424)))
        exit(1)

    with open('result.csv', 'w') as f:
        f.write(result)


def download_names():
    if exists('names.csv'):
        print('\tusing existing file')
        return

    select = """
    SELECT DISTINCT ?item ?label WHERE {
      ?item wdt:P225 ?taxonname.
      ?item wdt:P1843 ?label. FILTER (langMatches( lang(?label), "EN" ) )
    }
    """

    result = requests.get('https://query.wikidata.org/sparql?%s' % urlencode([('query', select)]), headers={'Accept': 'text/tab-separated-values'}).text

    if '\tat ' in result:
        print('Error with download')
        exit(1)
    with open('names.csv', 'w') as f:
        f.write(result)


def import_and_process():
    print('Downloading taxons')
    download_taxons()
    exit(1)
    print('Downloading names')
    download_names()
    import_wikidata()
