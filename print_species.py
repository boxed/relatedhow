import os
import sys

import django

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Need one argument: a species name in latin or english')
        exit(1)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "relatedhow.settings")
    django.setup()

    from relatedhow.viewer.models import find_matching_taxons

    def print_taxons(taxons):
        for t in taxons:
            print('--', t, '-', t.english_name, '--', t.wikidata_id)
            for parent in t.get_all_parents():
                print(parent)
        return len(taxons)

    taxons = find_matching_taxons(sys.argv[1])
    if not taxons:
        print("Didn't find a taxon with that name")
    else:
        print_taxons(taxons)
