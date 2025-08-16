from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from djmoney.money import Money

from .models import (
    FeeStructure, FeeRule, DiscountCode, DiscountUsage,
    ReferralProgram, ReferralCode, Referral,
    SubscriptionPlan, PlanBenefit, UserSubscription, SubscriptionTransaction
)
from .serializers import (
    FeeStructureSerializer, FeeRuleSerializer, 
    DiscountCodeSerializer, DiscountUsageSerializer,
    ReferralProgramSerializer, ReferralCodeSerializer, ReferralSerializer,
    SubscriptionPlanSerializer, PlanBenefitSerializer, 
    UserSubscriptionSerializer, SubscriptionTransactionSerializer,
    CalculateFeeSerializer, ApplyDiscountSerializer, 
    ProcessReferralSerializer, SubscribeUserSerializer
)
from .services import FeeService, ReferralService, SubscriptionService


class FeeStructureViewSet(viewsets.ModelViewSet):
    queryset = FeeStructure.objects.all()
    serializer_class = FeeStructureSerializer
    permission_classes = [permissions.IsAdminUser]


class FeeRuleViewSet(viewsets.ModelViewSet):
    queryset = FeeRule.objects.all()
    serializer_class = FeeRuleSerializer
    permission_classes = [permissions.IsAdminUser]
    filterset_fields = ['fee_structure', 'rule_type', 'transaction_type', 'is_active']


