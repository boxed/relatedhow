import os
import sys
from itertools import zip_longest, groupby
import django

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Need two or more arguments: species names in latin or english')
        exit(1)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "relatedhow.settings")
    django.setup()

    from relatedhow.viewer.models import find_matching_taxons

    taxons = [find_matching_taxons(x) for x in sys.argv[1:]]

    for i, t in enumerate(taxons):
        if not t:
            print("Didn't find a taxon %s" % sys.argv[1:][i])
            exit(1)

        if len(t) > 1:
            print('Found more than one taxon for %s:' % sys.argv[1:][i])
            for x in t:
                print(x)
            exit(1)

    parent_lists = sorted([list(reversed(x[0].get_all_parents())) + [x[0]] for x in taxons])

    # Now on to the actual work
    for l in zip_longest(*parent_lists):
        result = ''
        for k, group in groupby(l):
            padding = ' ' * ((len(list(group)) - 1) * 10)
            result += padding + '{:^20}'.format(k.name if k else '') + padding

        # assert len(result) == parent_lists[0] * 20
        print(result)
