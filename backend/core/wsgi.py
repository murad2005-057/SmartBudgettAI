"""
WSGI config for core project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""

import logging
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

application = get_wsgi_application()


def _auto_migrate():
    """Create/upgrade the database tables when the app starts.

    Vercel has no post-deploy hook for Django, so without this the database
    stays empty and the very first query (in /api/register/) fails with
    "no such table: auth_user" -> HTTP 500.
    """
    from django.conf import settings
    from django.core.management import call_command

    if not getattr(settings, 'AUTO_MIGRATE', False):
        return
    try:
        call_command('migrate', interactive=False, verbosity=0)
    except Exception:  # keep the app importable; requests will report JSON errors
        logging.getLogger(__name__).exception('Automatic database migration failed')


_auto_migrate()
