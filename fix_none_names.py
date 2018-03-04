import os

import django
from tqdm import tqdm

if __name__ == '__main__':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "relatedhow.settings")
    django.setup()

    from relatedhow.viewer.models import Taxon
    from relatedhow import download_contents, clean_name

    for t in tqdm([x for x in Taxon.objects.filter(name=None)]):
        r = download_contents(f'{t.pk}', """
SELECT ?itemLabel WHERE {
  VALUES ?item { wd:Q%s }
  ?item p:P171 ?p171stm .
  ?p171stm ps:P171 ?parenttaxon;
           wikibase:rank ?rank .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
}
ORDER BY DESC(?rank)
""" % t.pk)
        t.name = clean_name(r.strip().split('\n')[-1])
        assert t.name
        t.save()
