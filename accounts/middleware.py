from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from .utils import (
    log_audit_event, track_user_session, get_client_ip, get_user_agent,
    check_suspicious_activity, create_security_alert
)
from django.utils import timezone

class SecurityMiddleware(MiddlewareMixin):
    """Middleware for security monitoring and audit logging."""
    
    def process_request(self, request):
        """Process incoming requests for security monitoring."""
        # Get client information
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)
        
        # Store in request for later use
        request.client_ip = ip_address
        request.client_user_agent = user_agent
        
        # Track authenticated user sessions
        if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser):
            if hasattr(request, 'session') and request.session.session_key:
                track_user_session(
                    user=request.user,
                    session_key=request.session.session_key,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
    
    def process_response(self, request, response):
        """Process responses for audit logging."""
        # Log important actions
        if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser):
            self._log_user_activity(request, response)
        
        return response
    
    def _log_user_activity(self, request, response):
        """Log user activity based on request path and method."""
        user = request.user
        path = request.path
        method = request.method
        ip_address = getattr(request, 'client_ip', None)
        user_agent = getattr(request, 'client_user_agent', None)
        
        # Define important actions to log
        important_paths = {
            '/admin/': 'admin_access',
            '/accounts/profile/': 'profile_view',
            '/accounts/request-verification/': 'verification_request',
            '/accounts/verify/': 'verification_attempt',
            '/api/token/': 'token_request',
            '/api/token/refresh/': 'token_refresh',
        }
        
        # Log admin actions
        if path.startswith('/admin/') and method in ['POST', 'PUT', 'DELETE']:
            action = 'admin_action'
            description = f"Admin {method} action on {path}"
            severity = 'medium'
            
            log_audit_event(
                user=user,
                action=action,
                description=description,
                severity=severity,
                ip_address=ip_address,
                user_agent=user_agent
            )
        
        # Log authentication events
        elif path in important_paths:
            action = important_paths[path]
            description = f"User accessed {path} via {method}"
            severity = 'low'
            
            log_audit_event(
                user=user,
                action=action,
                description=description,
                severity=severity,
                ip_address=ip_address,
                user_agent=user_agent
            )
        
        # Check for suspicious activity
        if user and ip_address:
            suspicious, reasons = check_suspicious_activity(user, ip_address, 'general_activity')
            
            if suspicious:
                # Create security alert
                create_security_alert(
                    alert_type='unusual_activity',
                    severity='medium',
                    title=f"Suspicious activity detected for user {user.username}",
                    description=f"Reasons: {', '.join(reasons)}",
                    affected_user=user,
                    ip_address=ip_address
                )
                
                # Log the suspicious activity
                log_audit_event(
                    user=user,
                    action='security_alert',
                    description=f"Suspicious activity detected: {', '.join(reasons)}",
                    severity='high',
                    ip_address=ip_address,
                    user_agent=user_agent
                )

class LoginSecurityMiddleware(MiddlewareMixin):
    """Middleware specifically for login security monitoring."""
    
    def process_request(self, request):
        """Monitor login attempts and detect brute force attacks."""
        if request.path == '/api/token/' and request.method == 'POST':
            ip_address = get_client_ip(request)
            self._monitor_login_attempt(request, ip_address)
    
    def _monitor_login_attempt(self, request, ip_address):
        """Monitor login attempts for security threats."""
        from django.contrib.auth.models import User
        from .models import AuditLog
        
        # Get login credentials from request
        try:
            import json
            body = request.body.decode('utf-8')
            data = json.loads(body)
            username = data.get('username', '')
        except:
            username = request.POST.get('username', '')
        
        # Check if user exists
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None
        
        # Log the login attempt
        if user:
            # Successful login attempt
            log_audit_event(
                user=user,
                action='login_success',
                description=f"Successful login from {ip_address}",
                severity='low',
                ip_address=ip_address,
                user_agent=get_user_agent(request)
            )
            
            # Check for suspicious login
            suspicious, reasons = check_suspicious_activity(user, ip_address, 'login_success')
            if suspicious:
                create_security_alert(
                    alert_type='suspicious_login',
                    severity='medium',
                    title=f"Suspicious login for user {user.username}",
                    description=f"Login from {ip_address}. Reasons: {', '.join(reasons)}",
                    affected_user=user,
                    ip_address=ip_address
                )
        else:
            # Failed login attempt
            log_audit_event(
                user=None,
                action='login_failed',
                description=f"Failed login attempt for username '{username}' from {ip_address}",
                severity='medium',
                ip_address=ip_address,
                user_agent=get_user_agent(request)
            )
            
            # Check for brute force attempts
            recent_failures = AuditLog.objects.filter(
                action='login_failed',
                ip_address=ip_address,
                timestamp__gte=timezone.now() - timezone.timedelta(minutes=15)
            ).count()
            
            if recent_failures >= 10:
                create_security_alert(
                    alert_type='multiple_failed_attempts',
                    severity='high',
                    title=f"Brute force attack detected from {ip_address}",
                    description=f"Multiple failed login attempts ({recent_failures}) from IP {ip_address}",
                    ip_address=ip_address
                ) 