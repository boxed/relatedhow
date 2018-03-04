import os
import pickle
from collections import defaultdict

import django


if __name__ == '__main__':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "relatedhow.settings")
    django.setup()

    from relatedhow.viewer.models import Taxon

    print('load')
    taxon_by_pk = {t.pk: t for t in list(Taxon.objects.all())}

    print('dump')
    with open('data.pickle', 'wb') as f:
        names = defaultdict(set)
        for t in taxon_by_pk.values():
            names[t.name].add(t.pk)

        english_names = defaultdict(set)
        for t in taxon_by_pk.values():
            english_names[t.english_name].add(t.pk)

        data = dict(
            names=names,
            english_names=english_names,
            parents={t.pk: t.parent_id for t in taxon_by_pk.values() if t.parent_id},
        )
        pickle.dump(data, f)
