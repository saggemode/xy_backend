from django.apps import AppConfig
import sys


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        import accounts.signals
        # Only start scheduler if running the development server
        if 'runserver' in sys.argv:
            from django_apscheduler.jobstores import register_events, DjangoJobStore
            from apscheduler.schedulers.background import BackgroundScheduler
            from accounts.tasks import delete_expired_unverified_users
            scheduler = BackgroundScheduler()
            scheduler.add_jobstore(DjangoJobStore(), 'default')
            scheduler.add_job(
                delete_expired_unverified_users,
                'interval',
                minutes=10,
                name='Delete expired unverified users',
                replace_existing=True
            )
            register_events(scheduler)
            scheduler.start()
