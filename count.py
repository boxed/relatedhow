import os

import django

if __name__ == '__main__':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "relatedhow.settings")
    django.setup()

    from relatedhow.viewer.models import Taxon
    print('total', Taxon.objects.count())
    print('with rank', Taxon.objects.filter(rank__isnull=False).count())
    print('with parent', Taxon.objects.filter(parent__isnull=False).count())
    print('without parent and with simple name', Taxon.objects.filter(parent__isnull=True).exclude(name__contains=' ').count())
    print('empty parents_string', Taxon.objects.filter(parents_string='').count())
