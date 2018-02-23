import csv
import os
from itertools import groupby

import django
from django.db.models import Max
from tqdm import tqdm


def export(taxons, filename):
    with open(f'export/{filename}.csv', 'w') as csvfile:
        print(f'exporting {filename}')
        w = csv.writer(csvfile, delimiter='\t')
        w.writerow(['pk', 'name', 'english_name', 'parent_pk'])

        def write(t):
            w.writerow([t.pk, t.name, t.english_name, t.parent.pk])
            for t in t.children.all():
                write(t)

        for t in tqdm(taxons):
            write(t)


if __name__ == '__main__':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "relatedhow.settings")
    django.setup()

    from relatedhow.viewer.models import Taxon

    biota = 2382443
    eukaryota = 19088
    export(Taxon.objects.get(pk=biota).children.exclude(pk=eukaryota), 'misc')

    animalia = 729
    plantae = 756
    export(Taxon.objects.get(pk=eukaryota).children.exclude(pk__in=[animalia, plantae]), 'eukaryota')

    export(Taxon.objects.get(pk=plantae).children.all(), 'plantae')

    bilateria = 5173
    export(Taxon.objects.get(pk=animalia).children.exclude(pk=bilateria), 'animalia')
    export(Taxon.objects.get(pk=bilateria).children.all(), 'bilateria')

    protostomia = 5171
    deuterostomia = 150866
    export(Taxon.objects.get(pk=bilateria).children.exclude(pk__in=[protostomia, deuterostomia]), 'bilateria')
    export(Taxon.objects.get(pk=protostomia).children.all(), 'protostomia')
    export(Taxon.objects.get(pk=deuterostomia).children.all(), 'deuterostomia')

    # for t in Taxon.objects.get(name='insecta').children.all():
    #     print(t, t.number_of_direct_and_indirect_children)
