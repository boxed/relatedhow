import os

import django

if __name__ == '__main__':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "relatedhow.settings")
    django.setup()

    from relatedhow.viewer.models import Taxon
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
            if name not in to_insert:
                to_insert[name] = Taxon(name=name)
            to_insert[name].add_parent(row['?parenttaxonname'])

    Taxon.objects.bulk_create(to_insert.values())
