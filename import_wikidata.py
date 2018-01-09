import os

import django

if __name__ == '__main__':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "relatedhow.settings")
    django.setup()

    from relatedhow.viewer.models import Taxon, setup
    setup()
    import csv
    count = 0
    to_insert = {}

    with open('result.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter='\t')
        for row in reader:
            if count % 10000 == 0:
                print(count, flush=True)
            count += 1

            name = row['?taxonname']
            wikidata_id = row['?item']
            if wikidata_id not in to_insert:
                to_insert[wikidata_id] = Taxon(name=name, wikidata_id=wikidata_id)
            to_insert[wikidata_id].add_parent(row['?parenttaxon'])

    print('...inserting %s clades' % len(to_insert))
    Taxon.objects.bulk_create(to_insert.values())
