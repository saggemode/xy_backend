from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, AuditLog, SecurityAlert, UserSession, KYCProfile
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Sum, Avg, Q
from django.contrib.admin import SimpleListFilter
from django.utils.safestring import mark_safe
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django import forms
from notification.models import Notification

# Custom Filters
class VerificationStatusFilter(SimpleListFilter):
    title = 'Verification Status'
    parameter_name = 'verification_status'

    def lookups(self, request, model_admin):
        return (
            ('verified', 'Verified'),
            ('unverified', 'Unverified'),
            ('pending', 'Pending'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'verified':
            return queryset.filter(profile__is_verified=True)
        if self.value() == 'unverified':
            return queryset.filter(profile__is_verified=False)
        if self.value() == 'pending':
            return queryset.filter(profile__is_verified=False, profile__otp_code__isnull=False)

class RegistrationDateFilter(SimpleListFilter):
    title = 'Registration Date'
    parameter_name = 'registration_date'

    def lookups(self, request, model_admin):
        return (
            ('today', 'Today'),
            ('week', 'This Week'),
            ('month', 'This Month'),
            ('quarter', 'This Quarter'),
        )

    def queryset(self, request, queryset):
        today = timezone.now().date()
        if self.value() == 'today':
            return queryset.filter(date_joined__date=today)
        if self.value() == 'week':
            return queryset.filter(date_joined__gte=today - timedelta(days=7))
        if self.value() == 'month':
            return queryset.filter(date_joined__gte=today - timedelta(days=30))
        if self.value() == 'quarter':
            return queryset.filter(date_joined__gte=today - timedelta(days=90))

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    fields = ('phone', 'is_verified', 'otp_code', 'otp_expiry')
    readonly_fields = ('otp_code', 'otp_expiry')

class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'phone_number', 'is_verified', 'registration_date', 'last_login', 'is_active', 'actions_column')
    list_filter = (
        'is_active', 'is_staff', 'is_superuser', 'date_joined', 
        VerificationStatusFilter, RegistrationDateFilter,
        ('profile__is_verified', admin.BooleanFieldListFilter),
    )
    search_fields = ('username', 'email', 'profile__phone', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    list_per_page = 25
    list_max_show_all = 1000
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('username', 'password', 'first_name', 'last_name', 'email')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )
    
    def phone_number(self, obj):
        return obj.profile.phone if hasattr(obj, 'profile') else 'N/A'
    phone_number.short_description = 'Phone Number'
    phone_number.admin_order_field = 'profile__phone'
    
    def is_verified(self, obj):
        if hasattr(obj, 'profile'):
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                'green' if obj.profile.is_verified else 'red',
                '✓ Verified' if obj.profile.is_verified else '✗ Unverified'
            )
        return 'N/A'
    is_verified.short_description = 'Verification Status'
    is_verified.admin_order_field = 'profile__is_verified'
    
    def registration_date(self, obj):
        return format_html(
            '<span title="{}">{}</span>',
            obj.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
            obj.date_joined.strftime('%Y-%m-%d')
        )
    registration_date.short_description = 'Registration Date'
    registration_date.admin_order_field = 'date_joined'
    
    def actions_column(self, obj):
        return format_html(
            '<div class="btn-group" role="group">'
            '<a href="{}" class="btn btn-sm btn-primary" title="View Details">👁</a> '
            '<a href="{}" class="btn btn-sm btn-success" title="Verify User">✓</a> '
            '<a href="{}" class="btn btn-sm btn-warning" title="Suspend User">⏸</a> '
            '</div>',
            reverse('admin:auth_user_change', args=[obj.id]),
            reverse('admin:auth_user_change', args=[obj.id]) + '?action=verify',
            reverse('admin:auth_user_change', args=[obj.id]) + '?action=suspend'
        )
    actions_column.short_description = 'Actions'
    
    actions = ['bulk_verify_users', 'bulk_suspend_users', 'export_user_data', 'generate_user_report', 'send_welcome_email']
    
    def bulk_verify_users(self, request, queryset):
        updated = 0
        for user in queryset:
            if hasattr(user, 'profile'):
                user.profile.is_verified = True
                user.profile.save()
                updated += 1
        
        self.message_user(request, f'Successfully verified {updated} users.')
    bulk_verify_users.short_description = "Verify selected users"
    
    def bulk_suspend_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Successfully suspended {updated} users.')
    bulk_suspend_users.short_description = "Suspend selected users"
    
    def export_user_data(self, request, queryset):
        user_ids = ','.join(str(user.id) for user in queryset)
        return HttpResponseRedirect(f'/accounts/admin/api/user-export/?user_ids={user_ids}')
    export_user_data.short_description = "Export selected users"
    
    def generate_user_report(self, request, queryset):
        total_users = queryset.count()
        verified_users = queryset.filter(profile__is_verified=True).count()
        recent_users = queryset.filter(date_joined__gte=timezone.now() - timedelta(days=30)).count()
        
        message = f"""
        User Report for {total_users} selected users:
        - Verified Users: {verified_users} ({(verified_users/total_users*100):.1f}%)
        - Recent Users (30 days): {recent_users}
        - Average Registration Date: {queryset.aggregate(avg_date=Avg('date_joined'))['avg_date'].strftime('%Y-%m-%d') if queryset.exists() else 'N/A'}
        """
        self.message_user(request, message)
    generate_user_report.short_description = "Generate user report"
    
    def send_welcome_email(self, request, queryset):
        # Placeholder for welcome email functionality
        self.message_user(request, f'Welcome emails would be sent to {queryset.count()} users.')
    send_welcome_email.short_description = "Send welcome email"

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'severity', 'ip_address', 'description_preview', 'duration')
    list_filter = ('action', 'severity', 'timestamp', 'user', 'ip_address')
    search_fields = ('user__username', 'user__email', 'description', 'ip_address', 'action')
    readonly_fields = ('timestamp', 'user', 'action', 'description', 'ip_address', 'user_agent', 'severity', 'content_type', 'object_id', 'metadata')
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'
    list_per_page = 50
    
    fieldsets = (
        ('Event Information', {
            'fields': ('timestamp', 'action', 'description', 'severity')
        }),
        ('User Information', {
            'fields': ('user', 'ip_address', 'user_agent')
        }),
        ('Object Information', {
            'fields': ('content_type', 'object_id'),
            'classes': ('collapse',)
        }),
        ('Additional Data', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )
    
    def description_preview(self, obj):
        return obj.description[:100] + '...' if len(obj.description) > 100 else obj.description
    description_preview.short_description = 'Description'
    
    def duration(self, obj):
        # Calculate duration if there's a related event
        return 'N/A'
    duration.short_description = 'Duration'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    actions = ['export_audit_logs', 'analyze_patterns']
    
    def export_audit_logs(self, request, queryset):
        # Implementation for CSV export
        self.message_user(request, f'Exporting {queryset.count()} audit logs...')
    export_audit_logs.short_description = "Export audit logs to CSV"
    
    def analyze_patterns(self, request, queryset):
        # Analyze patterns in audit logs
        patterns = queryset.values('action').annotate(count=Count('id')).order_by('-count')[:5]
        pattern_text = '\n'.join([f"- {p['action']}: {p['count']} events" for p in patterns])
        self.message_user(request, f'Top 5 patterns:\n{pattern_text}')
    analyze_patterns.short_description = "Analyze patterns"

@admin.register(SecurityAlert)
class SecurityAlertAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'alert_type', 'severity', 'status', 'affected_user', 'ip_address', 'title', 'response_time')
    list_filter = ('alert_type', 'severity', 'status', 'timestamp', 'affected_user')
    search_fields = ('title', 'description', 'affected_user__username', 'ip_address', 'alert_type')
    readonly_fields = ('timestamp', 'alert_type', 'severity', 'title', 'description', 'affected_user', 'ip_address')
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'
    list_per_page = 25
    
    fieldsets = (
        ('Alert Information', {
            'fields': ('alert_type', 'severity', 'title', 'description')
        }),
        ('Affected User', {
            'fields': ('affected_user', 'ip_address')
        }),
        ('Status Management', {
            'fields': ('status', 'resolved_at', 'resolved_by', 'notes')
        }),
    )
    
    def response_time(self, obj):
        if obj.resolved_at and obj.timestamp:
            duration = obj.resolved_at - obj.timestamp
            hours = duration.total_seconds() / 3600
            return f"{hours:.1f}h"
        return 'Open'
    response_time.short_description = 'Response Time'
    
    actions = ['mark_as_investigating', 'mark_as_resolved', 'mark_as_false_positive', 'escalate_alert']
    
    def mark_as_investigating(self, request, queryset):
        updated = queryset.update(status='investigating')
        self.message_user(request, f'Marked {updated} alerts as investigating.')
    mark_as_investigating.short_description = "Mark as investigating"
    
    def mark_as_resolved(self, request, queryset):
        updated = queryset.update(
            status='resolved',
            resolved_at=timezone.now(),
            resolved_by=request.user
        )
        self.message_user(request, f'Marked {updated} alerts as resolved.')
    mark_as_resolved.short_description = "Mark as resolved"
    
    def mark_as_false_positive(self, request, queryset):
        updated = queryset.update(status='false_positive')
        self.message_user(request, f'Marked {updated} alerts as false positive.')
    mark_as_false_positive.short_description = "Mark as false positive"
    
    def escalate_alert(self, request, queryset):
        # Escalate critical alerts
        critical_alerts = queryset.filter(severity='critical', status='open')
        updated = critical_alerts.update(severity='critical')
        self.message_user(request, f'Escalated {updated} critical alerts.')
    escalate_alert.short_description = "Escalate critical alerts"

