import os

import django

if __name__ == '__main__':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "relatedhow.settings")
    django.setup()

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
            # TODO: fix rank of all taxons below
            t.save()
            count += 1

        count = 0

        if count == 0:
            break
