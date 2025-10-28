"""
Check Warranty Expiring Command
================================
Checks for assets with warranty expiring soon.

Usage:
    python manage.py check_warranty_expiring
    python manage.py check_warranty_expiring --days 30  # Check next 30 days
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from assets.models import Asset


class Command(BaseCommand):
    help = 'Checks for assets with warranty expiring soon'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Check warranty expiring within X days (default: 30)',
        )

    def handle(self, *args, **options):
        days = options.get('days')
        today = timezone.now().date()
        check_until = today + timedelta(days=days)
        
        self.stdout.write(
            f'Checking warranty expiring from {today} to {check_until}...\n'
        )
        
        # Get assets with warranty expiring
        assets = Asset.objects.filter(
            is_active=True,
            warranty_end_date__lte=check_until,
            warranty_end_date__gte=today
        ).exclude(current_status__in=['DISPOSED', 'RETIRED'])
        
        if not assets.exists():
            self.stdout.write(
                self.style.SUCCESS('✓ No warranties expiring in this period')
            )
            return
        
        # Display results
        self.stdout.write('Assets with expiring warranty:\n')
        for asset in assets:
            days_left = (asset.warranty_end_date - today).days
            
            if days_left == 0:
                status = self.style.ERROR('EXPIRES TODAY')
            elif days_left <= 7:
                status = self.style.ERROR(f'{days_left} days left')
            elif days_left <= 30:
                status = self.style.WARNING(f'{days_left} days left')
            else:
                status = f'{days_left} days left'
            
            location = asset.location.location_code if asset.location else 'N/A'
            assigned = asset.assigned_to_user.full_name if asset.assigned_to_user else 'Unassigned'
            
            self.stdout.write(
                f'  • {asset.asset_tag} - {asset.item.item_name} '
                f'[{status}] - {asset.warranty_end_date} '
                f'[{location}] ({assigned})'
            )
        
        self.stdout.write(
            self.style.WARNING(f'\n⚠ Total: {assets.count()} asset(s) with expiring warranty')
        )