# NOTE: This file now supports HTML OTP emails with a clickable verification link.
import random
import string
from django.utils import timezone
from django.contrib.auth.models import User
from .models import AuditLog, SecurityAlert, UserSession
from django.contrib.contenttypes.models import ContentType
from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator

# Generate a 6-digit OTP
def generate_otp():
    return f"{random.randint(100000, 999999)}"

# Send OTP via email
def send_otp_email(user, otp):
    subject = "Your OTP Code for Account Verification"
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
    verification_link = f"{site_url}/accounts/verify-email/?uid={uid}&token={token}"
    otp_expiry_minutes = getattr(settings, 'OTP_EXPIRY_MINUTES', 10)
    html_content = render_to_string('account/otp_email.html', {
        'username': user.username,
        'otp': otp,
        'verification_link': verification_link,
        'otp_expiry_minutes': otp_expiry_minutes,
    })
    text_content = f"Hello {user.username},\n\nYour OTP code is: {otp}\nThis OTP will expire in {otp_expiry_minutes} minutes.\n\nOr click the link below to verify your account:\n{verification_link}\n\nIf you did not request this, please ignore this email."
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com')
    msg = EmailMultiAlternatives(subject, text_content, from_email, [user.email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()
    print(f"OTP {otp} sent to {user.email}")
    return True

# Placeholder for sending SMS (implement with Twilio or other service)
def send_otp_sms(phone, otp):
    """Send OTP via SMS (placeholder implementation)."""
    # In production, integrate with SMS service like Twilio
    print(f"OTP {otp} sent to {phone}")
    return True

# Set OTP and expiry on profile
def set_otp(profile):
    """Generate and set OTP for user verification."""
    otp = ''.join(random.choices(string.digits, k=6))
    expiry_minutes = getattr(settings, 'OTP_EXPIRY_MINUTES', 10)
    profile.otp_code = otp
    profile.otp_expiry = timezone.now() + timedelta(minutes=expiry_minutes)
    profile.save()
    return otp

# Security and Audit Utilities
def log_audit_event(user, action, description, severity='low', ip_address=None, user_agent=None, content_object=None, metadata=None):
    """Log an audit event for security tracking."""
    try:
        audit_log = AuditLog.objects.create(
            user=user,
            action=action,
            description=description,
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent or '',
            content_type=ContentType.objects.get_for_model(content_object) if content_object else None,
            object_id=content_object.id if content_object else None,
            metadata=metadata or {}
        )
        return audit_log
    except Exception as e:
        print(f"Failed to log audit event: {e}")
        return None

def create_security_alert(alert_type, severity, title, description, affected_user=None, ip_address=None):
    """Create a security alert for monitoring."""
    try:
        alert = SecurityAlert.objects.create(
            alert_type=alert_type,
            severity=severity,
            title=title,
            description=description,
            affected_user=affected_user,
            ip_address=ip_address
        )
        return alert
    except Exception as e:
        print(f"Failed to create security alert: {e}")
        return None

def track_user_session(user, session_key, ip_address, user_agent):
    """Track user session for security monitoring."""
    try:
        session, created = UserSession.objects.get_or_create(
            session_key=session_key,
            defaults={
                'user': user,
                'ip_address': ip_address,
                'user_agent': user_agent,
            }
        )
        if not created:
            session.last_activity = timezone.now()
            session.save()
        return session
    except Exception as e:
        print(f"Failed to track user session: {e}")
        return None

def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def get_user_agent(request):
    """Get user agent from request."""
    return request.META.get('HTTP_USER_AGENT', '')

def check_suspicious_activity(user, ip_address, action):
    """Check for suspicious user activity."""
    suspicious = False
    reasons = []
    
    # Check for multiple failed login attempts
    if action == 'login_failed':
        recent_failures = AuditLog.objects.filter(
            user=user,
            action='login_failed',
            timestamp__gte=timezone.now() - timedelta(minutes=15)
        ).count()
        
        if recent_failures >= 5:
            suspicious = True
            reasons.append(f"Multiple failed login attempts: {recent_failures}")
    
    # Check for login from new IP
    if action == 'login_success':
        previous_ips = UserSession.objects.filter(user=user).values_list('ip_address', flat=True).distinct()
        if ip_address not in previous_ips:
            suspicious = True
            reasons.append(f"Login from new IP: {ip_address}")
    
    # Check for unusual activity patterns
    recent_actions = AuditLog.objects.filter(
        user=user,
        timestamp__gte=timezone.now() - timedelta(hours=1)
    ).count()
    
    if recent_actions > 50:  # Threshold for unusual activity
        suspicious = True
        reasons.append(f"High activity level: {recent_actions} actions in 1 hour")
    
    return suspicious, reasons

def generate_security_report(start_date=None, end_date=None):
    """Generate comprehensive security report."""
    if not start_date:
        start_date = timezone.now() - timedelta(days=30)
    if not end_date:
        end_date = timezone.now()
    
    report = {
        'period': {
            'start': start_date,
            'end': end_date
        },
        'audit_events': {
            'total': AuditLog.objects.filter(timestamp__range=[start_date, end_date]).count(),
            'by_action': {},
            'by_severity': {},
        },
        'security_alerts': {
            'total': SecurityAlert.objects.filter(timestamp__range=[start_date, end_date]).count(),
            'by_type': {},
            'by_severity': {},
            'open_alerts': SecurityAlert.objects.filter(status='open').count(),
        },
        'user_sessions': {
            'total': UserSession.objects.filter(created_at__range=[start_date, end_date]).count(),
            'active': UserSession.objects.filter(is_active=True).count(),
        },
        'suspicious_activity': {
            'failed_logins': AuditLog.objects.filter(
                action='login_failed',
                timestamp__range=[start_date, end_date]
            ).count(),
            'new_ip_logins': 0,  # Would need custom logic to calculate
        }
    }
    
    # Calculate breakdowns
    for action in AuditLog.ACTION_TYPES:
        count = AuditLog.objects.filter(
            action=action[0],
            timestamp__range=[start_date, end_date]
        ).count()
        if count > 0:
            report['audit_events']['by_action'][action[1]] = count
    
    for severity in AuditLog.SEVERITY_LEVELS:
        count = AuditLog.objects.filter(
            severity=severity[0],
            timestamp__range=[start_date, end_date]
        ).count()
        if count > 0:
            report['audit_events']['by_severity'][severity[1]] = count
    
    for alert_type in SecurityAlert.ALERT_TYPES:
        count = SecurityAlert.objects.filter(
            alert_type=alert_type[0],
            timestamp__range=[start_date, end_date]
        ).count()
        if count > 0:
            report['security_alerts']['by_type'][alert_type[1]] = count
    
    return report

def cleanup_old_data():
    """Clean up old audit logs and sessions for performance."""
    # Keep audit logs for 1 year
    one_year_ago = timezone.now() - timedelta(days=365)
    old_audit_logs = AuditLog.objects.filter(timestamp__lt=one_year_ago)
    audit_logs_deleted = old_audit_logs.count()
    old_audit_logs.delete()
    
    # Keep sessions for 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    old_sessions = UserSession.objects.filter(created_at__lt=thirty_days_ago)
    sessions_deleted = old_sessions.count()
    old_sessions.delete()
    
    # Resolve old security alerts
    old_alerts = SecurityAlert.objects.filter(
        status='open',
        timestamp__lt=timezone.now() - timedelta(days=7)
    )
    alerts_resolved = old_alerts.count()
    old_alerts.update(status='resolved', notes='Auto-resolved due to age')
    
    return {
        'audit_logs_deleted': audit_logs_deleted,
        'sessions_deleted': sessions_deleted,
        'alerts_resolved': alerts_resolved
    } 