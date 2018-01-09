# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models


class Taxon(models.Model):
    wikidata_id = models.CharField(max_length=1024, db_index=True, unique=True)

    name = models.CharField(max_length=1024, db_index=True)
    parent = models.ForeignKey('self', null=True, on_delete=models.PROTECT)
    parents_string = models.TextField()
    rank = models.IntegerField(null=True)

    def add_parent(self, p):
        parents = {x for x in self.parents_string.split('\t') if x}
        parents.add(p)
        self.parents_string = '\t'.join(parents)

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name


def setup():
    Taxon.objects.get_or_create(name='Biota', wikidata_id='<http://www.wikidata.org/entity/Q2382443>')
    Taxon.objects.get_or_create(name='Ichnofossils', wikidata_id='<http://www.wikidata.org/entity/Q23012932>')
    #"core eudicots", ""http://www.wikidata.org/entity/Q869087"
    # eupolypods I https://www.wikidata.org/wiki/Q5410882
    # euasterids II https://www.wikidata.org/wiki/Q14405943

