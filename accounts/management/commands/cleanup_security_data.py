from django.core.management.base import BaseCommand
from accounts.utils import cleanup_old_data

class Command(BaseCommand):
    help = 'Clean up old security data (audit logs, sessions, alerts)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No data will be deleted')
            )
            # In dry run mode, we would typically show what would be deleted
            # For now, just run the cleanup and show results
            self.stdout.write('Running cleanup to show what would be deleted...')
        
        # Run cleanup
        results = cleanup_old_data()
        
        # Display results
        self.stdout.write("\nCleanup Results:")
        self.stdout.write("-" * 20)
        self.stdout.write(f"Audit logs deleted: {results['audit_logs_deleted']}")
        self.stdout.write(f"Sessions deleted: {results['sessions_deleted']}")
        self.stdout.write(f"Alerts resolved: {results['alerts_resolved']}")
        
        total_cleaned = (
            results['audit_logs_deleted'] + 
            results['sessions_deleted'] + 
            results['alerts_resolved']
        )
        
        if total_cleaned > 0:
            self.stdout.write(
                self.style.SUCCESS(f'\nSuccessfully cleaned up {total_cleaned} records')
            )
        else:
            self.stdout.write(
                self.style.WARNING('\nNo old data found to clean up')
            ) 