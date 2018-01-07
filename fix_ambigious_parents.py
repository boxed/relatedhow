import os

import django

if __name__ == '__main__':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "relatedhow.settings")
    django.setup()

    from relatedhow.viewer.models import Taxon

    for t in Taxon.objects.filter(parent__isnull=False, rank__isnull=False).exclude(name='Biota').filter(parents_string__contains='\t'):
        try:
            try:
                parents = [Taxon.objects.get(name=name) for name in t.parents_string.split('\t')]
            except Taxon.DoesNotExist:
                continue

            if any([p.rank is None for p in parents]):
                continue

            parents = sorted(parents, key=lambda x: x.rank)
            if parents[0].rank == parents[1].rank:
                print('warning:', t, 'has multiple same rank parents!', parents)
            if t.parent != parents[0]:
                t.parent = parents[0]
                old_rank = t.rank
                t.rank = t.parent.rank + 1
                t.save()
                print('\t', t, old_rank, '->', t.rank)
        except Taxon.DoesNotExist:
            pass
