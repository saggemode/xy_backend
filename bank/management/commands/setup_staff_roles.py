from django.core.management.base import BaseCommand
from bank.models import StaffRole


class Command(BaseCommand):
    help = 'Set up initial banking hall staff roles with hierarchical permissions'

    def handle(self, *args, **options):
        roles_data = [
            {
                'name': 'teller',
                'level': 1,
                'description': 'Handles basic transactions like deposits, withdrawals, and cashing checks. First point of contact for customers.',
                'max_transaction_approval': 50000.00,  # ₦50,000
                'can_approve_kyc': False,
                'can_manage_staff': False,
                'can_view_reports': False,
                'can_override_transactions': False,
                'can_handle_escalations': False,
            },
            {
                'name': 'customer_service',
                'level': 2,
                'description': 'Assists customers with inquiries, account maintenance, and problem resolution. Handles a wider range of customer needs.',
                'max_transaction_approval': 100000.00,  # ₦100,000
                'can_approve_kyc': False,
                'can_manage_staff': False,
                'can_view_reports': True,
                'can_override_transactions': False,
                'can_handle_escalations': True,
            },
            {
                'name': 'personal_banker',
                'level': 3,
                'description': 'Builds relationships with clients, offers financial advice, and helps customers manage their accounts and investments.',
                'max_transaction_approval': 500000.00,  # ₦500,000
                'can_approve_kyc': True,
                'can_manage_staff': False,
                'can_view_reports': True,
                'can_override_transactions': True,
                'can_handle_escalations': True,
            },
            {
                'name': 'assistant_manager',
                'level': 4,
                'description': 'Supports branch manager in day-to-day operations, oversees specific areas or teams, and handles customer escalations.',
                'max_transaction_approval': 1000000.00,  # ₦1,000,000
                'can_approve_kyc': True,
                'can_manage_staff': True,
                'can_view_reports': True,
                'can_override_transactions': True,
                'can_handle_escalations': True,
            },
            {
                'name': 'manager',
                'level': 5,
                'description': 'Responsible for overall performance of specific departments or functions within the branch, such as lending or operations.',
                'max_transaction_approval': 5000000.00,  # ₦5,000,000
                'can_approve_kyc': True,
                'can_manage_staff': True,
                'can_view_reports': True,
                'can_override_transactions': True,
                'can_handle_escalations': True,
            },
            {
                'name': 'branch_manager',
                'level': 6,
                'description': 'Leader of the branch, responsible for overall success including sales, customer satisfaction, and staff management.',
                'max_transaction_approval': 10000000.00,  # ₦10,000,000
                'can_approve_kyc': True,
                'can_manage_staff': True,
                'can_view_reports': True,
                'can_override_transactions': True,
                'can_handle_escalations': True,
            },
        ]

        created_count = 0
        updated_count = 0

        for role_data in roles_data:
            role, created = StaffRole.objects.update_or_create(
                name=role_data['name'],
                defaults=role_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created role: {role.name} (Level {role.level})')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated role: {role.name} (Level {role.level})')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully set up {created_count} new roles and updated {updated_count} existing roles.'
            )
        )
        
        # Display summary
        self.stdout.write('\nRole Hierarchy Summary:')
        self.stdout.write('=' * 50)
        for role in StaffRole.objects.all().order_by('level'):
            permissions = []
            if role.can_approve_kyc:
                permissions.append('KYC')
            if role.can_manage_staff:
                permissions.append('Staff Mgmt')
            if role.can_view_reports:
                permissions.append('Reports')
            if role.can_override_transactions:
                permissions.append('Override')
            if role.can_handle_escalations:
                permissions.append('Escalations')
            
            self.stdout.write(
                f'{role.level}. {role.name.title()} - '
                f'Max Approval: ₦{role.max_transaction_approval:,.0f} - '
                f'Permissions: {", ".join(permissions) if permissions else "None"}'
            ) 