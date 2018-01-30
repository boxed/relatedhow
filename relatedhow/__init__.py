import csv
from itertools import groupby


def wikidata_id_as_int(s):
    prefix = '<http://www.wikidata.org/entity/Q'
    suffix = '>'
    assert s.startswith(prefix)
    assert s.endswith(suffix)
    return int(s[len(prefix):-len(suffix)])


def fix_text(s):
    return s.encode('ascii', errors='ignore').decode('ascii')


def import_wikidata():
    from relatedhow.viewer.models import Taxon
    count = 0
    taxon_by_pk = {
        2382443: Taxon(id=2382443, name='Biota', english_name='Life'),
        23012932: Taxon(id=23012932, name='Ichnofossils'),
        24150684: Taxon(id=24150684, name='Agmata'),
        5381701: Taxon(id=5381701, name='Eohostimella'),
        23832652: Taxon(id=23832652, name='Anucleobionta'),
        21078601: Taxon(id=21078601, name='Yelovichnus'),
        35107213: Taxon(id=35107213, name='Rhizopodea'),
        46987746: Taxon(id=46987746, name='Pan-Angiospermae'),
    }
    pks_of_taxons_with_ambigious_parents = set()

    print('load names.csv')
    english_name_by_pk = load_wikidata_names()

    print('load result.csv')
    with open('result.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter='\t')
        for row in reader:
            if count % 10000 == 0:
                print(count)
            count += 1

            name = fix_text(row['?taxonname'])
            pk = wikidata_id_as_int(row['?item'])
            if pk not in taxon_by_pk:
                taxon_by_pk[pk] = Taxon(id=pk, name=name, english_name=english_name_by_pk.get(pk))
            taxon_by_pk[pk].add_parent(wikidata_id_as_int(row['?parenttaxon']))

    print('set parents and (non-stored) children')

    for taxon in taxon_by_pk.values():
        taxon._children = set()

    for taxon in taxon_by_pk.values():
        if taxon.parents_string:
            parent_pk = int(taxon.parents_string.partition('\t')[0])
            if parent_pk not in taxon_by_pk:
                print('warning: %s not in taxon_by_pk' % parent_pk)
                continue
            parent_taxon = taxon_by_pk[parent_pk]
            taxon.parent = parent_taxon
            parent_taxon._children.add(taxon)
            if '\t' in taxon_by_pk[pk].parents_string:
                pks_of_taxons_with_ambigious_parents.add(pk)

    print('set rank')

    def set_rank(taxon, rank):
        taxon.rank = rank
        for child in taxon._children:
            set_rank(child, rank + 1)

    biota = taxon_by_pk[2382443]
    for taxon in taxon_by_pk.values():
        if taxon.rank is None and taxon.parent is None:
            set_rank(taxon, rank=0)

    print('fix ambiguous parents, until stable')

    def fix_ambiguous_parents():
        count = 0
        for pk in pks_of_taxons_with_ambigious_parents:
            taxon = taxon_by_pk[pk]
            parents = {taxon_by_pk[int(parent_pk)] for parent_pk in taxon.split('\t')}
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
    count = 0
    name_by_pk = {}
    with open('names.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter='\t')
        for row in reader:
            if count % 10000 == 0:
                print(count)

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
                count += 1
    return name_by_pk


# def fix_ambiguous_parents():
#     from relatedhow.viewer.models import Taxon
#     qs = Taxon.objects.filter(parent__isnull=False, rank__isnull=False).exclude(name='Biota')
#     if qs.count() == 0:
#         print('You need to run set_rank.py first')
#         exit(1)
#
#     for t in qs.filter(parents_string__contains='\t'):
#         try:
#             try:
#                 parents = [Taxon.objects.get(wikidata_id=wikidata_id) for wikidata_id in t.parents_string.split('\t')]
#             except Taxon.DoesNotExist:
#                 continue
#
#             if any([p.rank is None for p in parents]):
#                 continue
#
#             parents = sorted(parents, key=lambda x: x.rank, reverse=True)
#             if parents[0].rank == parents[1].rank:
#                 print('warning:', t, 'has multiple same rank parents!', parents)
#             if t.parent != parents[0]:
#                 t.parent = parents[0]
#                 old_rank = t.rank
#                 t.rank = t.parent.rank + 1
#                 t.save()
#                 print('\t', t, old_rank, '->', t.rank)
#                 t.update_rank_of_children()
#         except Taxon.DoesNotExist:
#             pass
#
#
# def _set_parents(queryset):
#     from relatedhow.viewer.models import Taxon
#     count = 0
#     taxons = {t.wikidata_id: t for t in Taxon.objects.all()}
#     for t in queryset:
#         try:
#             if count % 1000 == 0:
#                 print(count)
#             count += 1
#
#             parents = t.parents_string.split('\t')
#
#             if not t.parents_string:
#                 print('WARNING: orphan taxon', t)
#                 continue
#
#             if parents[0] == '':
#                 print('ERROR', t)
#             assert parents[0] != ''
#             try:
#                 t.parent = taxons[parents[0]]
#             except KeyError:
#                 print('WARNING: references unknown name', parents[0])
#             t.save()
#             # print(t, parents)
#         except Taxon.DoesNotExist:
#             pass


def import_and_process():
    print('import_wikidata')
    import_wikidata()
