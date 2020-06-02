from __future__ import unicode_literals

from functools import total_ordering

import re
from django.db import models
from django.db.models import Q


def capitalize(s):
    return s[0].upper() + s[1:]


@total_ordering
class Taxon(models.Model):
    name = models.CharField(max_length=255, db_index=True, null=True)
    english_name = models.CharField(max_length=255, db_index=True, null=True)
    alias = models.CharField(max_length=255, db_index=True, null=True)
    parent = models.ForeignKey('self', null=True, on_delete=models.PROTECT, related_name='children')
    rank = models.IntegerField(null=True)
    number_of_direct_children = models.IntegerField(null=True)
    number_of_direct_and_indirect_children = models.IntegerField(null=True)
    image = models.URLField(default=None, null=True, max_length=1024)
    wikipedia_title = models.CharField(max_length=255, null=True)

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
        return f'<{self.pk}: {self.name}>'

    def names(self):
        return [
            x
            for x in
            [self.name, self.english_name, self.alias, self.wikipedia_title]
            if x
        ]

    def __str__(self):
        names = self.names()
        if names:
            return capitalize(self.names()[0])
        else:
            return '<no label>'

    def alt_name(self):
        name = str(self).lower()
        try:
            return capitalize([x for x in self.names() if x.lower() != name][0])
        except IndexError:
            return None

    def image_url(self):
        from hashlib import md5
        from urllib.parse import quote
        x = self.image
        hash = md5(x.replace(' ', '_').encode()).hexdigest()
        return f'https://upload.wikimedia.org/wikipedia/commons/{hash[0]}/{hash[:2]}/{quote(x.replace(" ", "_"))}'

    def placeholder_str(self):
        return f'#####{self.id}%%%%%'

    def link_str(self):
        return f'<a xlink:href="{self.get_absolute_url()}">{self.name or self.english_name}</a>'

    def explicit_str(self):
        return f'{self} ({self.pk})'

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
