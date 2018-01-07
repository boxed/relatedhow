import os

import django

if __name__ == '__main__':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "relatedhow.settings")
    django.setup()

    from relatedhow.viewer.models import Taxon

    biota = Taxon.objects.get_or_create(name='Biota')[0]
    biota.rank = 0
    biota.save()

    while True:
        count = 0
        for t in Taxon.objects.filter(parent__rank__isnull=False, rank=None).select_related('parent'):
            # print(t)
            t.rank = t.parent.rank + 1
            t.save()
            count += 1

        if count == 0:
            break
