# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
from django.shortcuts import render, redirect
from django.utils.safestring import mark_safe
from graphviz import Digraph

from relatedhow.viewer.models import find_matching_taxons


def extract_names(q):
    names = [x.strip() for x in q.split(',')]
    return sorted([x for x in names if x])


def index(request):
    if request.method == 'POST':
        names = extract_names(request.POST['q'])
        if len(names) > 1:
            return redirect(to='/tree/%s/' % ','.join(names))
        elif len(names) == 1:
            return redirect(to='/clade/%s/' % names[0])
        else:
            return redirect(to='/')

    return render(
        request=request,
        template_name='viewer/index.html',
    )


def tree(request, names):
    ts = [find_matching_taxons(name) for name in extract_names(names)]

    errors = [
        (name, taxons)
        for name, taxons in zip(names, ts)
        if len(taxons) != 1
    ]

    svg = None
    if not errors:
        taxons = [x[0] for x in ts]

        edges = set()
        for t in taxons:
            tree = list(reversed(t.get_all_parents())) + [t]
            for a, b in zip(tree[:-1], tree[1:]):
                edges.add((str(a), str(b)))

        # TODO: filename! and write to temp dir
        g = Digraph('tree', format='svg')
        g.edges(edges)
        path = g.render(filename='RANDOM_HERE', cleanup=True)
        svg = open(path).read()
        os.remove(path)

    return render(
        request=request,
        template_name='viewer/tree.html',
        context=dict(
            q=names,
            tree=mark_safe(svg),
            errors=errors,
        ),
    )


def clade(request, name):
    t = find_matching_taxons(name)

    return render(
        request=request,
        template_name='viewer/clade.html',
        context=dict(
            taxon=t[0] if len(t) == 1 else None,
            error=t if len(t) != 1 else [],
            q=name,
        )
    )
