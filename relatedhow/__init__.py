import csv


def import_wikidata():
    from relatedhow.viewer.models import Taxon, setup
    setup()
    count = 0
    to_insert = {}

    with open('result.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter='\t')
        for row in reader:
            if count % 10000 == 0:
                print(count)
            count += 1

            name = row['?taxonname']
            wikidata_id = row['?item']
            if wikidata_id not in to_insert:
                to_insert[wikidata_id] = Taxon(name=name, wikidata_id=wikidata_id)
            to_insert[wikidata_id].add_parent(row['?parenttaxon'])

    print('...inserting %s clades' % len(to_insert))
    Taxon.objects.bulk_create(to_insert.values(), batch_size=10000)


def import_wikidata_names():
    from relatedhow.viewer.models import Taxon, setup
    setup()
    count = 0

    with open('names.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter='\t')
        for row in reader:
            if count % 10000 == 0:
                print(count)

            name = row['?label']
            wikidata_id = row['?item']
            if name.endswith('@en'):
                if name.startswith('"'):
                    assert name.endswith('"@en')
                    name = name[1:-len('"@en')]
                else:
                    assert name.endswith('@en')
                    name = name[:-len('@en')]
                try:
                    t = Taxon.objects.get(wikidata_id=wikidata_id)
                    if t.name.lower() != name.lower():
                        t.english_name = name
                        t.save()
                        count += 1
                except Taxon.DoesNotExist:
                    pass


def fix_ambiguous_parents():
    from relatedhow.viewer.models import Taxon
    qs = Taxon.objects.filter(parent__isnull=False, rank__isnull=False).exclude(name='Biota')
    if qs.count() == 0:
        print('You need to run set_rank.py first')
        exit(1)

    for t in qs.filter(parents_string__contains='\t'):
        try:
            try:
                parents = [Taxon.objects.get(wikidata_id=wikidata_id) for wikidata_id in t.parents_string.split('\t')]
            except Taxon.DoesNotExist:
                continue

            if any([p.rank is None for p in parents]):
                continue

            parents = sorted(parents, key=lambda x: x.rank, reverse=True)
            if parents[0].rank == parents[1].rank:
                print('warning:', t, 'has multiple same rank parents!', parents)
            if t.parent != parents[0]:
                t.parent = parents[0]
                old_rank = t.rank
                t.rank = t.parent.rank + 1
                t.save()
                print('\t', t, old_rank, '->', t.rank)
                t.update_rank_of_children()
        except Taxon.DoesNotExist:
            pass


def _set_parents(queryset):
    from relatedhow.viewer.models import Taxon
    count = 0
    taxons = {t.wikidata_id: t for t in Taxon.objects.all()}
    for t in queryset:
        try:
            if count % 1000 == 0:
                print(count)
            count += 1

            parents = t.parents_string.split('\t')

            if not t.parents_string:
                print('WARNING: orphan taxon', t)
                continue

            if parents[0] == '':
                print('ERROR', t)
            assert parents[0] != ''
            try:
                t.parent = taxons[parents[0]]
            except KeyError:
                print('WARNING: references unknown name', parents[0])
            t.save()
            # print(t, parents)
        except Taxon.DoesNotExist:
            pass


def fix_parents():
    from relatedhow.viewer.models import Taxon
    taxons = Taxon.objects.filter(parent=None).exclude(name='Biota')
    _set_parents(taxons.exclude(name__contains=' '))  # take the more important taxons first
    _set_parents(taxons)


def set_rank():
    from relatedhow.viewer.models import Taxon
    biota = Taxon.objects.get(name='Biota')
    biota.rank = 0
    biota.save()

    while True:
        count = 0
        for t in Taxon.objects.filter(parent__rank__isnull=False, rank=None).select_related('parent'):
            if count % 1000 == 0:
                print(count)
            count += 1

            t.rank = t.parent.rank + 1
            t.update_rank_of_children()
            t.save()
            count += 1

        count = 0

        if count == 0:
            break


def import_and_process():
    print('import_wikidata')
    import_wikidata()
    print('import_wikidata_names')
    import_wikidata_names()
    print('fix_parents')
    fix_parents()
    print('set_rank')
    set_rank()
    print('fix_ambiguous_parents')
    fix_ambiguous_parents()
