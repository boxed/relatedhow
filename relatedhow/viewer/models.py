# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models


class Taxon(models.Model):
    name = models.CharField(max_length=1024, db_index=True, unique=True)
    parent = models.ForeignKey('self', null=True, on_delete=models.PROTECT)
    parents_string = models.TextField()
    rank = models.IntegerField(null=True)

    def add_parent(self, p):
        parents = [x for x in self.parents_string.split('\t') if x]
        parents.append(p)
        self.parents_string = '\t'.join(parents)

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name
