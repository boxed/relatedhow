# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
from django.shortcuts import render, redirect
from django.utils.safestring import mark_safe
from graphviz import Digraph

from relatedhow.viewer.models import find_matching_taxons, Taxon


def extract_parts(q):
    names = [x.strip() for x in q.split(',')]
    return [x for x in names if x]


def index(request):
    if request.method == 'POST':
        names = extract_parts(request.POST['q'])
        ts = [find_matching_taxons(name) for name in names]

        errors = [
            (name, taxons)
            for name, taxons in zip(names, ts)
            if len(taxons) != 1
        ]

        if errors:
            return render(
                request=request,
                template_name='viewer/disambiguation.html',
            )

        taxons = [x[0] for x in ts]

        if len(names) > 1:
            return redirect(to='/tree/%s/' % ','.join(str(taxon.pk) for taxon in taxons))
        elif len(names) == 1:
            return redirect(to='/clade/%s/' % taxons[0].pk)
        else:
            return redirect(to='/')

    return render(
        request=request,
        template_name='viewer/index.html',
    )


def tree(request, pks):
    taxons = [Taxon.objects.get(pk=pk) for pk in extract_parts(pks)]

    edges = set()
    for t in taxons:
        tree = list(reversed(t.get_all_parents())) + [t]
        for a, b in zip(tree[:-1], tree[1:]):
            edges.add((str(a), str(b)))

    # TODO: filename! and write to temp dir
    g = Digraph('tree', format='svg')
    # for t in taxons:
    #     g.node(str(t), label=f'<a href="{t.get_absolute_url()}">{t.name}</a>')
    g.edges(edges)
    path = g.render(filename='RANDOM_HERE', cleanup=True)
    svg = open(path).read()
    os.remove(path)

    return render(
        request=request,
        template_name='viewer/tree.html',
        context=dict(
            q=', '.join(str(t) for t in taxons),
            tree=mark_safe(svg),
        ),
    )


def clade(request, pk):
    t = Taxon.objects.get(pk=pk)

    return render(
        request=request,
        template_name='viewer/clade.html',
        context=dict(
            taxon=t,
            q=f'{t.name} ({t.pk})',
        )
    )