class DiscountCodeViewSet(viewsets.ModelViewSet):
    queryset = DiscountCode.objects.all()
    serializer_class = DiscountCodeSerializer
    permission_classes = [permissions.IsAdminUser]
    filterset_fields = ['discount_type', 'is_active']
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def apply(self, request, pk=None):
        """Apply a discount code to a fee"""
        serializer = ApplyDiscountSerializer(data=request.data)
        if serializer.is_valid():
            fee_amount = Money(
                serializer.validated_data['fee_amount'],
                serializer.validated_data['currency']
            )
            
            discount_result = FeeService.apply_discount(
                discount_code_str=pk,  # Using the URL parameter as the code
                fee_amount=fee_amount,
                user=request.user
            )
            
            return Response({
                'success': discount_result['success'],
                'message': discount_result['message'],
                'discount_amount': {
                    'amount': discount_result['discount_amount'].amount,
                    'currency': discount_result['discount_amount'].currency.code
                },
                'discounted_fee': {
                    'amount': discount_result['discounted_fee'].amount,
                    'currency': discount_result['discounted_fee'].currency.code
                }
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DiscountUsageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DiscountUsage.objects.all()
    serializer_class = DiscountUsageSerializer
    permission_classes = [permissions.IsAdminUser]
    filterset_fields = ['discount_code', 'user']
    
    def get_queryset(self):
        # Regular users can only see their own discount usages
        if not self.request.user.is_staff:
            return DiscountUsage.objects.filter(user=self.request.user)
        return super().get_queryset()


class ReferralProgramViewSet(viewsets.ModelViewSet):
    queryset = ReferralProgram.objects.all()
    serializer_class = ReferralProgramSerializer
    permission_classes = [permissions.IsAdminUser]
    filterset_fields = ['is_active']
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def active(self, request):
        """Get active referral programs"""
        programs = ReferralProgram.objects.filter(is_active=True)
        serializer = self.get_serializer(programs, many=True)
        return Response(serializer.data)


class ReferralCodeViewSet(viewsets.ModelViewSet):
    queryset = ReferralCode.objects.all()
    serializer_class = ReferralCodeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['program', 'user', 'is_active']
    
    def get_queryset(self):
        # Regular users can only see their own referral codes
        if not self.request.user.is_staff:
            return ReferralCode.objects.filter(user=self.request.user)
        return super().get_queryset()
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def generate(self, request):
        """Generate a new referral code for the user"""
        program_id = request.data.get('program_id')
        program = None
        
        if program_id:
            try:
                program = ReferralProgram.objects.get(id=program_id, is_active=True)
            except ReferralProgram.DoesNotExist:
                return Response(
                    {'error': 'Referral program not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        referral_code = ReferralService.generate_referral_code(request.user, program)
        
        if not referral_code:
            return Response(
                {'error': 'No active referral program available'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(referral_code)
        return Response(serializer.data)


class ReferralViewSet(viewsets.ModelViewSet):
    queryset = Referral.objects.all()
    serializer_class = ReferralSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['program', 'status', 'referrer', 'referee']
    
    def get_queryset(self):
        # Regular users can only see referrals where they are the referrer or referee
        if not self.request.user.is_staff:
            return Referral.objects.filter(
                Q(referrer=self.request.user) | Q(referee=self.request.user)
            )
        return super().get_queryset()
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def process(self, request):
        """Process a new referral"""
        serializer = ProcessReferralSerializer(data=request.data)
        if serializer.is_valid():
            # Get the referee user
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            try:
                referee = User.objects.get(id=serializer.validated_data['referee_id'])
            except User.DoesNotExist:
                return Response(
                    {'error': 'Referee user not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Process the referral
            result = ReferralService.process_referral(
                referral_code_str=serializer.validated_data['referral_code'],
                referee=referee,
                referrer_ip=serializer.validated_data.get('referrer_ip'),
                referee_ip=serializer.validated_data.get('referee_ip'),
                referrer_device_id=serializer.validated_data.get('referrer_device_id'),
                referee_device_id=serializer.validated_data.get('referee_device_id')
            )
            
            if result['success']:
                referral_serializer = self.get_serializer(result['referral'])
                return Response({
                    'success': True,
                    'message': result['message'],
                    'referral': referral_serializer.data
                })
            else:
                return Response({
                    'success': False,
                    'message': result['message']
                }, status=status.HTTP_400_BAD_REQUEST)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def verify(self, request, pk=None):
        """Verify a referral"""
        result = ReferralService.verify_referral(pk)
        
        if result['success']:
            referral_serializer = self.get_serializer(result['referral'])
            return Response({
                'success': True,
                'message': result['message'],
                'referral': referral_serializer.data
            })
        else:
            return Response({
                'success': False,
                'message': result['message']
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reward(self, request, pk=None):
        """Process rewards for a verified referral"""
        result = ReferralService.process_reward(pk)
        
        if result['success']:
            referral_serializer = self.get_serializer(result['referral'])
            return Response({
                'success': True,
                'message': result['message'],
                'referral': referral_serializer.data,
                'referrer_reward': {
                    'amount': result['referrer_reward'].amount,
                    'currency': result['referrer_reward'].currency.code
                },
                'referee_reward': {
                    'amount': result['referee_reward'].amount,
                    'currency': result['referee_reward'].currency.code
                }
            })
        else:
            return Response({
                'success': False,
                'message': result['message']
            }, status=status.HTTP_400_BAD_REQUEST)


class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.IsAdminUser]
    filterset_fields = ['is_active']
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def available(self, request):
        """Get available subscription plans"""
        plans = SubscriptionService.get_available_plans()
        serializer = self.get_serializer(plans, many=True)
        return Response(serializer.data)


class PlanBenefitViewSet(viewsets.ModelViewSet):
    queryset = PlanBenefit.objects.all()
    serializer_class = PlanBenefitSerializer
    permission_classes = [permissions.IsAdminUser]
    filterset_fields = ['plan', 'benefit_type', 'is_active']


class UserSubscriptionViewSet(viewsets.ModelViewSet):
    queryset = UserSubscription.objects.all()
    serializer_class = UserSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['plan', 'status', 'billing_cycle', 'auto_renew']
    
    def get_queryset(self):
        # Regular users can only see their own subscriptions
        if not self.request.user.is_staff:
            return UserSubscription.objects.filter(user=self.request.user)
        return super().get_queryset()
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def active(self, request):
        """Get user's active subscription"""
        subscription = SubscriptionService.get_user_subscription(request.user)
        if subscription:
            serializer = self.get_serializer(subscription)
            return Response(serializer.data)
        else:
            return Response({'message': 'No active subscription found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def subscribe(self, request):
        """Subscribe to a plan"""
        serializer = SubscribeUserSerializer(data=request.data)
        if serializer.is_valid():
            result = SubscriptionService.subscribe_user(
                user=request.user,
                plan_id=serializer.validated_data['plan_id'],
                billing_cycle=serializer.validated_data['billing_cycle'],
                payment_reference=serializer.validated_data.get('payment_reference')
            )
            
            if result['success']:
                subscription_serializer = self.get_serializer(result['subscription'])
                return Response({
                    'success': True,
                    'message': result['message'],
                    'subscription': subscription_serializer.data
                })
            else:
                return Response({
                    'success': False,
                    'message': result['message']
                }, status=status.HTTP_400_BAD_REQUEST)
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def cancel(self, request, pk=None):
        """Cancel a subscription"""
        # Ensure the user can only cancel their own subscription
        subscription = self.get_object()
        if not request.user.is_staff and subscription.user != request.user:
            return Response(
                {'error': 'You can only cancel your own subscriptions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        result = SubscriptionService.cancel_subscription(request.user, subscription.id)
        
        if result['success']:
            subscription_serializer = self.get_serializer(result['subscription'])
            return Response({
                'success': True,
                'message': result['message'],
                'subscription': subscription_serializer.data
            })
        else:
            return Response({
                'success': False,
                'message': result['message']
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def renew(self, request, pk=None):
        """Renew a subscription"""
        # Ensure the user can only renew their own subscription
        subscription = self.get_object()
        if not request.user.is_staff and subscription.user != request.user:
            return Response(
                {'error': 'You can only renew your own subscriptions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        payment_reference = request.data.get('payment_reference')
        
        result = SubscriptionService.renew_subscription(
            subscription_id=subscription.id,
            payment_reference=payment_reference
        )
        
        if result['success']:
            subscription_serializer = self.get_serializer(result['subscription'])
            return Response({
                'success': True,
                'message': result['message'],
                'subscription': subscription_serializer.data
            })
        else:
            return Response({
                'success': False,
                'message': result['message']
            }, status=status.HTTP_400_BAD_REQUEST)


class SubscriptionTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SubscriptionTransaction.objects.all()
    serializer_class = SubscriptionTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['subscription', 'transaction_type']
    
    def get_queryset(self):
        # Regular users can only see transactions for their own subscriptions
        if not self.request.user.is_staff:
            return SubscriptionTransaction.objects.filter(subscription__user=self.request.user)
        return super().get_queryset()


class FeeCalculationViewSet(viewsets.ViewSet):
    """ViewSet for fee calculation without database operations"""
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """Calculate fee for a transaction"""
        serializer = CalculateFeeSerializer(data=request.data)
        if serializer.is_valid():
            amount = Money(
                serializer.validated_data['amount'],
                serializer.validated_data['currency']
            )
            
            fee_result = FeeService.calculate_fee(
                transaction_type=serializer.validated_data['transaction_type'],
                amount=amount,
                user=request.user,
                discount_code=serializer.validated_data.get('discount_code')
            )
            
            # Convert Money objects to dictionaries for JSON response
            response_data = {
                'fee_amount': {
                    'amount': fee_result['fee_amount'].amount,
                    'currency': fee_result['fee_amount'].currency.code
                },
                'original_amount': {
                    'amount': fee_result['original_amount'].amount,
                    'currency': fee_result['original_amount'].currency.code
                },
                'total_amount': {
                    'amount': fee_result['total_amount'].amount,
                    'currency': fee_result['total_amount'].currency.code
                },
                'discount_applied': fee_result['discount_applied'],
                'discount_amount': {
                    'amount': fee_result['discount_amount'].amount,
                    'currency': fee_result['discount_amount'].currency.code
                },
                'rules_applied': fee_result['rules_applied']
            }
            
            return Response(response_data)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)