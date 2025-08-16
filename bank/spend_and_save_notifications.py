import logging
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from djmoney.money import Money
from notification.models import Notification, NotificationType, NotificationLevel, NotificationStatus
from .models import SpendAndSaveAccount, SpendAndSaveTransaction, SpendAndSaveSettings

logger = logging.getLogger(__name__)


class SpendAndSaveNotificationService:
    """
    Service for sending notifications related to Spend and Save functionality
    """
    
    @staticmethod
    def send_account_activated_notification(user, account, savings_percentage):
        """Send notification when Spend and Save account is activated"""
        try:
            Notification.objects.create(
                recipient=user,
                title="🎉 Spend and Save Activated!",
                message=f"Your Spend and Save account has been successfully activated with {savings_percentage}% automatic savings. "
                        f"Every time you spend, {savings_percentage}% will be automatically saved to your account {account.account_number}.",
                notification_type=NotificationType.SPEND_AND_SAVE_ACTIVATION,
                level=NotificationLevel.SUCCESS,
                status=NotificationStatus.PENDING,
                source='spend_and_save',
                extra_data={
                    'account_number': account.account_number,
                    'savings_percentage': float(savings_percentage),
                    'balance': str(account.balance),
                    'action_url': '/spend-and-save/dashboard'
                }
            )
            logger.info(f"Account activation notification sent to user {user.username}")
        except Exception as e:
            logger.error(f"Error sending account activation notification: {str(e)}")
    
    @staticmethod
    def send_savings_milestone_notification(user, account, milestone_type, amount):
        """Send notification when user reaches savings milestones"""
        try:
            milestone_messages = {
                'first_save': {
                    'title': "💰 First Save Complete!",
                    'message': f"Congratulations! Your first automatic save of ₦{amount:,.2f} has been processed. "
                              f"Keep spending to save more!",
                    'level': NotificationLevel.SUCCESS
                },
                'hundred_naira': {
                    'title': "🎯 ₦100 Milestone Reached!",
                    'message': f"Great job! You've saved ₦{amount:,.2f} so far. Your savings are growing!",
                    'level': NotificationLevel.SUCCESS
                },
                'five_hundred_naira': {
                    'title': "🎉 ₦500 Milestone Reached!",
                    'message': f"Excellent! You've saved ₦{amount:,.2f} through automatic savings. "
                              f"You're building a great savings habit!",
                    'level': NotificationLevel.SUCCESS
                },
                'thousand_naira': {
                    'title': "🏆 ₦1,000 Milestone Reached!",
                    'message': f"Outstanding! You've saved ₦{amount:,.2f} automatically. "
                              f"Your future self will thank you!",
                    'level': NotificationLevel.SUCCESS
                },
                'five_thousand_naira': {
                    'title': "💎 ₦5,000 Milestone Reached!",
                    'message': f"Fantastic! You've saved ₦{amount:,.2f} through smart spending. "
                              f"You're a savings champion!",
                    'level': NotificationLevel.SUCCESS
                },
                'ten_thousand_naira': {
                    'title': "👑 ₦10,000 Milestone Reached!",
                    'message': f"Amazing! You've saved ₦{amount:,.2f} automatically. "
                              f"You're building real wealth through smart spending!",
                    'level': NotificationLevel.SUCCESS
                }
            }
            
            if milestone_type in milestone_messages:
                message_data = milestone_messages[milestone_type]
                Notification.objects.create(
                    recipient=user,
                    title=message_data['title'],
                    message=message_data['message'],
                    notification_type=NotificationType.SAVINGS_MILESTONE,
                    level=message_data['level'],
                    status=NotificationStatus.PENDING,
                    source='spend_and_save',
                    extra_data={
                        'milestone_type': milestone_type,
                        'amount': float(amount),
                        'account_number': account.account_number,
                        'action_url': '/spend-and-save/dashboard'
                    }
                )
                logger.info(f"Savings milestone notification sent to user {user.username}: {milestone_type}")
        except Exception as e:
            logger.error(f"Error sending savings milestone notification: {str(e)}")
    
    @staticmethod
    def send_interest_credited_notification(user, account, interest_amount, total_interest):
        """Send notification when interest is credited"""
        try:
            Notification.objects.create(
                recipient=user,
                title="💸 Interest Credited!",
                message=f"Great news! ₦{interest_amount:,.2f} in interest has been credited to your Spend and Save account. "
                        f"Total interest earned: ₦{total_interest:,.2f}",
                notification_type=NotificationType.INTEREST_CREDITED,
                level=NotificationLevel.SUCCESS,
                status=NotificationStatus.PENDING,
                source='spend_and_save',
                extra_data={
                    'interest_amount': float(interest_amount),
                    'total_interest': float(total_interest),
                    'account_number': account.account_number,
                    'action_url': '/spend-and-save/interest'
                }
            )
            logger.info(f"Interest credited notification sent to user {user.username}")
        except Exception as e:
            logger.error(f"Error sending interest credited notification: {str(e)}")
    
    @staticmethod
    def send_withdrawal_notification(user, account, amount, destination):
        """Send notification when funds are withdrawn from Spend and Save"""
        try:
            destination_text = "your wallet" if destination == 'wallet' else "your XySave account"
            Notification.objects.create(
                recipient=user,
                title="💳 Withdrawal Successful",
                message=f"₦{amount:,.2f} has been withdrawn from your Spend and Save account to {destination_text}. "
                        f"Current balance: ₦{account.balance.amount:,.2f}",
                notification_type=NotificationType.SAVINGS_WITHDRAWAL,
                level=NotificationLevel.INFO,
                status=NotificationStatus.PENDING,
                source='spend_and_save',
                extra_data={
                    'withdrawal_amount': float(amount),
                    'destination': destination,
                    'account_number': account.account_number,
                    'action_url': '/spend-and-save/transactions'
                }
            )
            logger.info(f"Withdrawal notification sent to user {user.username}")
        except Exception as e:
            logger.error(f"Error sending withdrawal notification: {str(e)}")
    
    @staticmethod
    def send_spending_save_notification(user, account, transaction_amount, saved_amount, total_saved):
        """Send notification when automatic save occurs from spending"""
        try:
            Notification.objects.create(
                recipient=user,
                title="💾 Automatic Save Complete",
                message=f"From your ₦{transaction_amount:,.2f} spending, ₦{saved_amount:,.2f} has been automatically saved. "
                        f"Total saved from spending: ₦{total_saved:,.2f}",
                notification_type=NotificationType.AUTOMATIC_SAVE,
                level=NotificationLevel.INFO,
                status=NotificationStatus.PENDING,
                source='spend_and_save',
                extra_data={
                    'transaction_amount': float(transaction_amount),
                    'saved_amount': float(saved_amount),
                    'total_saved': float(total_saved),
                    'account_number': account.account_number,
                    'action_url': '/spend-and-save/dashboard'
                }
            )
            logger.info(f"Spending save notification sent to user {user.username}")
        except Exception as e:
            logger.error(f"Error sending spending save notification: {str(e)}")
    
    @staticmethod
    def send_account_deactivated_notification(user, account):
        """Send notification when Spend and Save account is deactivated"""
        try:
            Notification.objects.create(
                recipient=user,
                title="⏸️ Spend and Save Deactivated",
                message=f"Your Spend and Save account has been deactivated. "
                        f"Your balance of ₦{account.balance.amount:,.2f} remains safe and accessible.",
                notification_type=NotificationType.SPEND_AND_SAVE_DEACTIVATION,
                level=NotificationLevel.WARNING,
                status=NotificationStatus.PENDING,
                source='spend_and_save',
                extra_data={
                    'account_number': account.account_number,
                    'final_balance': str(account.balance),
                    'action_url': '/spend-and-save/reactivate'
                }
            )
            logger.info(f"Account deactivation notification sent to user {user.username}")
        except Exception as e:
            logger.error(f"Error sending account deactivation notification: {str(e)}")

    @staticmethod
    def send_weekly_savings_summary(user, account, weekly_stats):
        """Send weekly savings summary notification"""
        try:
            total_spent = weekly_stats.get('total_spent', 0)
            total_saved = weekly_stats.get('total_saved', 0)
            transactions_count = weekly_stats.get('transactions_count', 0)

            Notification.objects.create(
                recipient=user,
                title="📊 Weekly Savings Summary",
                message=f"This week you spent ₦{total_spent:,.2f} and automatically saved ₦{total_saved:,.2f} "
                        f"from {transactions_count} transactions. Keep up the great work!",
                notification_type=NotificationType.WEEKLY_SAVINGS_SUMMARY,
                level=NotificationLevel.INFO,
                status=NotificationStatus.PENDING,
                source='spend_and_save',
                extra_data={
                    'weekly_stats': weekly_stats,
                    'account_number': account.account_number,
                    'action_url': '/spend-and-save/weekly-summary'
                }
            )
            logger.info(f"Weekly savings summary notification sent to user {user.username}")
        except Exception as e:
            logger.error(f"Error sending weekly savings summary notification: {str(e)}")
    
    @staticmethod
    def send_goal_achievement_notification(user, account, goal_amount, current_amount):
        """Send notification when user achieves a savings goal"""
        try:
            Notification.objects.create(
                recipient=user,
                title="🎯 Savings Goal Achieved!",
                message=f"Congratulations! You've reached your savings goal of ₦{goal_amount:,.2f}. "
                        f"Current balance: ₦{current_amount:,.2f}. Time to set a new goal!",
                notification_type=NotificationType.SAVINGS_GOAL_ACHIEVED,
                level=NotificationLevel.SUCCESS,
                status=NotificationStatus.PENDING,
                source='spend_and_save',
                extra_data={
                    'goal_amount': float(goal_amount),
                    'current_amount': float(current_amount),
                    'account_number': account.account_number,
                    'action_url': '/spend-and-save/goals'
                }
            )
            logger.info(f"Goal achievement notification sent to user {user.username}")
        except Exception as e:
            logger.error(f"Error sending goal achievement notification: {str(e)}")
    
    @staticmethod
    def check_and_send_milestone_notifications(user, account):
        """Check if user has reached any savings milestones and send notifications"""
        try:
            total_saved = account.total_saved_from_spending.amount
            
            # Define milestones
            milestones = [
                (100, 'hundred_naira'),
                (500, 'five_hundred_naira'),
                (1000, 'thousand_naira'),
                (5000, 'five_thousand_naira'),
                (10000, 'ten_thousand_naira')
            ]
            
            for milestone_amount, milestone_type in milestones:
                if total_saved >= milestone_amount:
                    # Check if we've already sent this milestone notification
                    existing_notification = Notification.objects.filter(
                        recipient=user,
                        source='spend_and_save',
                        extra_data__milestone_type=milestone_type
                    ).first()
                    
                    if not existing_notification:
                        SpendAndSaveNotificationService.send_savings_milestone_notification(
                            user, account, milestone_type, total_saved
                        )
                        break  # Only send one milestone at a time
                        
        except Exception as e:
            logger.error(f"Error checking milestone notifications: {str(e)}") 