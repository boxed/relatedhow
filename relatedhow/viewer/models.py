# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from functools import total_ordering

import re
from django.db import models
from django.db.models import Q


@total_ordering
class Taxon(models.Model):
    name = models.CharField(max_length=255, db_index=True, null=True)
    english_name = models.CharField(max_length=255, db_index=True, null=True)
    parent = models.ForeignKey('self', null=True, on_delete=models.PROTECT, related_name='children')
    rank = models.IntegerField(null=True)
    number_of_direct_children = models.IntegerField(null=True)
    number_of_direct_and_indirect_children = models.IntegerField(null=True)

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
            if t.parent.pk == t.pk:
                print('warning: invalid taxon points to itself: %s' % t.pk)
                return []
            if len(result) > 1000:
                print('warning: probable infinite loop for %s' % t.pk)
                return []
            result.append(t.parent)
            t = t.parent
        return result

    def __repr__(self):
        return self.name

    def __str__(self):
        return f'{self.name} ({self.pk})'

    def __lt__(self, other):
        return self.name < other.name

    def get_absolute_url(self):
        return f'/clade/{self.pk}/'


def find_matching_taxons(s):
    m = re.match(r'.* \((?P<pk>\d+)\)', s)
    if m:
        return list(Taxon.objects.filter(pk=m.groupdict()['pk']))

    result = list(Taxon.objects.filter(name__iexact=s))
    if not result:
        result = list(Taxon.objects.filter(english_name__iexact=s))

    if not result:
        result = list(Taxon.objects.filter(english_name__iexact=f'domesticated {s}'))

    if not result:
        result = list(Taxon.objects.filter(english_name__iexact=f'domestic {s}'))

    if not result:
        result = list(Taxon.objects.filter(english_name__iexact=f'wild {s}'))

    if not result:
        result = list(Taxon.objects.filter(Q(english_name__istartswith=s) | Q(english_name__iendswith=s)))

    return result
