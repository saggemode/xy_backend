from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.utils import generate_security_report
from datetime import timedelta
import json

class Command(BaseCommand):
    help = 'Generate comprehensive security report'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to include in report (default: 30)'
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['json', 'text'],
            default='text',
            help='Output format (default: text)'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path (optional)'
        )

    def handle(self, *args, **options):
        days = options['days']
        output_format = options['format']
        output_file = options['output']
        
        # Calculate date range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Generate report
        report = generate_security_report(start_date, end_date)
        
        if output_format == 'json':
            output = json.dumps(report, indent=2, default=str)
        else:
            output = self._format_text_report(report)
        
        # Output to file or console
        if output_file:
            with open(output_file, 'w') as f:
                f.write(output)
            self.stdout.write(
                self.style.SUCCESS(f'Security report saved to {output_file}')
            )
        else:
            self.stdout.write(output)

    def _format_text_report(self, report):
        """Format report as readable text."""
        output = []
        output.append("=" * 60)
        output.append("SECURITY REPORT")
        output.append("=" * 60)
        output.append(f"Period: {report['period']['start']} to {report['period']['end']}")
        output.append("")
        
        # Audit Events
        output.append("AUDIT EVENTS")
        output.append("-" * 20)
        output.append(f"Total Events: {report['audit_events']['total']}")
        
        if report['audit_events']['by_action']:
            output.append("\nBy Action:")
            for action, count in report['audit_events']['by_action'].items():
                output.append(f"  {action}: {count}")
        
        if report['audit_events']['by_severity']:
            output.append("\nBy Severity:")
            for severity, count in report['audit_events']['by_severity'].items():
                output.append(f"  {severity}: {count}")
        
        # Security Alerts
        output.append("\nSECURITY ALERTS")
        output.append("-" * 20)
        output.append(f"Total Alerts: {report['security_alerts']['total']}")
        output.append(f"Open Alerts: {report['security_alerts']['open_alerts']}")
        
        if report['security_alerts']['by_type']:
            output.append("\nBy Type:")
            for alert_type, count in report['security_alerts']['by_type'].items():
                output.append(f"  {alert_type}: {count}")
        
        # User Sessions
        output.append("\nUSER SESSIONS")
        output.append("-" * 20)
        output.append(f"Total Sessions: {report['user_sessions']['total']}")
        output.append(f"Active Sessions: {report['user_sessions']['active']}")
        
        # Suspicious Activity
        output.append("\nSUSPICIOUS ACTIVITY")
        output.append("-" * 20)
        output.append(f"Failed Logins: {report['suspicious_activity']['failed_logins']}")
        output.append(f"New IP Logins: {report['suspicious_activity']['new_ip_logins']}")
        
        output.append("\n" + "=" * 60)
        
        return "\n".join(output) 