from django.apps import AppConfig
import sys


class BankConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bank'

    def ready(self):
        import bank.signals.transaction_signals  # Import transaction processing signals
        import bank.signals.notification_signals  # Import notification signals
        import bank.signals.kyc_signals  # Import KYC signals for wallet creation
        # Optional: ensure Celery finds tasks when autodiscover runs
        import bank.tasks  # noqa: F401
        # Start APScheduler job only for server process
        if 'runserver' in sys.argv or 'runserver_plus' in sys.argv:
            try:
                from django_apscheduler.jobstores import register_events, DjangoJobStore
                from apscheduler.schedulers.background import BackgroundScheduler
                from bank.tasks import run_daily_interest_job
                scheduler = BackgroundScheduler()
                scheduler.add_jobstore(DjangoJobStore(), 'default')
                # Daily at 23:55
                scheduler.add_job(
                    run_daily_interest_job,
                    trigger='cron',
                    hour=23,
                    minute=55,
                    name='Process daily interest (SAS & XySave)',
                    replace_existing=True
                )
                register_events(scheduler)
                scheduler.start()
            except Exception:
                # Don't break app startup due to scheduler issues
                pass

