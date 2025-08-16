from .celery_app import app as celery_app

__all__ = ('celery_app',)
# (Celery import removed; this file can be left empty unless needed for Django startup)
