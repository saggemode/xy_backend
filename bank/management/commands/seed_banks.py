import requests
import json
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from bank.models import Bank
from pathlib import Path

class Command(BaseCommand):
    help = 'Seed Bank model with data from Nigerian banks API and always merge with local custom banks from JSON file.'

    def handle(self, *args, **options):
        self.stdout.write('Fetching banks from Nigerian banks API...')
        banks_data = []
        api_used = False
        local_used = False
        # Try API first
        try:
            response = requests.get('https://nigerianbanks.xyz/')
            response.raise_for_status()
            banks_data = response.json()
            api_used = True
            self.stdout.write(self.style.SUCCESS('Loaded banks from API.'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'API unavailable: {str(e)}'))

        # Always load local custom banks and merge
        json_path = Path(__file__).parent / 'seed_banks.json'
        local_banks = []
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                local_banks = json.load(f)
            local_used = True
            self.stdout.write(self.style.SUCCESS('Loaded banks from local seed_banks.json.'))
        else:
            self.stdout.write(self.style.WARNING('No local seed_banks.json found.'))

        # Merge: local custom banks override API banks by code
        all_banks_by_code = {b['code']: b for b in banks_data if b.get('code')}
        for b in local_banks:
            if b.get('code'):
                all_banks_by_code[b['code']] = b  # local overrides API
        merged_banks = list(all_banks_by_code.values())

        if not merged_banks:
            self.stdout.write(self.style.ERROR('No banks found from API or local JSON. Cannot proceed.'))
            return

        self.stdout.write(f'Found {len(merged_banks)} unique banks (merged).')
        created_count = 0
        updated_count = 0
        skipped_count = 0
        for bank_data in merged_banks:
            try:
                name = bank_data.get('name', '').strip()
                code = bank_data.get('code', '').strip()
                ussd = bank_data.get('ussd', '').strip()
                logo = bank_data.get('logo', '').strip()
                if not name or not code:
                    self.stdout.write(
                        self.style.WARNING(f'Skipping bank with missing name or code: {bank_data}')
                    )
                    skipped_count += 1
                    continue
                slug = slugify(name)
                bank, created = Bank.objects.get_or_create(
                    code=code,
                    defaults={
                        'name': name,
                        'slug': slug,
                        'ussd': ussd if ussd else None,
                        'logo': logo if logo else None,
                    }
                )
                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'Created: {name} ({code})')
                    )
                else:
                    updated = False
                    if bank.name != name or bank.slug != slug or bank.ussd != ussd or bank.logo != logo:
                        bank.name = name
                        bank.slug = slug
                        bank.ussd = ussd if ussd else None
                        bank.logo = logo if logo else None
                        bank.save()
                        updated_count += 1
                        self.stdout.write(
                            self.style.WARNING(f'Updated: {name} ({code})')
                        )
                    else:
                        self.stdout.write(
                            self.style.SUCCESS(f'Already exists: {name} ({code})')
                        )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing bank {bank_data}: {str(e)}')
                )
                skipped_count += 1
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('Bank seeding completed!'))
        self.stdout.write(f'Created: {created_count} banks')
        self.stdout.write(f'Updated: {updated_count} banks')
        self.stdout.write(f'Skipped: {skipped_count} banks')
        self.stdout.write(f'Total banks in database: {Bank.objects.count()}')
        self.stdout.write('='*50)
        # Log which sources were used
        if api_used and local_used:
            self.stdout.write(self.style.SUCCESS('Merged API and local custom banks.'))
        elif api_used:
            self.stdout.write(self.style.SUCCESS('Used only API banks.'))
        elif local_used:
            self.stdout.write(self.style.SUCCESS('Used only local custom banks.'))
        else:
            self.stdout.write(self.style.ERROR('No bank data source was available.')) 