from django.shortcuts import render, redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Sum, Avg, Q
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .serializers import UserProfileSerializer
from .utils import set_otp, send_otp_email, send_otp_sms
from .models import UserProfile, KYCProfile
from django.contrib.auth.models import User
import json
import csv
from datetime import datetime, timedelta
from .models import KYCLevelChoices
from .serializers import KYCProfileSerializer, KYCProfileDetailSerializer, KYCLevelUpdateSerializer
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
import os
from django.conf import settings
from django.contrib.auth import get_user_model
from bank.models import Wallet
import requests
from .forms import RegistrationForm, OTPVerificationForm, KYCInputForm
from django.contrib import messages
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import SetTransactionPinSerializer
from rest_framework import viewsets
from rest_framework.decorators import action
from .serializers import SetTransactionPinSerializer, UpdateTransactionPinSerializer

DUMMY_KYC_PATH = os.path.join(settings.PROJECT_ROOT, 'dummy_kyc_data.json')

REMOTE_KYC_URL = "https://raw.githubusercontent.com/saggemode/djbackend2/master/bvn_nin.json"

def load_dummy_kyc():
    with open(DUMMY_KYC_PATH, 'r') as f:
        return json.load(f)

def load_remote_kyc():
    try:
        response = requests.get(REMOTE_KYC_URL, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        raise RuntimeError("Validation service timed out. Please try again.")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Validation service error: {str(e)}")

def load_remote_kyc_with_fallback():
    try:
        response = requests.get(REMOTE_KYC_URL, timeout=5)
        response.raise_for_status()
        return response.json(), False  # False = not fallback
    except (requests.exceptions.Timeout, requests.exceptions.RequestException):
        from .views import load_dummy_kyc  # avoid circular import if any
        return load_dummy_kyc(), True  # True = fallback used

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    """Get current user's profile."""
    profile = request.user.profile
    serializer = UserProfileSerializer(profile)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_verification(request):
    """Request OTP for account verification."""
    profile = request.user.profile
    otp = set_otp(profile)
    send_otp_email(request.user, otp)
    send_otp_sms(profile.phone, otp)
    return Response({'detail': 'Verification code sent to your email and phone.'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify(request):
    try:
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=request.user)
        # Debug: Print request data type and content
        print(f"Request data type: {type(request.data)}")
        print(f"Request data: {request.data}")
        print(f"Request content type: {request.content_type}")
        # Handle different data formats
        if hasattr(request.data, 'get'):
            code = request.data.get('otp')
        elif isinstance(request.data, (list, tuple)) and len(request.data) > 0:
            code = request.data[0]
        else:
            code = request.POST.get('otp')
        if not code:
            return Response({'detail': 'OTP code is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not profile.otp_code or not profile.otp_expiry:
            return Response({'detail': 'No OTP requested.'}, status=status.HTTP_400_BAD_REQUEST)
        if timezone.now() > profile.otp_expiry:
            user = request.user
            user.delete()
            return Response({'detail': 'OTP expired. Your account has been deleted. Please register again.'}, status=status.HTTP_400_BAD_REQUEST)
        if str(code) != str(profile.otp_code):
            return Response({'detail': 'Invalid OTP.'}, status=status.HTTP_400_BAD_REQUEST)
        profile.is_verified = True
        profile.otp_code = None
        profile.otp_expiry = None
        profile.save()
        return Response({'detail': 'Account verified successfully.'})
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return Response({'detail': f'Internal error: {str(e)}'}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_bvn(request):
    from .serializers import BVNValidationSerializer
    from .models import KYCProfile
    serializer = BVNValidationSerializer(data=request.data)
    if serializer.is_valid():
        bvn = serializer.validated_data['bvn']
        data, fallback = load_remote_kyc_with_fallback()
        bvn_data = data.get('bvn', {}).get(bvn)
        if bvn_data:
            user = request.user
            dob = bvn_data.get('dob')
            if not dob:
                return Response({'detail': 'Date of birth is required for KYC.'}, status=400)
            kyc, created = KYCProfile.objects.get_or_create(
                user=user,
                defaults={
                    'date_of_birth': dob,
                    'address': '',
                    'state': '',
                }
            )
            kyc.bvn = bvn
            kyc.date_of_birth = dob
            kyc.telephone_number = bvn_data.get('phone') or kyc.telephone_number
            if not kyc.address:
                kyc.address = ''
            if not kyc.state:
                kyc.state = ''
            if not kyc.is_approved:
                kyc.is_approved = True
                if created:
                    kyc.save(update_fields=['bvn', 'date_of_birth', 'telephone_number', 'address', 'state'])
                    kyc.is_approved = True
                    kyc.save(update_fields=['is_approved'])
                else:
                    kyc.save()
            else:
                kyc.save()
            resp = bvn_data.copy()
            if fallback:
                resp['warning'] = 'Remote validation unavailable, using local fallback data.'
            resp['kyc_profile_updated'] = True
            return Response(resp)
        return Response({'detail': 'BVN not found.'}, status=404)
    return Response(serializer.errors, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_nin(request):
    from .serializers import NINValidationSerializer
    from .models import KYCProfile
    serializer = NINValidationSerializer(data=request.data)
    if serializer.is_valid():
        nin = serializer.validated_data['nin']
        data, fallback = load_remote_kyc_with_fallback()
        nin_data = data.get('nin', {}).get(nin)
        if nin_data:
            user = request.user
            dob = nin_data.get('dob')
            if not dob:
                return Response({'detail': 'Date of birth is required for KYC.'}, status=400)
            kyc, created = KYCProfile.objects.get_or_create(
                user=user,
                defaults={
                    'date_of_birth': dob,
                    'address': '',
                    'state': '',
                }
            )
            kyc.nin = nin
            kyc.date_of_birth = dob
            kyc.telephone_number = nin_data.get('phone') or kyc.telephone_number
            if not kyc.address:
                kyc.address = ''
            if not kyc.state:
                kyc.state = ''
            if not kyc.is_approved:
                kyc.is_approved = True
                if created:
                    kyc.save(update_fields=['nin', 'date_of_birth', 'telephone_number', 'address', 'state'])
                    kyc.is_approved = True
                    kyc.save(update_fields=['is_approved'])
                else:
                    kyc.save()
            else:
                kyc.save()
            resp = nin_data.copy()
            if fallback:
                resp['warning'] = 'Remote validation unavailable, using local fallback data.'
            resp['kyc_profile_updated'] = True
            return Response(resp)
        return Response({'detail': 'NIN not found.'}, status=404)
    return Response(serializer.errors, status=400)

@api_view(['POST'])
@permission_classes([AllowAny])
def resume_registration(request):
    identifier = request.data.get('identifier')
    user = None
    if not identifier:
        return Response({'detail': 'Identifier is required.'}, status=400)
    if '@' in identifier:
        user = get_user_model().objects.filter(email=identifier).first()
    elif identifier.isdigit() and len(identifier) >= 10:
        profile = UserProfile.objects.filter(phone=identifier).first()
        user = profile.user if profile else None
    else:
        user = get_user_model().objects.filter(username=identifier).first()
    if not user:
        return Response({'detail': 'User not found.'}, status=404)
    profile = getattr(user, 'profile', None)
    kyc = KYCProfile.objects.filter(user=user).first()
    wallet = Wallet.objects.filter(user=user).first()
    return Response({
        'username': user.username,
        'email': user.email,
        'phone': profile.phone if profile else None,
        'is_verified': profile.is_verified if profile else False,
        'has_kyc': bool(kyc and (kyc.bvn or kyc.nin)),
        'has_wallet': bool(wallet),
        'kyc': {
            'bvn': kyc.bvn if kyc else None,
            'nin': kyc.nin if kyc else None,
            'is_approved': kyc.is_approved if kyc else False,
        } if kyc else None,
    })

def register(request):

    # register new user 
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password1']
            )
            # Optionally, set phone number in UserProfile
            if hasattr(user, 'profile'):
                user.profile.phone = form.cleaned_data['phone']
                user.profile.save()
            # Send OTP (reuse your set_otp/send_otp_email/send_otp_sms logic)
            from .utils import set_otp, send_otp_email, send_otp_sms
            otp = set_otp(user.profile)
            send_otp_email(user, otp)
            send_otp_sms(user.profile.phone, otp)
            request.session['pending_verification_user'] = user.username
            messages.success(request, 'Registration successful. An OTP has been sent to your email and phone. Please verify your account.')
            return redirect('verify-otp')
    else:
        form = RegistrationForm()
    return render(request, 'account/register.html', {'form': form})

def verify_otp(request):
    username = request.session.get('pending_verification_user')
    user = None
    if username:
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None
    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid() and user:
            otp = form.cleaned_data['otp']
            profile = user.profile
            if not profile.otp_code or not profile.otp_expiry:
                form.add_error('otp', 'No OTP requested.')
            elif timezone.now() > profile.otp_expiry:
                user.delete()
                if 'pending_verification_user' in request.session:
                    del request.session['pending_verification_user']
                messages.error(request, 'OTP expired. Your account has been deleted. Please register again.')
                return redirect('register')
            elif str(otp) != str(profile.otp_code):
                form.add_error('otp', 'Invalid OTP.')
            else:
                profile.is_verified = True
                profile.otp_code = None
                profile.otp_expiry = None
                profile.save()
                messages.success(request, 'Account verified successfully. You can now log in.')
                del request.session['pending_verification_user']
                return redirect('kyc-input')
    else:
        form = OTPVerificationForm()
    return render(request, 'account/verify_otp.html', {'form': form, 'user': user})

def kyc_input(request):
    user = request.user
    result = None
    error = None
    if not user.is_authenticated:
        return redirect('/login/')
    if request.method == 'POST':
        form = KYCInputForm(request.POST)
        if form.is_valid():
            kyc_type = form.cleaned_data['kyc_type']
            value = form.cleaned_data['value']
            if kyc_type == 'bvn':
                from .serializers import BVNValidationSerializer
                serializer = BVNValidationSerializer(data={'bvn': value})
                if serializer.is_valid():
                    from .models import KYCProfile
                    data, fallback = load_remote_kyc_with_fallback()
                    bvn_data = data.get('bvn', {}).get(value)
                    if bvn_data:
                        dob = bvn_data.get('dob')
                        gender = bvn_data.get('gender')
                        if not dob:
                            error = 'Date of birth is required for KYC.'
                        else:
                            kyc, created = KYCProfile.objects.get_or_create(
                                user=user,
                                defaults={
                                    'date_of_birth': dob,
                                    'address': '',
                                    'state': '',
                                }
                            )
                            kyc.bvn = value
                            kyc.date_of_birth = dob
                            kyc.telephone_number = bvn_data.get('phone') or kyc.telephone_number
                            kyc.gender = gender
                            if not kyc.address:
                                kyc.address = ''
                            if not kyc.state:
                                kyc.state = ''
                            if not kyc.is_approved:
                                kyc.is_approved = True
                                if created:
                                    kyc.save(update_fields=['bvn', 'date_of_birth', 'telephone_number', 'address', 'state', 'gender'])
                                    kyc.is_approved = True
                                    kyc.save(update_fields=['is_approved'])
                                else:
                                    kyc.save()
                            else:
                                kyc.save()
                            result = bvn_data.copy()
                            if fallback:
                                result['warning'] = 'Remote validation unavailable, using local fallback data.'
                            result['kyc_profile_updated'] = True
                    else:
                        error = 'BVN not found.'
                else:
                    error = serializer.errors.get('bvn', ['Invalid BVN'])[0]
            else:
                from .serializers import NINValidationSerializer
                serializer = NINValidationSerializer(data={'nin': value})
                if serializer.is_valid():
                    from .models import KYCProfile
                    data, fallback = load_remote_kyc_with_fallback()
                    nin_data = data.get('nin', {}).get(value)
                    if nin_data:
                        dob = nin_data.get('dob')
                        gender = nin_data.get('gender')
                        if not dob:
                            error = 'Date of birth is required for KYC.'
                        else:
                            kyc, created = KYCProfile.objects.get_or_create(
                                user=user,
                                defaults={
                                    'date_of_birth': dob,
                                    'address': '',
                                    'state': '',
                                }
                            )
                            kyc.nin = value
                            kyc.date_of_birth = dob
                            kyc.telephone_number = nin_data.get('phone') or kyc.telephone_number
                            kyc.gender = gender
                            if not kyc.address:
                                kyc.address = ''
                            if not kyc.state:
                                kyc.state = ''
                            if not kyc.is_approved:
                                kyc.is_approved = True
                                if created:
                                    kyc.save(update_fields=['nin', 'date_of_birth', 'telephone_number', 'address', 'state', 'gender'])
                                    kyc.is_approved = True
                                    kyc.save(update_fields=['is_approved'])
                                else:
                                    kyc.save()
                            else:
                                kyc.save()
                            result = nin_data.copy()
                            if fallback:
                                result['warning'] = 'Remote validation unavailable, using local fallback data.'
                            result['kyc_profile_updated'] = True
                    else:
                        error = 'NIN not found.'
                else:
                    error = serializer.errors.get('nin', ['Invalid NIN'])[0]
    else:
        form = KYCInputForm()
    return render(request, 'account/kyc_input.html', {'form': form, 'result': result, 'error': error})

def verify_email_link(request):
    uidb64 = request.GET.get('uid')
    token = request.GET.get('token')
    if not uidb64 or not token:
        return HttpResponse("Invalid verification link.", status=400)
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user and default_token_generator.check_token(user, token):
        profile = user.profile
        profile.is_verified = True
        profile.otp_code = None
        profile.otp_expiry = None
        profile.save()
        return HttpResponse("Your email has been verified. You can now log in.")
    else:
        return HttpResponse("Verification link is invalid or expired.", status=400)

# Custom Admin Views for Financial Operations
@staff_member_required
def admin_dashboard(request):
    """Custom admin dashboard with financial metrics."""
    # User statistics
    total_users = User.objects.count()
    verified_users = UserProfile.objects.filter(is_verified=True).count()
    new_users_today = User.objects.filter(date_joined__date=timezone.now().date()).count()
    new_users_week = User.objects.filter(date_joined__gte=timezone.now() - timedelta(days=7)).count()
    
    # Financial metrics (placeholder - replace with actual bank models)
    total_wallets = 0  # Replace with actual wallet count
    total_transactions = 0  # Replace with actual transaction count
    total_volume = 0  # Replace with actual transaction volume
    
    # System health
    system_status = "Healthy"
    last_backup = timezone.now() - timedelta(hours=2)
    
    context = {
        'total_users': total_users,
        'verified_users': verified_users,
        'verification_rate': (verified_users / total_users * 100) if total_users > 0 else 0,
        'new_users_today': new_users_today,
        'new_users_week': new_users_week,
        'total_wallets': total_wallets,
        'total_transactions': total_transactions,
        'total_volume': total_volume,
        'system_status': system_status,
        'last_backup': last_backup,
    }
    
    return render(request, 'admin/dashboard.html', context)

@staff_member_required
def compliance_report(request):
    """Generate compliance report for regulators."""
    # User verification data
    users = User.objects.select_related('profile').all()
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="compliance_report_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'User ID', 'Username', 'Email', 'Phone', 'Verification Status',
        'Registration Date', 'Last Login', 'Is Active'
    ])
    
    for user in users:
        phone = user.profile.phone if hasattr(user, 'profile') else 'N/A'
        verified = user.profile.is_verified if hasattr(user, 'profile') else False
        
        writer.writerow([
            user.id,
            user.username,
            user.email,
            phone,
            'Verified' if verified else 'Unverified',
            user.date_joined.strftime('%Y-%m-%d %H:%M'),
            user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else 'Never',
            'Active' if user.is_active else 'Inactive'
        ])
    
    return response

@staff_member_required
def user_analytics(request):
    """User analytics and growth metrics."""
    # Date ranges
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # User growth data
    daily_registrations = []
    for i in range(30):
        date = today - timedelta(days=i)
        count = User.objects.filter(date_joined__date=date).count()
        daily_registrations.append({'date': date.strftime('%Y-%m-%d'), 'count': count})
    
    # Verification statistics
    verification_stats = {
        'total': UserProfile.objects.count(),
        'verified': UserProfile.objects.filter(is_verified=True).count(),
        'unverified': UserProfile.objects.filter(is_verified=False).count(),
        'verification_rate': 0
    }
    
    if verification_stats['total'] > 0:
        verification_stats['verification_rate'] = (verification_stats['verified'] / verification_stats['total']) * 100
    
    # Recent activity
    recent_users = User.objects.select_related('profile').order_by('-date_joined')[:10]
    
    context = {
        'daily_registrations': daily_registrations,
        'verification_stats': verification_stats,
        'recent_users': recent_users,
        'week_ago': week_ago,
        'month_ago': month_ago,
    }
    
    return render(request, 'admin/user_analytics.html', context)

@staff_member_required
def system_monitoring(request):
    """System health and monitoring dashboard."""
    # System metrics
    system_metrics = {
        'total_users': User.objects.count(),
        'active_users_today': User.objects.filter(last_login__date=timezone.now().date()).count(),
        'new_users_today': User.objects.filter(date_joined__date=timezone.now().date()).count(),
        'verified_users': UserProfile.objects.filter(is_verified=True).count(),
        'pending_verifications': UserProfile.objects.filter(is_verified=False).count(),
    }
    
    # Performance metrics (placeholder)
    performance_metrics = {
        'response_time': '120ms',
        'uptime': '99.9%',
        'database_connections': 15,
        'memory_usage': '45%',
        'cpu_usage': '23%',
    }
    
    # Security alerts
    security_alerts = [
        {'type': 'info', 'message': 'All systems operational', 'time': timezone.now()},
        {'type': 'warning', 'message': 'High login attempts detected', 'time': timezone.now() - timedelta(hours=1)},
    ]
    
    context = {
        'system_metrics': system_metrics,
        'performance_metrics': performance_metrics,
        'security_alerts': security_alerts,
    }
    
    return render(request, 'admin/system_monitoring.html', context)

# API endpoints for admin dashboard
@staff_member_required
def api_dashboard_data(request):
    """API endpoint for dashboard data."""
    # Real-time dashboard data
    data = {
        'users': {
            'total': User.objects.count(),
            'verified': UserProfile.objects.filter(is_verified=True).count(),
            'new_today': User.objects.filter(date_joined__date=timezone.now().date()).count(),
        },
        'system': {
            'status': 'healthy',
            'last_update': timezone.now().isoformat(),
        }
    }
    
    return JsonResponse(data)

@staff_member_required
def api_user_export(request):
    """API endpoint for user data export."""
    format_type = request.GET.get('format', 'csv')
    
    if format_type == 'json':
        users = User.objects.select_related('profile').all()
        data = []
        
        for user in users:
            data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'phone': user.profile.phone if hasattr(user, 'profile') else None,
                'verified': user.profile.is_verified if hasattr(user, 'profile') else False,
                'registration_date': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'is_active': user.is_active,
            })
        
        return JsonResponse({'users': data})
    
    # Default to CSV
    return compliance_report(request)

class KYCProfileViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_approved', 'created_at']
    search_fields = ['user__username', 'user__email', 'bvn', 'nin']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    def get_queryset(self):
        if self.request.user.is_staff:
            return KYCProfile.objects.all()
        return KYCProfile.objects.filter(user=self.request.user)
    def get_serializer_class(self):
        if self.action in ['retrieve', 'list']:
            return KYCProfileDetailSerializer
        return KYCProfileSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tier_upgrade_requirements(request):
    """
    Get tier upgrade requirements for the authenticated user.
    """
    try:
        kyc_profile = KYCProfile.objects.get(user=request.user)
        
        # Get current tier info
        current_tier = kyc_profile.get_kyc_level_display()
        tier_limits = kyc_profile.get_tier_limits()
        
        # Get available upgrades
        available_upgrades = kyc_profile.get_available_upgrades()
        
        # Get requirements for next tier
        next_tier_requirements = {}
        if kyc_profile.kyc_level == 'tier_1':
            next_tier_requirements = kyc_profile.get_upgrade_requirements('tier_2')
        elif kyc_profile.kyc_level == 'tier_2':
            next_tier_requirements = kyc_profile.get_upgrade_requirements('tier_3')
        
        response_data = {
            'current_tier': {
                'level': kyc_profile.kyc_level,
                'display_name': current_tier,
                'limits': tier_limits,
                'is_approved': kyc_profile.is_approved,
            },
            'available_upgrades': available_upgrades,
            'next_tier_requirements': next_tier_requirements,
            'upgrade_requested': kyc_profile.upgrade_requested,
            'upgrade_request_date': kyc_profile.upgrade_request_date,
        }
        
        return Response(response_data)
        
    except KYCProfile.DoesNotExist:
        return Response({
            'error': 'KYC profile not found. Please complete your KYC first.'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_tier_upgrade(request):
    """
    Request a tier upgrade for the authenticated user.
    """
    try:
        kyc_profile = KYCProfile.objects.get(user=request.user)
        target_tier = request.data.get('target_tier')
        
        if not target_tier:
            return Response({
                'error': 'target_tier is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user can upgrade to the requested tier
        if target_tier == 'tier_2':
            can_upgrade, message = kyc_profile.can_upgrade_to_tier_2()
        elif target_tier == 'tier_3':
            can_upgrade, message = kyc_profile.can_upgrade_to_tier_3()
        else:
            return Response({
                'error': 'Invalid target tier. Must be tier_2 or tier_3'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not can_upgrade:
            return Response({
                'error': message,
                'requirements': kyc_profile.get_upgrade_requirements(target_tier)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Mark upgrade as requested
        kyc_profile.upgrade_requested = True
        kyc_profile.upgrade_request_date = timezone.now()
        kyc_profile.save()
        
        return Response({
            'message': f'Upgrade request submitted successfully for {target_tier}',
            'target_tier': target_tier,
            'request_date': kyc_profile.upgrade_request_date
        })
        
    except KYCProfile.DoesNotExist:
        return Response({
            'error': 'KYC profile not found. Please complete your KYC first.'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_upgrade_eligibility(request):
    """
    Check if the user is eligible for any tier upgrades.
    """
    try:
        kyc_profile = KYCProfile.objects.get(user=request.user)
        
        can_tier_2, tier_2_message = kyc_profile.can_upgrade_to_tier_2()
        can_tier_3, tier_3_message = kyc_profile.can_upgrade_to_tier_3()
        
        response_data = {
            'current_tier': kyc_profile.kyc_level,
            'current_tier_display': kyc_profile.get_kyc_level_display(),
            'eligibility': {
                'tier_2': {
                    'eligible': can_tier_2,
                    'message': tier_2_message,
                    'requirements': kyc_profile.get_upgrade_requirements('tier_2') if kyc_profile.kyc_level == 'tier_1' else None
                },
                'tier_3': {
                    'eligible': can_tier_3,
                    'message': tier_3_message,
                    'requirements': kyc_profile.get_upgrade_requirements('tier_3') if kyc_profile.kyc_level == 'tier_2' else None
                }
            },
            'available_upgrades': kyc_profile.get_available_upgrades()
        }
        
        return Response(response_data)
        
    except KYCProfile.DoesNotExist:
        return Response({
            'error': 'KYC profile not found. Please complete your KYC first.'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TransactionPinViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def set(self, request):
        serializer = SetTransactionPinSerializer(data=request.data)
        if serializer.is_valid():
            pin = serializer.validated_data['pin']
            if request.user.profile.transaction_pin:
                return Response({'error': 'PIN already set. Use update endpoint.'}, status=400)
            request.user.profile.set_transaction_pin(pin)
            return Response({'success': 'Transaction PIN set.'})
        return Response(serializer.errors, status=400)

    @action(detail=False, methods=['post'], url_path='change')
    def change_pin(self, request):
        serializer = UpdateTransactionPinSerializer(data=request.data)
        if serializer.is_valid():
            old_pin = serializer.validated_data['old_pin']
            new_pin = serializer.validated_data['new_pin']
            profile = request.user.profile
            if not profile.transaction_pin:
                return Response({'error': 'No PIN set yet. Use set endpoint.'}, status=400)
            if not profile.check_transaction_pin(old_pin):
                return Response({'error': 'Old PIN is incorrect.'}, status=400)
            profile.set_transaction_pin(new_pin)
            return Response({'success': 'Transaction PIN updated.'})
        return Response(serializer.errors, status=400)
