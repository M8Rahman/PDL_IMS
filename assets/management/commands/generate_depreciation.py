# assets/management/commands/generate_depreciation.py
"""
Generate Depreciation Schedule Command
=======================================
Generates monthly depreciation schedules for all active assets.

Usage:
    python manage.py generate_depreciation
    python manage.py generate_depreciation --asset-tag AST-2025-00001
    python manage.py generate_depreciation --year 2025
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from assets.models import Asset, generate_depreciation_schedule
from datetime import date


class Command(BaseCommand):
    help = 'Generates monthly depreciation schedules for assets'

    def add_arguments(self, parser):
        parser.add_argument(
            '--asset-tag',
            type=str,
            help='Generate schedule for specific asset tag',
        )
        parser.add_argument(
            '--year',
            type=int,
            default=date.today().year,
            help='Generate schedule for specific year (default: current year)',
        )

    def handle(self, *args, **options):
        asset_tag = options.get('asset_tag')
        year = options.get('year')
        
        self.stdout.write(f'Generating depreciation schedules for year {year}...\n')
        
        # Get assets to process
        if asset_tag:
            assets = Asset.objects.filter(asset_tag=asset_tag)
            if not assets.exists():
                self.stdout.write(self.style.ERROR(f'Asset {asset_tag} not found'))
                return
                
        else:
            assets = Asset.objects.filter(
                is_active=True,
                depreciation_method__in=['STRAIGHT_LINE', 'DECLINING_BALANCE']
            ).exclude(current_status='DISPOSED')
        
        count = 0
        errors = 0
        
        with transaction.atomic():
            for asset in assets:
                try:
                    start_date = date(year, 1, 1)
                    end_date = date(year, 12, 31)
                    
                    # Only generate if asset was purchased before end of year
                    if asset.purchase_date and asset.purchase_date <= end_date:
                        generate_depreciation_schedule(
                            asset=asset,
                            start_date=max(asset.purchase_date, start_date),
                            end_date=end_date
                        )
                        count += 1
                        self.stdout.write(f'  ✓ Generated schedule for {asset.asset_tag}')
                except Exception as e:
                    errors += 1
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Error for {asset.asset_tag}: {str(e)}')
                    )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✓ Generated schedules for {count} asset(s)')
        )
        if errors:
            self.stdout.write(
                self.style.WARNING(f'⚠ {errors} error(s) occurred')
            )