import os
from collections import defaultdict

import django
from django.db.models import Q, Max

if __name__ == '__main__':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "relatedhow.settings")
    django.setup()

    from relatedhow.viewer.models import Taxon

    biota = Taxon.objects.get(name='Biota')
    # max_rank = Taxon.objects.all().aggregate(Max('rank'))['rank__max']
    # print('max rank', max_rank)

    print('listing')
    # taxons = list(Taxon.objects.filter(Q(parent__parent__parent=biota) | Q(parent__parent=biota) | Q(parent=biota) | Q(pk=biota.pk)))
    taxons = list(Taxon.objects.all())

    print('building dict')
    taxon_by_pk = {t.pk: t for t in taxons}
    biota = taxon_by_pk[biota.pk]

    print('setup members')
    for t in taxons:
        t._children = set()

    print('registering children')
    for t in taxons:
        if t.parent_id is not None:
            taxon_by_pk[t.parent_id]._children.add(t)

    def get_count(t):
        t.number_of_direct_children = len(t._children)
        t.number_of_direct_and_indirect_children = sum(get_count(c) for c in t._children) + t.number_of_direct_children
        return t.number_of_direct_and_indirect_children


    print('calculating')
    print('\t total count:', len(taxon_by_pk))
    print('\t biota count:', get_count(biota))

    print('updating db...')
    for t in taxons:
        t.save()
