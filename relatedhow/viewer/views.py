import os
import re
from uuid import uuid1

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
        disambiguate_prefix = 'disambiguate_'
        disambiguation = [v for k, v in request.POST.items() if k.startswith(disambiguate_prefix)]
        names += disambiguation
        ts = [find_matching_taxons(name) for name in names]

        errors = [
            (name, sorted(taxons, key=lambda x: (x.name or '', x.english_name or '')))
            for name, taxons in zip(names, ts)
            if len(taxons) != 1
        ]
        taxons = [x[0] for x in ts if len(x) == 1]

        if errors:
            return render(
                request=request,
                template_name='viewer/disambiguation.html',
                context=dict(
                    q=','.join(taxon.explicit_str() for taxon in taxons),
                    errors=errors,
                ),
            )

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

    taxon_by_pk = {x.pk: x for x in taxons}

    edges = set()
    for t in taxons:
        tree = list(reversed(t.get_all_parents())) + [t]
        for x in tree:
            taxon_by_pk[x.pk] = x
        for a, b in zip(tree[:-1], tree[1:]):
            edges.add((a.placeholder_str(), b.placeholder_str()))

    g = Digraph('tree', format='svg')
    g.edges(edges)
    uuid = uuid1()
    path = g.render(filename=f'/tmp/graph/{uuid}', cleanup=True)
    with open(path) as f:
        svg = f.read()
    os.remove(path)

    def replacement(matchobj):
        id = int(matchobj.group(1))
        return taxon_by_pk[id].link_str()

    svg = re.sub('#####(\d+)%%%%%', replacement, svg)
    svg = svg.replace('fill="#ffffff"', 'fill="#202b38"').replace('stroke="#000000"', 'stroke="#dbdbdb"')

    return render(
        request=request,
        template_name='viewer/tree.html',
        context=dict(
            q=', '.join(t.explicit_str() for t in taxons),
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
            q=t.explicit_str(),
        )
    )


def fix_issues(request):
    pass
