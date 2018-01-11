import os

import django

from relatedhow import import_wikidata_names

if __name__ == '__main__':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "relatedhow.settings")
    django.setup()

    import_wikidata_names()
