import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'Sponge.settings'
os.environ["CELERY_LOADER"] = "django"
import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
