import os

import django


if __name__ == '__main__':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "relatedhow.settings")
    django.setup()

    from relatedhow import import_and_process
    import_and_process()
