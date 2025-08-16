from decimal import Decimal
import random
import string
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Sum
from djmoney.money import Money

from .models import (
    FeeStructure, FeeRule, DiscountCode, DiscountUsage,
    ReferralProgram, ReferralCode, Referral,
    SubscriptionPlan, UserSubscription, SubscriptionTransaction
)


class FeeService:
    """Service for calculating and applying fees"""
    
    @staticmethod
    def calculate_fee(transaction_type, amount, user=None, discount_code=None):
        """Calculate fee for a transaction based on active fee structures and rules
        
        Args:
            transaction_type: Type of transaction (transfer, withdrawal, etc.)
            amount: Transaction amount (Money object)
            user: User making the transaction (optional)
            discount_code: Discount code string (optional)
            
        Returns:
            dict: Dictionary containing fee details
        """
        # Get active fee structures and rules
        fee_structures = FeeStructure.objects.filter(is_active=True)
        
        # If no fee structures, return zero fee
        if not fee_structures.exists():
            return {
                'fee_amount': Money(0, amount.currency),
                'original_amount': amount,
                'total_amount': amount,
                'discount_applied': False,
                'discount_amount': Money(0, amount.currency),
                'rules_applied': []
            }
        
        # Get applicable rules
        rules = FeeRule.objects.filter(
            fee_structure__in=fee_structures,
            is_active=True
        ).filter(
            Q(transaction_type='all') | Q(transaction_type=transaction_type)
        ).filter(
            Q(min_amount__isnull=True) | Q(min_amount__lte=amount)
        ).filter(
            Q(max_amount__isnull=True) | Q(max_amount__gte=amount)
        ).order_by('-priority')
        
        # Calculate fee based on rules
        fee_amount = Money(0, amount.currency)
        rules_applied = []
        
        for rule in rules:
            rule_fee = Money(0, amount.currency)
            
            if rule.rule_type == 'fixed':
                if rule.fixed_amount:
                    rule_fee = Money(rule.fixed_amount.amount, amount.currency)
            
            elif rule.rule_type == 'percentage':
                if rule.percentage:
                    rule_fee = Money(amount.amount * (rule.percentage / Decimal('100')), amount.currency)
            
            elif rule.rule_type == 'capped_percentage':
                if rule.percentage and rule.cap_amount:
                    calculated_fee = amount.amount * (rule.percentage / Decimal('100'))
                    capped_amount = min(calculated_fee, rule.cap_amount.amount)
                    rule_fee = Money(capped_amount, amount.currency)
            
            elif rule.rule_type == 'minimum_fee':
                if rule.min_fee and fee_amount < rule.min_fee:
                    rule_fee = Money(rule.min_fee.amount - fee_amount.amount, amount.currency)
            
            # Add rule fee to total fee
            if rule_fee.amount > 0:
                fee_amount += rule_fee
                rules_applied.append({
                    'rule_id': str(rule.id),
                    'rule_name': rule.name,
                    'rule_type': rule.rule_type,
                    'fee_amount': rule_fee
                })
        
        # Apply discount if provided
        discount_applied = False
        discount_amount = Money(0, amount.currency)
        
        if discount_code and fee_amount.amount > 0:
            discount_result = FeeService.apply_discount(discount_code, fee_amount, user)
            if discount_result['success']:
                discount_applied = True
                discount_amount = discount_result['discount_amount']
                fee_amount = discount_result['discounted_fee']
        
        # Calculate total amount
        total_amount = amount + fee_amount
        
        return {
            'fee_amount': fee_amount,
            'original_amount': amount,
            'total_amount': total_amount,
            'discount_applied': discount_applied,
            'discount_amount': discount_amount,
            'rules_applied': rules_applied
        }
    
    @staticmethod
    def apply_discount(discount_code_str, fee_amount, user=None):
        """Apply a discount code to a fee
        
        Args:
            discount_code_str: The discount code string
            fee_amount: The fee amount (Money object)
            user: The user applying the discount
            
        Returns:
            dict: Result of discount application
        """
        try:
            discount_code = DiscountCode.objects.get(code=discount_code_str, is_active=True)
            
            # Check if code is valid
            if not discount_code.is_valid:
                return {
                    'success': False,
                    'message': 'Discount code is no longer valid',
                    'discount_amount': Money(0, fee_amount.currency),
                    'discounted_fee': fee_amount
                }
            
            # Check user-specific limits if user is provided
            if user and discount_code.max_uses_per_user:
                user_usage_count = DiscountUsage.objects.filter(
                    discount_code=discount_code,
                    user=user
                ).count()
                
                if user_usage_count >= discount_code.max_uses_per_user:
                    return {
                        'success': False,
                        'message': 'You have reached the maximum usage limit for this code',
                        'discount_amount': Money(0, fee_amount.currency),
                        'discounted_fee': fee_amount
                    }
            
            # Calculate discount
            discount_amount = Money(0, fee_amount.currency)
            
            if discount_code.discount_type == 'fixed' and discount_code.fixed_amount:
                discount_amount = Money(
                    min(discount_code.fixed_amount.amount, fee_amount.amount),
                    fee_amount.currency
                )
            
            elif discount_code.discount_type == 'percentage' and discount_code.percentage:
                discount_amount = Money(
                    fee_amount.amount * (discount_code.percentage / Decimal('100')),
                    fee_amount.currency
                )
            
            elif discount_code.discount_type == 'waive_fee':
                discount_amount = fee_amount
            
            # Calculate discounted fee
            discounted_fee = Money(max(0, fee_amount.amount - discount_amount.amount), fee_amount.currency)
            
            return {
                'success': True,
                'message': 'Discount applied successfully',
                'discount_amount': discount_amount,
                'discounted_fee': discounted_fee,
                'discount_code': discount_code
            }
            
        except DiscountCode.DoesNotExist:
            return {
                'success': False,
                'message': 'Invalid discount code',
                'discount_amount': Money(0, fee_amount.currency),
                'discounted_fee': fee_amount
            }
    
    @staticmethod
    def record_discount_usage(discount_result, user, transaction=None):
        """Record the usage of a discount code
        
        Args:
            discount_result: Result from apply_discount method
            user: User who used the discount
            transaction: Related transaction (optional)
            
        Returns:
            DiscountUsage: The created usage record
        """
        if not discount_result['success']:
            return None
        
        discount_code = discount_result['discount_code']
        
        with transaction.atomic():
            # Increment usage count
            discount_code.uses_count += 1
            discount_code.save()
            
            # Create usage record
            usage = DiscountUsage.objects.create(
                discount_code=discount_code,
                user=user,
                transaction=transaction,
                amount_saved=discount_result['discount_amount']
            )
            
            return usage


