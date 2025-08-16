from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from bank.models import StaffRole, StaffProfile
from datetime import date


class Command(BaseCommand):
    help = 'Create sample staff members for testing the staff management system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--role',
            type=str,
            choices=['teller', 'customer_service', 'personal_banker', 'assistant_manager', 'manager', 'branch_manager'],
            default='teller',
            help='Role for the sample staff member'
        )
        parser.add_argument(
            '--username',
            type=str,
            default='sample_staff',
            help='Username for the sample staff member'
        )

    def handle(self, *args, **options):
        role_name = options['role']
        username = options['username']
        
        try:
            role = StaffRole.objects.get(name=role_name)
        except StaffRole.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Role "{role_name}" does not exist. Please run setup_staff_roles first.')
            )
            return
        
        # Create user
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@example.com',
                'first_name': 'Sample',
                'last_name': role_name.replace('_', ' ').title(),
                'is_staff': True,
                'is_active': True,
            }
        )
        
        if created:
            user.set_password('password123')
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'Created user: {username}')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'User {username} already exists')
            )
        
        # Create staff profile
        staff_profile, created = StaffProfile.objects.get_or_create(
            user=user,
            defaults={
                'role': role,
                'employee_id': f'EMP{user.id:04d}',
                'branch': 'Main Branch',
                'department': 'Operations',
                'is_active': True,
                'hire_date': date.today(),
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Created staff profile: {user.get_full_name()} - {role.name}'
                )
            )
            self.stdout.write(
                self.style.SUCCESS(f'Login credentials: {username} / password123')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Staff profile for {username} already exists')
            )
        
        # Display staff member details
        self.stdout.write('\nStaff Member Details:')
        self.stdout.write('=' * 40)
        self.stdout.write(f'Name: {user.get_full_name()}')
        self.stdout.write(f'Username: {user.username}')
        self.stdout.write(f'Email: {user.email}')
        self.stdout.write(f'Role: {role.name.title()}')
        self.stdout.write(f'Employee ID: {staff_profile.employee_id}')
        self.stdout.write(f'Branch: {staff_profile.branch}')
        self.stdout.write(f'Department: {staff_profile.department}')
        self.stdout.write(f'Max Approval Limit: ₦{role.max_transaction_approval:,.0f}')
        
        # Display permissions
        permissions = []
        if role.can_approve_kyc:
            permissions.append('KYC Approval')
        if role.can_manage_staff:
            permissions.append('Staff Management')
        if role.can_view_reports:
            permissions.append('View Reports')
        if role.can_override_transactions:
            permissions.append('Override Transactions')
        if role.can_handle_escalations:
            permissions.append('Handle Escalations')
        
        self.stdout.write(f'Permissions: {", ".join(permissions) if permissions else "None"}') 