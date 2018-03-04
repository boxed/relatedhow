import csv
import os

import django
from tqdm import tqdm


if __name__ == '__main__':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "relatedhow.settings")
    django.setup()

    from relatedhow.viewer.models import Taxon

    print('load')
    taxon_by_pk = {t.pk: t for t in list(Taxon.objects.all())}

    print('setup')
    for t in tqdm(taxon_by_pk.values()):
        t._children = []
    for t in tqdm(taxon_by_pk.values()):
        if t.parent_id:
            t.parent = taxon_by_pk[t.parent_id]
            t.parent._children.append(t)

    print('relevant...')
    taxon_by_pk = {t.pk: t for t in tqdm(taxon_by_pk.values()) if t.number_of_direct_and_indirect_children > 100 or t.name is None or t.parent is None or t.parent.name is None or not t.name.startswith(t.parent.name + ' ')}
    print(len(taxon_by_pk))
    print('setup2')
    for t in tqdm(taxon_by_pk.values()):
        t._children = []
    for t in tqdm(taxon_by_pk.values()):
        if t.parent_id and t.parent_id in taxon_by_pk:
            t.parent = taxon_by_pk[t.parent_id]
            t.parent._children.append(t)

    foo = dict(
        biota=2382443,
        eukaryota=19088,
        animalia=729,
        chromista=862296,  # some algae
        fungi=764,
        bilateria=5173,
        protostomia=5171,  # non-vertebrate bilateral
        deuterostomia=150866,  # includes vertebrates
        actinopterygii=127282,  # Ray - finned Fishes
        reptilia=10811,
        synapsidomorpha=21353733,  # includes mammals
        superrosids=23905211,  # big group of flowering plants
        superasterids=23927181,  # big group of flowering plants
    )
    change_file_pks = set(foo.values())

    counter = 0

    def export(t, writer=None):
        global counter
        if writer is None or t.pk in change_file_pks:
            name = t.name or t.english_name or f'Q{t.pk}'
            print(f'change file: {name}')
            with open(f'export_relevant/{counter:02}_{name}.csv', 'w') as csvfile:
                counter += 1
                writer = csv.writer(csvfile, delimiter='\t')
                writer.writerow([t.pk, t.name, t.english_name, t.parent.pk if t.parent else ''])
                for t in t._children:
                    export(t, writer)
            print(f'done with {name}')
        else:
            writer.writerow([t.pk, t.name, t.english_name, t.parent.pk if t.parent else ''])
            for t in t._children:
                export(t, writer)

    export(taxon_by_pk[foo['biota']])