class ReferralService:
    """Service for managing referrals"""
    
    @staticmethod
    def generate_referral_code(user, program=None):
        """Generate a unique referral code for a user
        
        Args:
            user: User to generate code for
            program: Specific referral program (optional)
            
        Returns:
            ReferralCode: The created referral code
        """
        # Get active program if not specified
        if not program:
            try:
                program = ReferralProgram.objects.filter(is_active=True).first()
                if not program:
                    return None
            except ReferralProgram.DoesNotExist:
                return None
        
        # Check if user already has a code for this program
        existing_code = ReferralCode.objects.filter(user=user, program=program, is_active=True).first()
        if existing_code:
            return existing_code
        
        # Generate a unique code
        code_length = 8
        while True:
            # Generate random alphanumeric code
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=code_length))
            
            # Check if code already exists
            if not ReferralCode.objects.filter(code=code).exists():
                break
        
        # Create and return the referral code
        referral_code = ReferralCode.objects.create(
            program=program,
            user=user,
            code=code
        )
        
        return referral_code
    
    @staticmethod
    def process_referral(referral_code_str, referee, referrer_ip=None, referee_ip=None, 
                         referrer_device_id=None, referee_device_id=None):
        """Process a referral when a new user signs up
        
        Args:
            referral_code_str: Referral code string
            referee: User who was referred (new user)
            referrer_ip: IP address of referrer (optional)
            referee_ip: IP address of referee (optional)
            referrer_device_id: Device ID of referrer (optional)
            referee_device_id: Device ID of referee (optional)
            
        Returns:
            dict: Result of referral processing
        """
        try:
            # Find the referral code
            referral_code = ReferralCode.objects.get(
                code=referral_code_str,
                is_active=True
            )
            
            # Get the referrer and program
            referrer = referral_code.user
            program = referral_code.program
            
            # Check if program is active
            if not program.is_active:
                return {
                    'success': False,
                    'message': 'Referral program is not active'
                }
            
            # Check if program is within valid dates
            now = timezone.now()
            if program.valid_until and now > program.valid_until:
                return {
                    'success': False,
                    'message': 'Referral program has expired'
                }
            
            # Check if referrer has reached max referrals
            if program.max_referrals_per_user:
                referral_count = Referral.objects.filter(
                    referrer=referrer,
                    program=program,
                    status__in=['verified', 'rewarded']
                ).count()
                
                if referral_count >= program.max_referrals_per_user:
                    return {
                        'success': False,
                        'message': 'Referrer has reached maximum referrals limit'
                    }
            
            # Check if referee is already referred
            existing_referral = Referral.objects.filter(referee=referee).first()
            if existing_referral:
                return {
                    'success': False,
                    'message': 'User has already been referred'
                }
            
            # Create the referral
            referral = Referral.objects.create(
                program=program,
                referral_code=referral_code,
                referrer=referrer,
                referee=referee,
                referrer_ip=referrer_ip,
                referee_ip=referee_ip,
                referrer_device_id=referrer_device_id,
                referee_device_id=referee_device_id,
                status='pending'
            )
            
            # Increment the referral code usage count
            referral_code.times_used += 1
            referral_code.save()
            
            return {
                'success': True,
                'message': 'Referral processed successfully',
                'referral': referral
            }
            
        except ReferralCode.DoesNotExist:
            return {
                'success': False,
                'message': 'Invalid referral code'
            }
    
    @staticmethod
    def verify_referral(referral_id):
        """Verify a referral after fraud checks
        
        Args:
            referral_id: ID of the referral to verify
            
        Returns:
            dict: Result of verification
        """
        try:
            referral = Referral.objects.get(id=referral_id)
            
            # Check if already verified or rewarded
            if referral.status in ['verified', 'rewarded']:
                return {
                    'success': True,
                    'message': 'Referral already verified',
                    'referral': referral
                }
            
            # Check if rejected
            if referral.status == 'rejected':
                return {
                    'success': False,
                    'message': f'Referral was rejected: {referral.rejection_reason}',
                    'referral': referral
                }
            
            # Perform fraud checks
            fraud_check_result = ReferralService._perform_fraud_checks(referral)
            
            if not fraud_check_result['passed']:
                # Reject the referral
                referral.status = 'rejected'
                referral.rejected_at = timezone.now()
                referral.rejection_reason = fraud_check_result['reason']
                referral.save()
                
                return {
                    'success': False,
                    'message': f'Referral verification failed: {fraud_check_result["reason"]}',
                    'referral': referral
                }
            
            # Mark as verified
            referral.status = 'verified'
            referral.verified_at = timezone.now()
            referral.save()
            
            return {
                'success': True,
                'message': 'Referral verified successfully',
                'referral': referral
            }
            
        except Referral.DoesNotExist:
            return {
                'success': False,
                'message': 'Referral not found'
            }
    
    @staticmethod
    def _perform_fraud_checks(referral):
        """Perform fraud checks on a referral
        
        Args:
            referral: Referral object to check
            
        Returns:
            dict: Result of fraud checks
        """
        program = referral.program
        referee = referral.referee
        
        # Check if referrer and referee are the same person
        if referral.referrer == referee:
            return {
                'passed': False,
                'reason': 'Referrer and referee cannot be the same person'
            }
        
        # IP address validation
        if program.ip_address_validation and referral.referrer_ip and referral.referee_ip:
            if referral.referrer_ip == referral.referee_ip:
                return {
                    'passed': False,
                    'reason': 'Referrer and referee have the same IP address'
                }
        
        # Device validation
        if program.device_validation and referral.referrer_device_id and referral.referee_device_id:
            if referral.referrer_device_id == referral.referee_device_id:
                return {
                    'passed': False,
                    'reason': 'Referrer and referee have the same device'
                }
        
        # All checks passed
        return {
            'passed': True
        }
    
    @staticmethod
    def process_reward(referral_id):
        """Process rewards for a verified referral
        
        Args:
            referral_id: ID of the referral to reward
            
        Returns:
            dict: Result of reward processing
        """
        try:
            referral = Referral.objects.get(id=referral_id)
            
            # Check if already rewarded
            if referral.status == 'rewarded':
                return {
                    'success': True,
                    'message': 'Referral already rewarded',
                    'referral': referral
                }
            
            # Check if verified
            if referral.status != 'verified':
                return {
                    'success': False,
                    'message': f'Referral is not verified (status: {referral.status})',
                    'referral': referral
                }
            
            # Get program and users
            program = referral.program
            referrer = referral.referrer
            referee = referral.referee
            
            # Process rewards (this would integrate with your banking/wallet system)
            # For now, we'll just mark it as rewarded
            referral.status = 'rewarded'
            referral.rewarded_at = timezone.now()
            referral.save()
            
            # Here you would add the actual reward to user accounts
            # This is a placeholder for integration with your banking system
            # Example:
            # banking_service.credit_account(referrer.account, program.referrer_reward)
            # banking_service.credit_account(referee.account, program.referee_reward)
            
            return {
                'success': True,
                'message': 'Referral rewarded successfully',
                'referral': referral,
                'referrer_reward': program.referrer_reward,
                'referee_reward': program.referee_reward
            }
            
        except Referral.DoesNotExist:
            return {
                'success': False,
                'message': 'Referral not found'
            }


