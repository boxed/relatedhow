import os
import sys

import django

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Need one argument: a species name in latin')
        exit(1)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "relatedhow.settings")
    django.setup()

    from relatedhow.viewer.models import Taxon

    t = Taxon.objects.get(name__iexact=sys.argv[1])
    print('--', t, '--', t.parents_string)
    while t.parent:
        print(t.parent)
        t = t.parent