@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'ip_address', 'created_at', 'last_activity', 'is_active', 'session_duration', 'location')
    list_filter = ('is_active', 'created_at', 'last_activity', 'ip_address')
    search_fields = ('user__username', 'user__email', 'ip_address', 'session_key')
    readonly_fields = ('user', 'session_key', 'ip_address', 'user_agent', 'created_at', 'last_activity')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    list_per_page = 50
    
    fieldsets = (
        ('Session Information', {
            'fields': ('user', 'session_key', 'is_active')
        }),
        ('Connection Details', {
            'fields': ('ip_address', 'user_agent')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'last_activity')
        }),
    )
    
    def session_duration(self, obj):
        if obj.last_activity and obj.created_at:
            duration = obj.last_activity - obj.created_at
            hours = duration.total_seconds() / 3600
            return f"{hours:.1f} hours"
        return 'N/A'
    session_duration.short_description = 'Session Duration'
    
    def location(self, obj):
        # Placeholder for IP geolocation
        return 'Unknown'
    location.short_description = 'Location'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    actions = ['terminate_sessions', 'analyze_sessions']
    
    def terminate_sessions(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Terminated {updated} sessions.')
    terminate_sessions.short_description = "Terminate selected sessions"
    
    def analyze_sessions(self, request, queryset):
        # Analyze session patterns
        total_sessions = queryset.count()
        active_sessions = queryset.filter(is_active=True).count()
        avg_duration = queryset.aggregate(avg_duration=Avg('last_activity' - 'created_at'))
        
        self.message_user(request, f'Session Analysis:\n- Total: {total_sessions}\n- Active: {active_sessions}\n- Avg Duration: {avg_duration}')
    analyze_sessions.short_description = "Analyze sessions"

class RejectKYCForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    rejection_reason = forms.CharField(widget=forms.Textarea, label="Rejection Reason")

@admin.register(KYCProfile)
class KYCProfileAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'bvn', 'nin', 'kyc_level', 'date_of_birth', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'kyc_level', 'created_at')
    search_fields = ('user__username', 'user__email', 'bvn', 'nin', 'address')
    readonly_fields = (
        'id', 'created_at', 'updated_at',
        'passport_photo_preview', 'selfie_preview', 'id_document_preview'
    )
    ordering = ('-created_at',)
    list_per_page = 25

    actions = [
        'approve_kyc', 
        'reject_kyc_with_reason', 
        'export_kyc', 
        'upgrade_to_tier_2', 
        'upgrade_to_tier_3', 
        'downgrade_to_tier_1',
        'show_tier_requirements',
        'check_upgrade_eligibility'
    ]

    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('KYC Details', {
            'fields': (
                'bvn', 'nin', 'kyc_level', 'date_of_birth', 'address', 'id_document',
                'passport_photo', 'passport_photo_preview',
                'selfie', 'selfie_preview',
                'govt_id_type', 'govt_id_document', 'proof_of_address', 'id_document_preview'
            )
        }),
        ('Status', {
            'fields': ('is_approved', 'approved_by', 'approved_at', 'rejection_reason')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def has_add_permission(self, request):
        return True  # Allow creating new KYC profiles

    def has_change_permission(self, request, obj=None):
        return True  # Allow editing

    def has_delete_permission(self, request, obj=None):
        return True  # Allow deleting

    def upgrade_to_tier_2(self, request, queryset):
        success_count = 0
        error_messages = []
        
        for obj in queryset:
            try:
                can_upgrade, message = obj.can_upgrade_to_tier_2()
                if can_upgrade:
                    obj.kyc_level = 'tier_2'
                    obj.save()
                    success_count += 1
                else:
                    error_messages.append(f"{obj.user.username}: {message}")
            except Exception as e:
                error_messages.append(f"{obj.user.username}: {str(e)}")
        
        if success_count > 0:
            self.message_user(request, f'Successfully upgraded {success_count} KYC profiles to Tier 2.')
        
        if error_messages:
            error_msg = "Failed upgrades:\n" + "\n".join(error_messages[:5])  # Show first 5 errors
            if len(error_messages) > 5:
                error_msg += f"\n... and {len(error_messages) - 5} more"
            self.message_user(request, error_msg, level='error')
    
    upgrade_to_tier_2.short_description = "Upgrade selected to Tier 2 (with validation)"

    def upgrade_to_tier_3(self, request, queryset):
        success_count = 0
        error_messages = []
        
        for obj in queryset:
            try:
                can_upgrade, message = obj.can_upgrade_to_tier_3()
                if can_upgrade:
                    obj.kyc_level = 'tier_3'
                    obj.save()
                    success_count += 1
                else:
                    error_messages.append(f"{obj.user.username}: {message}")
            except Exception as e:
                error_messages.append(f"{obj.user.username}: {str(e)}")
        
        if success_count > 0:
            self.message_user(request, f'Successfully upgraded {success_count} KYC profiles to Tier 3.')
        
        if error_messages:
            error_msg = "Failed upgrades:\n" + "\n".join(error_messages[:5])  # Show first 5 errors
            if len(error_messages) > 5:
                error_msg += f"\n... and {len(error_messages) - 5} more"
            self.message_user(request, error_msg, level='error')
    
    upgrade_to_tier_3.short_description = "Upgrade selected to Tier 3 (with validation)"

    def downgrade_to_tier_1(self, request, queryset):
        updated = queryset.update(kyc_level='tier_1')
        self.message_user(request, f'Successfully downgraded {updated} KYC profiles to Tier 1.')
    downgrade_to_tier_1.short_description = "Downgrade selected to Tier 1"

    def show_tier_requirements(self, request, queryset):
        """Show tier upgrade requirements for selected profiles."""
        requirements_info = []
        
        for obj in queryset:
            current_tier = obj.get_kyc_level_display()
            available_upgrades = obj.get_available_upgrades()
            
            info = f"User: {obj.user.username}\n"
            info += f"Current Tier: {current_tier}\n"
            
            if available_upgrades:
                info += "Available Upgrades:\n"
                for upgrade in available_upgrades:
                    info += f"- {upgrade['display_name']}\n"
                    for req in upgrade['requirements']['requirements']:
                        info += f"  • {req}\n"
            else:
                info += "No upgrades available\n"
                if obj.kyc_level == 'tier_1':
                    info += "Requirements for Tier 2:\n"
                    reqs = obj.get_upgrade_requirements('tier_2')
                    for req in reqs['requirements']:
                        info += f"  • {req}\n"
                elif obj.kyc_level == 'tier_2':
                    info += "Requirements for Tier 3:\n"
                    reqs = obj.get_upgrade_requirements('tier_3')
                    for req in reqs['requirements']:
                        info += f"  • {req}\n"
            
            requirements_info.append(info)
        
        # Create a simple message with requirements
        message = f"Tier Requirements for {len(queryset)} selected profiles:\n\n"
        for i, info in enumerate(requirements_info[:3]):  # Show first 3
            message += f"--- Profile {i+1} ---\n{info}\n"
        
        if len(requirements_info) > 3:
            message += f"... and {len(requirements_info) - 3} more profiles"
        
        self.message_user(request, message)
    
    show_tier_requirements.short_description = "Show tier upgrade requirements"

    def check_upgrade_eligibility(self, request, queryset):
        """Check upgrade eligibility for selected profiles."""
        eligible_tier_2 = 0
        eligible_tier_3 = 0
        ineligible = 0
        
        for obj in queryset:
            can_tier_2, _ = obj.can_upgrade_to_tier_2()
            can_tier_3, _ = obj.can_upgrade_to_tier_3()
            
            if can_tier_2:
                eligible_tier_2 += 1
            elif can_tier_3:
                eligible_tier_3 += 1
            else:
                ineligible += 1
        
        message = f"Upgrade Eligibility Summary:\n"
        message += f"- Eligible for Tier 2: {eligible_tier_2}\n"
        message += f"- Eligible for Tier 3: {eligible_tier_3}\n"
        message += f"- Not eligible: {ineligible}\n"
        message += f"- Total checked: {len(queryset)}"
        
        self.message_user(request, message)
    
    check_upgrade_eligibility.short_description = "Check upgrade eligibility"

    def approve_kyc(self, request, queryset):
        updated = 0
        for obj in queryset:
            if not obj.is_approved:
                if not obj.bvn and not obj.nin:
                    self.message_user(request, f"KYC for {obj.user} missing BVN/NIN.", level='error')
                    continue
                obj.is_approved = True
                obj.approved_by = request.user
                obj.approved_at = timezone.now()
                obj.rejection_reason = ''
                obj.save()
                # In-app notification
                Notification.objects.create(
                    user=obj.user,
                    title="KYC Approved",
                    message="Your KYC has been approved."
                )
                # Email
                subject = "KYC Approved"
                html_content = render_to_string("emails/kyc_approved.html", {"user": obj.user})
                msg = EmailMultiAlternatives(subject, "", "no-reply@yourapp.com", [obj.user.email])
                msg.attach_alternative(html_content, "text/html")
                msg.send()
                updated += 1
        self.message_user(request, f"Approved {updated} KYC profiles.")
    approve_kyc.short_description = "Approve selected KYC profiles"

    def reject_kyc_with_reason(self, request, queryset):
        if 'apply' in request.POST:
            reason = request.POST['rejection_reason']
            for obj in queryset:
                obj.is_approved = False
                obj.rejection_reason = reason
                obj.approved_by = request.user
                obj.approved_at = timezone.now()
                obj.save()
                # In-app notification
                Notification.objects.create(
                    user=obj.user,
                    title="KYC Rejected",
                    message=f"Your KYC has been rejected. Reason: {reason}"
                )
                # Email
                subject = "KYC Rejected"
                html_content = render_to_string("emails/kyc_rejected.html", {"user": obj.user, "reason": reason})
                msg = EmailMultiAlternatives(subject, "", "no-reply@yourapp.com", [obj.user.email])
                msg.attach_alternative(html_content, "text/html")
                msg.send()
            self.message_user(request, f"Rejected {queryset.count()} KYC profiles.")
            return None
        else:
            form = RejectKYCForm(initial={'_selected_action': queryset.values_list('pk', flat=True)})
            return admin.helpers.render_action_form(
                request, form, 'reject_kyc_with_reason', queryset
            )
    reject_kyc_with_reason.short_description = "Reject selected KYC profiles (with reason popup)"

    def export_kyc(self, request, queryset):
        import csv
        from django.http import HttpResponse
        fieldnames = ['user', 'bvn', 'nin', 'kyc_level', 'date_of_birth', 'is_approved', 'created_at', 'approved_by', 'approved_at', 'rejection_reason']
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="kyc_profiles.csv"'
        writer = csv.writer(response)
        writer.writerow(fieldnames)
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in fieldnames])
        return response
    export_kyc.short_description = "Export selected KYC profiles as CSV"

    def user_link(self, obj):
        if obj.user:
            return format_html('<a href="{}">{}</a>',
                               reverse('admin:auth_user_change', args=[obj.user.id]),
                               obj.user.username)
        return 'N/A'
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'

    def passport_photo_preview(self, obj):
        if obj.passport_photo:
            return format_html('<img src="{}" width="100" />', obj.passport_photo.url)
        return "No photo"
    passport_photo_preview.short_description = "Passport Photo"

    def selfie_preview(self, obj):
        if obj.selfie:
            return format_html('<img src="{}" width="100" />', obj.selfie.url)
        return "No selfie"
    selfie_preview.short_description = "Selfie"

    def id_document_preview(self, obj):
        if obj.id_document:
            return format_html('<a href="{}" target="_blank">View Document</a>', obj.id_document.url)
        return "No document"
    id_document_preview.short_description = "ID Document"

# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

class ResetTransactionPinForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    new_pin = forms.CharField(label='New Transaction PIN', min_length=4, max_length=10, widget=forms.PasswordInput)

class UserProfileAdmin(admin.ModelAdmin):
    exclude = ('transaction_pin',)
    actions = ['reset_transaction_pin']

    def reset_transaction_pin(self, request, queryset):
        if 'apply' in request.POST:
            form = ResetTransactionPinForm(request.POST)
            if form.is_valid():
                new_pin = form.cleaned_data['new_pin']
                for profile in queryset:
                    profile.set_transaction_pin(new_pin)
                self.message_user(request, f"Transaction PIN reset for {queryset.count()} user(s).", messages.SUCCESS)
                return
        else:
            form = ResetTransactionPinForm(initial={'_selected_action': request.POST.getlist(admin.ACTION_CHECKBOX_NAME)})
        return admin.helpers.render_action_form(
            request,
            form,
            'Reset Transaction PIN for selected users',
            action_short_description='Reset Transaction PIN',
            action_checkbox_name=admin.ACTION_CHECKBOX_NAME
        )
    reset_transaction_pin.short_description = "Reset transaction PIN for selected users"

admin.site.register(UserProfile, UserProfileAdmin)