class SubscriptionService:
    """Service for managing premium subscriptions"""
    
    @staticmethod
    def get_available_plans():
        """Get all available subscription plans
        
        Returns:
            QuerySet: Active subscription plans
        """
        return SubscriptionPlan.objects.filter(is_active=True)
    
    @staticmethod
    def get_user_subscription(user):
        """Get a user's active subscription
        
        Args:
            user: User to check
            
        Returns:
            UserSubscription: User's active subscription or None
        """
        now = timezone.now()
        return UserSubscription.objects.filter(
            user=user,
            status='active',
            start_date__lte=now,
            end_date__gte=now
        ).first()
    
    @staticmethod
    def subscribe_user(user, plan_id, billing_cycle='monthly', payment_reference=None):
        """Subscribe a user to a premium plan
        
        Args:
            user: User to subscribe
            plan_id: ID of the plan to subscribe to
            billing_cycle: 'monthly' or 'annual'
            payment_reference: Payment reference (optional)
            
        Returns:
            dict: Result of subscription
        """
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
            
            # Check if user already has an active subscription
            current_subscription = SubscriptionService.get_user_subscription(user)
            
            if current_subscription:
                # Handle upgrade/downgrade logic here
                return {
                    'success': False,
                    'message': 'User already has an active subscription. Please cancel or upgrade instead.',
                    'subscription': current_subscription
                }
            
            # Calculate subscription period
            start_date = timezone.now()
            if billing_cycle == 'monthly':
                end_date = start_date + timezone.timedelta(days=30)
                amount = plan.monthly_fee
            else:  # annual
                end_date = start_date + timezone.timedelta(days=365)
                amount = plan.annual_fee if plan.annual_fee else plan.monthly_fee * 12
            
            # Create subscription
            with transaction.atomic():
                subscription = UserSubscription.objects.create(
                    user=user,
                    plan=plan,
                    status='active',
                    billing_cycle=billing_cycle,
                    start_date=start_date,
                    end_date=end_date,
                    auto_renew=True
                )
                
                # Record transaction
                SubscriptionTransaction.objects.create(
                    subscription=subscription,
                    transaction_type='new',
                    amount=amount,
                    payment_reference=payment_reference or ''
                )
            
            return {
                'success': True,
                'message': f'Successfully subscribed to {plan.name}',
                'subscription': subscription
            }
            
        except SubscriptionPlan.DoesNotExist:
            return {
                'success': False,
                'message': 'Subscription plan not found'
            }
    
    @staticmethod
    def cancel_subscription(user, subscription_id=None):
        """Cancel a user's subscription
        
        Args:
            user: User whose subscription to cancel
            subscription_id: Specific subscription ID (optional)
            
        Returns:
            dict: Result of cancellation
        """
        # Get subscription to cancel
        if subscription_id:
            try:
                subscription = UserSubscription.objects.get(id=subscription_id, user=user)
            except UserSubscription.DoesNotExist:
                return {
                    'success': False,
                    'message': 'Subscription not found'
                }
        else:
            subscription = SubscriptionService.get_user_subscription(user)
            if not subscription:
                return {
                    'success': False,
                    'message': 'No active subscription found'
                }
        
        # Cancel subscription
        subscription.status = 'cancelled'
        subscription.auto_renew = False
        subscription.save()
        
        # Record transaction
        SubscriptionTransaction.objects.create(
            subscription=subscription,
            transaction_type='cancellation',
            amount=Money(0, subscription.plan.monthly_fee.currency)
        )
        
        return {
            'success': True,
            'message': 'Subscription cancelled successfully',
            'subscription': subscription
        }
    
    @staticmethod
    def renew_subscription(subscription_id, payment_reference=None):
        """Renew a subscription
        
        Args:
            subscription_id: ID of the subscription to renew
            payment_reference: Payment reference (optional)
            
        Returns:
            dict: Result of renewal
        """
        try:
            subscription = UserSubscription.objects.get(id=subscription_id)
            
            # Check if subscription is eligible for renewal
            if subscription.status not in ['active', 'expired']:
                return {
                    'success': False,
                    'message': f'Subscription cannot be renewed (status: {subscription.status})'
                }
            
            # Calculate new period
            if subscription.end_date > timezone.now():
                # If not expired, extend from current end date
                start_date = subscription.end_date
            else:
                # If expired, start from now
                start_date = timezone.now()
            
            if subscription.billing_cycle == 'monthly':
                end_date = start_date + timezone.timedelta(days=30)
                amount = subscription.plan.monthly_fee
            else:  # annual
                end_date = start_date + timezone.timedelta(days=365)
                amount = subscription.plan.annual_fee if subscription.plan.annual_fee else subscription.plan.monthly_fee * 12
            
            # Update subscription
            subscription.status = 'active'
            subscription.start_date = start_date
            subscription.end_date = end_date
            subscription.save()
            
            # Record transaction
            SubscriptionTransaction.objects.create(
                subscription=subscription,
                transaction_type='renewal',
                amount=amount,
                payment_reference=payment_reference or ''
            )
            
            return {
                'success': True,
                'message': 'Subscription renewed successfully',
                'subscription': subscription
            }
            
        except UserSubscription.DoesNotExist:
            return {
                'success': False,
                'message': 'Subscription not found'
            }
    
    @staticmethod
    def check_user_benefit(user, benefit_type):
        """Check if a user has a specific benefit from their subscription
        
        Args:
            user: User to check
            benefit_type: Type of benefit to check for
            
        Returns:
            dict: Benefit details if available
        """
        subscription = SubscriptionService.get_user_subscription(user)
        
        if not subscription:
            return {
                'has_benefit': False,
                'message': 'User has no active subscription'
            }
        
        # Find matching benefit
        benefit = PlanBenefit.objects.filter(
            plan=subscription.plan,
            benefit_type=benefit_type,
            is_active=True
        ).first()
        
        if not benefit:
            return {
                'has_benefit': False,
                'message': f'Subscription does not include {benefit_type} benefit'
            }
        
        return {
            'has_benefit': True,
            'benefit': benefit,
            'value': benefit.value,
            'description': benefit.description
        }