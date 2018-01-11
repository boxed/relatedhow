# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.db.models import Q


class Taxon(models.Model):
    wikidata_id = models.CharField(max_length=255, db_index=True, unique=True)

    name = models.CharField(max_length=1024, db_index=True)
    english_name = models.CharField(max_length=1024, db_index=True, null=True)
    parent = models.ForeignKey('self', null=True, on_delete=models.PROTECT, related_name='children')
    parents_string = models.TextField()
    rank = models.IntegerField(null=True)

    def add_parent(self, p):
        parents = {x for x in self.parents_string.split('\t') if x}
        parents.add(p)
        self.parents_string = '\t'.join(parents)

    def update_rank_of_children(self):
        for c in self.children.all():
            c.rank = self.rank + 1
            c.save()
            print('.', end='', flush=True)
            c.update_rank_of_children()

    def get_all_parents(self):
        result = []
        t = self
        while t.parent:
            result.append(t.parent)
            t = t.parent
        return result

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name


def find_matching_taxons(s):
    result = list(Taxon.objects.filter(name__iexact=s))
    if not result:
        result = list(Taxon.objects.filter(english_name__iexact=s))
    if not result:
        result = Taxon.objects.filter(Q(name__icontains=s) | Q(english_name__icontains=s))

    return result


def setup():
    Taxon.objects.get_or_create(name='Biota', wikidata_id='<http://www.wikidata.org/entity/Q2382443>')
    Taxon.objects.get_or_create(name='Ichnofossils', wikidata_id='<http://www.wikidata.org/entity/Q23012932>')
