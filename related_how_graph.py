import os
import sys
import django
from graphviz import Digraph

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

    taxons = [x[0] for x in taxons]

    edges = set()
    for t in taxons:
        tree = list(reversed(t.get_all_parents()))
        for a, b in zip(tree[:-1], tree[1:]):
            edges.add((str(a), str(b)))

    g = Digraph('tree', filename='tree.gv', format='svg')
    g.edges(edges)
    g.view()
