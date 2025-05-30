from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site

class Command(BaseCommand):
    help = 'Creates the default site'

    def handle(self, *args, **options):
        if not Site.objects.exists():
            Site.objects.create(
                id=1,
                domain='example.com',
                name='example.com'
            )
            self.stdout.write(self.style.SUCCESS('Successfully created default site'))
        else:
            self.stdout.write(self.style.SUCCESS('Default site already exists')) 