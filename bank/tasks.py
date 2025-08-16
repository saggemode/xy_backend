from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone
from celery import shared_task

@shared_task(bind=True, ignore_result=True)
def send_weekly_statements(self):
    from .models import Wallet, Transaction
    User = get_user_model()
    today = timezone.now().date()
    week_ago = today - timezone.timedelta(days=7)
    for user in User.objects.filter(is_active=True):
        try:
            wallet = Wallet.objects.get(user=user)
        except Wallet.DoesNotExist:
            continue
        txs = Transaction.objects.filter(wallet=wallet, timestamp__date__gte=week_ago, timestamp__date__lte=today).order_by('timestamp')
        if not txs.exists():
            continue
        opening_balance = txs.first().balance_after - txs.first().amount if txs.first().balance_after is not None else 0
        closing_balance = txs.last().balance_after if txs.last().balance_after is not None else 0
        total_credits = sum(t.amount for t in txs if t.type == 'credit')
        total_debits = sum(t.amount for t in txs if t.type == 'debit')
        html = render_to_string('bank/statement_pdf.html', {
            'user': user,
            'wallet': wallet,
            'transactions': txs,
            'date_from': week_ago,
            'date_to': today,
            'opening_balance': opening_balance,
            'closing_balance': closing_balance,
            'total_credits': total_credits,
            'total_debits': total_debits,
            'now': timezone.now(),
        })
        # Hook: render html to PDF and email (intentionally disabled in dev)
        # email = EmailMessage(
        #     subject=f"Your Weekly Account Statement ({week_ago} to {today})",
        #     body=html,
        #     from_email=None,
        #     to=[user.email],
        # )
        # email.send()


@shared_task(bind=True, ignore_result=True)
def process_daily_interest(self):
    """Process daily interest for Spend & Save and XySave."""
    from .spend_and_save_services import SpendAndSaveInterestService
    from .xysave_services import XySaveInterestService

    try:
        SpendAndSaveInterestService.process_daily_interest_payout()
    except Exception:
        # swallow errors to keep task idempotent across retries
        pass

    try:
        XySaveInterestService.calculate_daily_interest_for_all_accounts()
    except Exception:
        pass


@shared_task(bind=True, ignore_result=True)
def send_spend_save_daily_summaries(self):
    """Send daily Spend & Save summaries/notifications (placeholder hook)."""
    from .spend_and_save_notifications import SpendAndSaveNotificationService
    from django.contrib.auth import get_user_model
    from .models import SpendAndSaveAccount

    User = get_user_model()
    for user in User.objects.filter(is_active=True).iterator():
        try:
            account = SpendAndSaveAccount.objects.get(user=user)
            # Example: weekly summary can be adapted to daily
            weekly_stats = {
                'total_spent': 0,
                'total_saved': float(account.total_saved_from_spending.amount) if account.total_saved_from_spending else 0,
                'transactions_count': int(account.total_transactions_processed or 0),
            }
            # Optional: SpendAndSaveNotificationService.send_weekly_savings_summary(user, account, weekly_stats)
        except SpendAndSaveAccount.DoesNotExist:
            continue


# APScheduler-friendly wrapper (no Celery context required)
def run_daily_interest_job():
    from .spend_and_save_services import SpendAndSaveInterestService
    from .xysave_services import XySaveInterestService
    from .fixed_savings_services import FixedSavingsService
    try:
        SpendAndSaveInterestService.process_daily_interest_payout()
    except Exception:
        pass
    try:
        XySaveInterestService.calculate_daily_interest_for_all_accounts()
    except Exception:
        pass
    try:
        # Process matured fixed savings payouts and auto-renewals
        from .models import FixedSavingsAccount
        for fs in FixedSavingsAccount.objects.filter(is_active=True).iterator():
            try:
                # Maturity payout
                if fs.is_mature and not fs.is_paid_out and fs.can_be_paid_out:
                    FixedSavingsService.process_maturity_payout(fs)
                # Auto-renewal if enabled
                if fs.is_mature and fs.auto_renewal_enabled:
                    FixedSavingsService.process_auto_renewal(fs)
            except Exception:
                continue
    except Exception:
        pass