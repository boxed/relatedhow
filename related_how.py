import os
import sys
from itertools import zip_longest

import django

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Need two arguments: species names in latin or english')
        exit(1)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "relatedhow.settings")
    django.setup()

    from relatedhow.viewer.models import find_matching_taxons

    taxons_a = find_matching_taxons(sys.argv[1])
    taxons_b = find_matching_taxons(sys.argv[2])

    if not taxons_a:
        print("Didn't find a taxon %s" % sys.argv[1])
        exit(1)

    if not taxons_b:
        print("Didn't find a taxon %s" % sys.argv[2])
        exit(1)

    if len(taxons_a) > 1:
        print('Found more than one taxon for %s:' % sys.argv[1])
        for t in taxons_a:
            print(t)
        exit(1)

    if len(taxons_b) > 1:
        print('Found more than one taxon for %s:' % sys.argv[2])
        for t in taxons_b:
            print(t)
        exit(1)

    # Now on to the actual work
    p_a, p_b = reversed(taxons_a[0].get_all_parents()), reversed(taxons_b[0].get_all_parents())
    for a, b in zip_longest(p_a, p_b):
        if a == b:
            print('{:^43}'.format(str(a)))
        else:
            print('{:^20}   {:^20}'.format(str(a or ''), str(b or '')))

