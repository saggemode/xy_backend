import logging
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from djmoney.money import Money
from notification.models import Notification, NotificationType, NotificationLevel, NotificationStatus
from .models import TargetSaving, TargetSavingDeposit, TargetSavingCategory, TargetSavingFrequency

logger = logging.getLogger(__name__)


class TargetSavingService:
    """
    Service for managing target savings with notification integration
    """
    
    @staticmethod
    def _validate_sufficient_funds(user, amount, source):
        """
        Validate that the user has sufficient funds in the selected source
        Similar to FixedSavingsService._validate_sufficient_funds
        """
        from .models import Wallet, XySaveAccount, TargetSavingSource
        
        try:
            wallet = Wallet.objects.get(user=user)
            
            if source == TargetSavingSource.WALLET:
                return wallet.balance.amount >= amount
            
            elif source == TargetSavingSource.XYSAVE:
                try:
                    xysave = XySaveAccount.objects.get(user=user)
                    return xysave.balance.amount >= amount
                except XySaveAccount.DoesNotExist:
                    return False
            
            elif source == TargetSavingSource.BOTH:
                try:
                    xysave = XySaveAccount.objects.get(user=user)
                    half_amount = amount / 2
                    return (wallet.balance.amount >= half_amount and 
                            xysave.balance.amount >= half_amount)
                except XySaveAccount.DoesNotExist:
                    return False
            
            return False
        
        except Wallet.DoesNotExist:
            return False
    
    @staticmethod
    def create_target_saving(user, **kwargs):
        """Create a new target saving"""
        try:
            with transaction.atomic():
                # Validate required fields
                required_fields = ['name', 'category', 'target_amount', 'frequency', 'start_date', 'end_date']
                for field in required_fields:
                    if field not in kwargs:
                        raise ValidationError(f"Missing required field: {field}")
                
                # Validate frequency and preferred deposit day
                frequency = kwargs.get('frequency')
                preferred_deposit_day = kwargs.get('preferred_deposit_day')
                
                if frequency in [TargetSavingFrequency.WEEKLY, TargetSavingFrequency.MONTHLY]:
                    if not preferred_deposit_day:
                        raise ValidationError("Preferred deposit day is required for weekly/monthly frequency")
                
                # Get optional enhanced fields
                source = kwargs.get('source', 'wallet')  # Default to wallet if not specified
                strict_mode = kwargs.get('strict_mode', False)  # Default to non-strict if not specified
                
                # Validate source if provided
                from .models import Wallet, XySaveAccount, TargetSavingSource
                
                # Validate that the user has sufficient funds in the selected source
                if not TargetSavingService._validate_sufficient_funds(user, kwargs['target_amount'], source):
                    raise ValidationError(f'Insufficient funds in {source} for target saving')
                
                # Generate a unique account number
                import random
                account_number = f"TS{str(user.id)[:4]}{random.randint(100000, 999999)}"
                while TargetSaving.objects.filter(account_number=account_number).exists():
                    account_number = f"TS{str(user.id)[:4]}{random.randint(100000, 999999)}"
                
                # Create target saving
                target_saving = TargetSaving.objects.create(
                    user=user,
                    name=kwargs['name'],
                    category=kwargs['category'],
                    target_amount=kwargs['target_amount'],
                    frequency=frequency,
                    preferred_deposit_day=preferred_deposit_day,
                    start_date=kwargs['start_date'],
                    end_date=kwargs['end_date'],
                    account_number=account_number,
                    source=source,
                    strict_mode=strict_mode
                )
                
                # Send creation notification
                TargetSavingNotificationService.send_target_created_notification(user, target_saving)
                
                logger.info(f"Target saving created for user {user.username}: {target_saving.name}")
                
                return {
                    'success': True,
                    'target_saving': target_saving,
                    'message': 'Target saving created successfully'
                }
                
        except Exception as e:
            logger.error(f"Error creating target saving: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def update_target_saving(user, target_id, **kwargs):
        """Update an existing target saving"""
        try:
            with transaction.atomic():
                target_saving = TargetSaving.objects.get(id=target_id, user=user)
                
                # Update fields
                for field, value in kwargs.items():
                    if hasattr(target_saving, field):
                        setattr(target_saving, field, value)
                
                target_saving.save()
                
                # Send update notification
                TargetSavingNotificationService.send_target_updated_notification(user, target_saving)
                
                logger.info(f"Target saving updated for user {user.username}: {target_saving.name}")
                
                return {
                    'success': True,
                    'target_saving': target_saving,
                    'message': 'Target saving updated successfully'
                }
                
        except TargetSaving.DoesNotExist:
            return {
                'success': False,
                'message': 'Target saving not found'
            }
        except Exception as e:
            logger.error(f"Error updating target saving: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def make_deposit(user, target_id, amount, notes=""):
        """Make a deposit to a target saving"""
        try:
            with transaction.atomic():
                target_saving = TargetSaving.objects.get(id=target_id, user=user)
                
                if not target_saving.is_active:
                    raise ValidationError("Target saving is not active")
                
                if target_saving.is_completed:
                    raise ValidationError("Target saving is already completed")
                
                # Handle deposit based on source
                from .models import Wallet, XySaveAccount, TargetSavingSource
                
                # Validate that the user has sufficient funds in the selected source
                if not TargetSavingService._validate_sufficient_funds(user, amount, target_saving.source):
                    raise ValidationError(f'Insufficient funds in {target_saving.source} for deposit')
                
                # Process the withdrawal from appropriate source(s)
                wallet = Wallet.objects.get(user=user)
                
                if target_saving.source == TargetSavingSource.WALLET:
                    wallet.balance.amount -= amount
                    wallet.balance.save()
                    
                elif target_saving.source == TargetSavingSource.XYSAVE:
                    xysave = XySaveAccount.objects.get(user=user)
                    xysave.balance.amount -= amount
                    xysave.balance.save()
                    
                elif target_saving.source == TargetSavingSource.BOTH:
                    half_amount = amount / 2
                    xysave = XySaveAccount.objects.get(user=user)
                    
                    wallet.balance.amount -= half_amount
                    wallet.balance.save()
                    
                    xysave.balance.amount -= half_amount
                    xysave.balance.save()
                
                # Create deposit
                deposit = TargetSavingDeposit.objects.create(
                    target_saving=target_saving,
                    amount=amount,
                    notes=notes,
                    source=target_saving.source  # Record the source used for this deposit
                )
                
                # Send deposit notification
                TargetSavingNotificationService.send_deposit_notification(user, target_saving, deposit)
                
                # Check for milestones
                TargetSavingNotificationService.check_and_send_milestone_notifications(user, target_saving)
                
                # Check if target is completed
                if target_saving.is_completed:
                    TargetSavingNotificationService.send_target_completed_notification(user, target_saving)
                
                logger.info(f"Deposit made to target saving {target_saving.name}: {amount}")
                
                return {
                    'success': True,
                    'deposit': deposit,
                    'target_saving': target_saving,
                    'message': 'Deposit made successfully'
                }
                
        except TargetSaving.DoesNotExist:
            return {
                'success': False,
                'message': 'Target saving not found'
            }
        except Exception as e:
            logger.error(f"Error making deposit: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def get_user_targets(user, active_only=True):
        """Get all target savings for a user"""
        try:
            queryset = TargetSaving.objects.filter(user=user)
            if active_only:
                queryset = queryset.filter(is_active=True)
            
            return {
                'success': True,
                'targets': queryset,
                'count': queryset.count()
            }
        except Exception as e:
            logger.error(f"Error getting user targets: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def get_target_details(user, target_id):
        """Get detailed information about a target saving"""
        try:
            target_saving = TargetSaving.objects.get(id=target_id, user=user)
            
            # Get recent deposits
            recent_deposits = target_saving.deposits.all()[:10]
            
            return {
                'success': True,
                'target_saving': target_saving,
                'recent_deposits': recent_deposits,
                'total_deposits': target_saving.deposits.count(),
                'progress_percentage': target_saving.progress_percentage,
                'remaining_amount': target_saving.remaining_amount,
                'days_remaining': target_saving.days_remaining
            }
        except TargetSaving.DoesNotExist:
            return {
                'success': False,
                'message': 'Target saving not found'
            }
        except Exception as e:
            logger.error(f"Error getting target details: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def deactivate_target(user, target_id):
        """Deactivate a target saving"""
        try:
            with transaction.atomic():
                target_saving = TargetSaving.objects.get(id=target_id, user=user)
                target_saving.is_active = False
                target_saving.save()
                
                # Send deactivation notification
                TargetSavingNotificationService.send_target_deactivated_notification(user, target_saving)
                
                logger.info(f"Target saving deactivated for user {user.username}: {target_saving.name}")
                
                return {
                    'success': True,
                    'message': 'Target saving deactivated successfully'
                }
                
        except TargetSaving.DoesNotExist:
            return {
                'success': False,
                'message': 'Target saving not found'
            }
        except Exception as e:
            logger.error(f"Error deactivating target saving: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def get_target_analytics(user, target_id):
        """Get analytics for a target saving"""
        try:
            target_saving = TargetSaving.objects.get(id=target_id, user=user)
            
            # Calculate analytics
            total_deposits = target_saving.deposits.count()
            average_deposit = target_saving.deposits.aggregate(
                avg_amount=models.Avg('amount')
            )['avg_amount'] or 0
            
            # Get deposit frequency
            if total_deposits > 0:
                days_since_start = (timezone.now().date() - target_saving.start_date).days
                deposit_frequency = days_since_start / total_deposits if total_deposits > 0 else 0
            else:
                deposit_frequency = 0
            
            return {
                'success': True,
                'analytics': {
                    'total_deposits': total_deposits,
                    'average_deposit': average_deposit,
                    'deposit_frequency': deposit_frequency,
                    'progress_percentage': target_saving.progress_percentage,
                    'remaining_amount': target_saving.remaining_amount,
                    'days_remaining': target_saving.days_remaining,
                    'is_overdue': target_saving.is_overdue,
                    'daily_target': target_saving.daily_target,
                    'weekly_target': target_saving.weekly_target,
                    'monthly_target': target_saving.monthly_target
                }
            }
        except TargetSaving.DoesNotExist:
            return {
                'success': False,
                'message': 'Target saving not found'
            }
        except Exception as e:
            logger.error(f"Error getting target analytics: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }


    @staticmethod
    def withdraw_from_target(user, target_id, amount, destination='wallet'):
        """Withdraw from a target saving"""
        try:
            with transaction.atomic():
                target_saving = TargetSaving.objects.get(id=target_id, user=user)
                
                # Validate target saving is active
                if not target_saving.is_active:
                    return {
                        'success': False,
                        'message': 'Cannot withdraw from an inactive target saving'
                    }
                
                # Validate amount
                if amount <= 0:
                    return {
                        'success': False,
                        'message': 'Withdrawal amount must be greater than zero'
                    }
                
                # Validate sufficient funds
                if amount > target_saving.current_amount:
                    return {
                        'success': False,
                        'message': 'Insufficient funds in target saving'
                    }
                
                # Process withdrawal
                target_saving.current_amount -= amount
                target_saving.save()
                
                # Credit user's wallet or XySave based on destination
                if destination == 'wallet':
                    user.wallet.balance += amount
                    user.wallet.save()
                    destination_account = 'wallet'
                elif destination == 'xysave':
                    xysave_account = user.xysave_account
                    if not xysave_account:
                        return {
                            'success': False,
                            'message': 'User does not have an XySave account'
                        }
                    xysave_account.balance += amount
                    xysave_account.save()
                    destination_account = 'xysave'
                else:
                    return {
                        'success': False,
                        'message': 'Invalid destination account'
                    }
                
                # Create withdrawal record
                withdrawal = TargetSavingWithdrawal.objects.create(
                    target_saving=target_saving,
                    amount=amount,
                    withdrawal_date=timezone.now(),
                    destination=destination_account,
                    notes=f'Withdrawal to {destination_account}'
                )
                
                # Send withdrawal notification
                TargetSavingNotificationService.send_withdrawal_notification(
                    user, target_saving, withdrawal
                )
                
                logger.info(f"Withdrawal of {amount} from target saving {target_saving.name} for user {user.username}")
                
                return {
                    'success': True,
                    'message': f'Successfully withdrew {amount} from target saving',
                    'withdrawal': withdrawal
                }
                
        except TargetSaving.DoesNotExist:
            return {
                'success': False,
                'message': 'Target saving not found'
            }
        except Exception as e:
            logger.error(f"Error withdrawing from target saving: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }


class TargetSavingNotificationService:
    """
    Service for sending notifications related to Target Saving functionality
    """
    
    @staticmethod
    def send_target_created_notification(user, target_saving):
        """Send notification when target saving is created"""
        try:
            Notification.objects.create(
                recipient=user,
                title="🎯 New Target Saving Created!",
                message=f"Your target '{target_saving.name}' has been created successfully. "
                        f"Target amount: ₦{target_saving.target_amount:,.2f}, "
                        f"End date: {target_saving.end_date.strftime('%B %d, %Y')}",
                notification_type=NotificationType.TARGET_SAVING_CREATED,
                level=NotificationLevel.SUCCESS,
                status=NotificationStatus.PENDING,
                source='target_saving',
                extra_data={
                    'target_id': str(target_saving.id),
                    'target_name': target_saving.name,
                    'target_amount': float(target_saving.target_amount),
                    'category': target_saving.category,
                    'frequency': target_saving.frequency,
                    'end_date': target_saving.end_date.isoformat(),
                    'action_url': f'/target-savings/{target_saving.id}'
                }
            )
            logger.info(f"Target created notification sent to user {user.username}")
        except Exception as e:
            logger.error(f"Error sending target created notification: {str(e)}")
    
    @staticmethod
    def send_target_updated_notification(user, target_saving):
        """Send notification when target saving is updated"""
        try:
            Notification.objects.create(
                recipient=user,
                title="📝 Target Saving Updated",
                message=f"Your target '{target_saving.name}' has been updated successfully. "
                        f"Current progress: {target_saving.progress_percentage:.1f}%",
                notification_type=NotificationType.TARGET_SAVING_UPDATED,
                level=NotificationLevel.INFO,
                status=NotificationStatus.PENDING,
                source='target_saving',
                extra_data={
                    'target_id': str(target_saving.id),
                    'target_name': target_saving.name,
                    'progress_percentage': float(target_saving.progress_percentage),
                    'current_amount': float(target_saving.current_amount),
                    'action_url': f'/target-savings/{target_saving.id}'
                }
            )
            logger.info(f"Target updated notification sent to user {user.username}")
        except Exception as e:
            logger.error(f"Error sending target updated notification: {str(e)}")
    
    @staticmethod
    def send_target_completed_notification(user, target_saving):
        """Send notification when target saving is completed"""
        try:
            Notification.objects.create(
                recipient=user,
                title="🎉 Target Saving Completed!",
                message=f"Congratulations! You've successfully completed your target '{target_saving.name}'. "
                        f"Final amount saved: ₦{target_saving.current_amount:,.2f}",
                notification_type=NotificationType.TARGET_SAVING_COMPLETED,
                level=NotificationLevel.SUCCESS,
                status=NotificationStatus.PENDING,
                source='target_saving',
                extra_data={
                    'target_id': str(target_saving.id),
                    'target_name': target_saving.name,
                    'final_amount': float(target_saving.current_amount),
                    'target_amount': float(target_saving.target_amount),
                    'action_url': f'/target-savings/{target_saving.id}'
                }
            )
            logger.info(f"Target completed notification sent to user {user.username}")
        except Exception as e:
            logger.error(f"Error sending target completed notification: {str(e)}")
    
    @staticmethod
    def send_deposit_notification(user, target_saving, deposit):
        """Send notification when a deposit is made"""
        try:
            Notification.objects.create(
                recipient=user,
                title="💰 Deposit Made to Target",
                message=f"₦{deposit.amount:,.2f} deposited to '{target_saving.name}'. "
                        f"Progress: {target_saving.progress_percentage:.1f}% "
                        f"({target_saving.current_amount:,.2f}/{target_saving.target_amount:,.2f})",
                notification_type=NotificationType.TARGET_SAVING_DEPOSIT,
                level=NotificationLevel.SUCCESS,
                status=NotificationStatus.PENDING,
                source='target_saving',
                extra_data={
                    'target_id': str(target_saving.id),
                    'target_name': target_saving.name,
                    'deposit_amount': float(deposit.amount),
                    'progress_percentage': float(target_saving.progress_percentage),
                    'current_amount': float(target_saving.current_amount),
                    'remaining_amount': float(target_saving.remaining_amount),
                    'action_url': f'/target-savings/{target_saving.id}'
                }
            )
            logger.info(f"Deposit notification sent to user {user.username}")
        except Exception as e:
            logger.error(f"Error sending deposit notification: {str(e)}")
    
    @staticmethod
    def send_milestone_notification(user, target_saving, milestone_type, progress_percentage):
        """Send notification when target saving reaches milestones"""
        try:
            milestone_messages = {
                'quarter': {
                    'title': "🎯 25% Target Milestone!",
                    'message': f"Great progress! You've reached 25% of your target '{target_saving.name}'. "
                              f"Keep up the excellent work!",
                    'level': NotificationLevel.SUCCESS
                },
                'half': {
                    'title': "🏆 50% Target Milestone!",
                    'message': f"Outstanding! You're halfway to your target '{target_saving.name}'. "
                              f"You're doing amazing!",
                    'level': NotificationLevel.SUCCESS
                },
                'three_quarters': {
                    'title': "💎 75% Target Milestone!",
                    'message': f"Fantastic! You're 75% of the way to your target '{target_saving.name}'. "
                              f"Almost there!",
                    'level': NotificationLevel.SUCCESS
                },
                'ninety': {
                    'title': "🔥 90% Target Milestone!",
                    'message': f"Incredible! You're 90% of the way to your target '{target_saving.name}'. "
                              f"Final stretch!",
                    'level': NotificationLevel.SUCCESS
                }
            }
            
            if milestone_type in milestone_messages:
                message_data = milestone_messages[milestone_type]
                Notification.objects.create(
                    recipient=user,
                    title=message_data['title'],
                    message=message_data['message'],
                    notification_type=NotificationType.TARGET_SAVING_MILESTONE,
                    level=message_data['level'],
                    status=NotificationStatus.PENDING,
                    source='target_saving',
                    extra_data={
                        'target_id': str(target_saving.id),
                        'target_name': target_saving.name,
                        'milestone_type': milestone_type,
                        'progress_percentage': float(progress_percentage),
                        'current_amount': float(target_saving.current_amount),
                        'action_url': f'/target-savings/{target_saving.id}'
                    }
                )
                logger.info(f"Target milestone notification sent to user {user.username}: {milestone_type}")
        except Exception as e:
            logger.error(f"Error sending target milestone notification: {str(e)}")
    
    @staticmethod
    def check_and_send_milestone_notifications(user, target_saving):
        """Check if target has reached milestones and send notifications"""
        try:
            progress_percentage = target_saving.progress_percentage
            
            # Define milestones
            milestones = [
                (25, 'quarter'),
                (50, 'half'),
                (75, 'three_quarters'),
                (90, 'ninety')
            ]
            
            for milestone_percentage, milestone_type in milestones:
                if progress_percentage >= milestone_percentage:
                    # Check if we've already sent this milestone notification
                    existing_notification = Notification.objects.filter(
                        recipient=user,
                        source='target_saving',
                        extra_data__milestone_type=milestone_type,
                        extra_data__target_id=str(target_saving.id)
                    ).first()
                    
                    if not existing_notification:
                        TargetSavingNotificationService.send_milestone_notification(
                            user, target_saving, milestone_type, progress_percentage
                        )
                        break  # Only send one milestone at a time
                        
        except Exception as e:
            logger.error(f"Error checking target milestone notifications: {str(e)}")
    
    @staticmethod
    def send_target_overdue_notification(user, target_saving):
        """Send notification when target saving is overdue"""
        try:
            Notification.objects.create(
                recipient=user,
                title="⚠️ Target Saving Overdue",
                message=f"Your target '{target_saving.name}' is overdue. "
                        f"End date was {target_saving.end_date.strftime('%B %d, %Y')}. "
                        f"Current progress: {target_saving.progress_percentage:.1f}%",
                notification_type=NotificationType.TARGET_SAVING_OVERDUE,
                level=NotificationLevel.WARNING,
                status=NotificationStatus.PENDING,
                source='target_saving',
                extra_data={
                    'target_id': str(target_saving.id),
                    'target_name': target_saving.name,
                    'end_date': target_saving.end_date.isoformat(),
                    'progress_percentage': float(target_saving.progress_percentage),
                    'remaining_amount': float(target_saving.remaining_amount),
                    'action_url': f'/target-savings/{target_saving.id}'
                }
            )
            logger.info(f"Target overdue notification sent to user {user.username}")
        except Exception as e:
            logger.error(f"Error sending target overdue notification: {str(e)}")
    
    @staticmethod
    def send_target_reminder_notification(user, target_saving, reminder_type):
        """Send reminder notifications for target savings"""
        try:
            reminder_messages = {
                'weekly': {
                    'title': "📅 Weekly Target Reminder",
                    'message': f"Don't forget to contribute to your target '{target_saving.name}'. "
                              f"Progress: {target_saving.progress_percentage:.1f}%",
                    'level': NotificationLevel.INFO
                },
                'monthly': {
                    'title': "📅 Monthly Target Reminder",
                    'message': f"Monthly reminder for your target '{target_saving.name}'. "
                              f"Progress: {target_saving.progress_percentage:.1f}%",
                    'level': NotificationLevel.INFO
                },
                'deadline': {
                    'title': "⏰ Target Deadline Approaching",
                    'message': f"Your target '{target_saving.name}' deadline is approaching. "
                              f"Days remaining: {target_saving.days_remaining}",
                    'level': NotificationLevel.WARNING
                }
            }
            
            if reminder_type in reminder_messages:
                message_data = reminder_messages[reminder_type]
                Notification.objects.create(
                    recipient=user,
                    title=message_data['title'],
                    message=message_data['message'],
                    notification_type=NotificationType.TARGET_SAVING_REMINDER,
                    level=message_data['level'],
                    status=NotificationStatus.PENDING,
                    source='target_saving',
                    extra_data={
                        'target_id': str(target_saving.id),
                        'target_name': target_saving.name,
                        'reminder_type': reminder_type,
                        'progress_percentage': float(target_saving.progress_percentage),
                        'days_remaining': target_saving.days_remaining,
                        'action_url': f'/target-savings/{target_saving.id}'
                    }
                )
                logger.info(f"Target reminder notification sent to user {user.username}: {reminder_type}")
        except Exception as e:
            logger.error(f"Error sending target reminder notification: {str(e)}")
    
    @staticmethod
    def send_target_deactivated_notification(user, target_saving):
        """Send notification when target saving is deactivated"""
        try:
            Notification.objects.create(
                recipient=user,
                title="⏸️ Target Saving Deactivated",
                message=f"Your target '{target_saving.name}' has been deactivated. "
                        f"Final progress: {target_saving.progress_percentage:.1f}% "
                        f"({target_saving.current_amount:,.2f}/{target_saving.target_amount:,.2f})",
                notification_type=NotificationType.TARGET_SAVING_UPDATED,
                level=NotificationLevel.WARNING,
                status=NotificationStatus.PENDING,
                source='target_saving',
                extra_data={
                    'target_id': str(target_saving.id),
                    'target_name': target_saving.name,
                    'final_progress': float(target_saving.progress_percentage),
                    'final_amount': float(target_saving.current_amount),
                    'action_url': f'/target-savings/{target_saving.id}'
                }
            )
            logger.info(f"Target deactivated notification sent to user {user.username}")
        except Exception as e:
            logger.error(f"Error sending target deactivated notification: {str(e)}")
    
    @staticmethod
    def send_withdrawal_notification(user, target_saving, withdrawal):
        """Send notification when a withdrawal is made from target saving"""
        try:
            Notification.objects.create(
                recipient=user,
                title="💸 Withdrawal from Target Saving",
                message=f"₦{withdrawal.amount:,.2f} withdrawn from '{target_saving.name}'. "
                        f"New balance: ₦{target_saving.current_amount:,.2f} "
                        f"Progress: {target_saving.progress_percentage:.1f}%",
                notification_type=NotificationType.TARGET_SAVING_WITHDRAWAL,
                level=NotificationLevel.INFO,
                status=NotificationStatus.PENDING,
                source='target_saving',
                extra_data={
                    'target_id': str(target_saving.id),
                    'target_name': target_saving.name,
                    'withdrawal_amount': float(withdrawal.amount),
                    'destination': withdrawal.destination,
                    'current_amount': float(target_saving.current_amount),
                    'progress_percentage': float(target_saving.progress_percentage),
                    'action_url': f'/target-savings/{target_saving.id}'
                }
            )
            logger.info(f"Withdrawal notification sent to user {user.username}")
        except Exception as e:
            logger.error(f"Error sending withdrawal notification: {str(e)}")
