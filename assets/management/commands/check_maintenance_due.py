"""
Check Maintenance Due Command
==============================
Checks for assets with maintenance due and sends notifications.

Usage:
    python manage.py check_maintenance_due
    python manage.py check_maintenance_due --days 7  # Check next 7 days
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from assets.models import Asset


class Command(BaseCommand):
    help = 'Checks for assets with maintenance due'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=0,
            help='Check maintenance due within X days (0 = today only)',
        )

    def handle(self, *args, **options):
        days = options.get('days')
        today = timezone.now().date()
        check_until = today + timedelta(days=days)
        
        self.stdout.write(
            f'Checking maintenance due from {today} to {check_until}...\n'
        )
        
        # Get assets with maintenance due
        assets = Asset.objects.filter(
            is_active=True,
            next_maintenance_date__lte=check_until,
            next_maintenance_date__gte=today
        ).exclude(current_status__in=['DISPOSED', 'RETIRED'])
        
        if not assets.exists():
            self.stdout.write(self.style.SUCCESS('✓ No maintenance due'))
            return
        
        # Group by due date
        by_date = {}
        for asset in assets:
            due_date = asset.next_maintenance_date
            if due_date not in by_date:
                by_date[due_date] = []
            by_date[due_date].append(asset)
        
        # Display results
        total = 0
        for due_date in sorted(by_date.keys()):
            assets_due = by_date[due_date]
            total += len(assets_due)
            
            days_until = (due_date - today).days
            if days_until == 0:
                status = self.style.ERROR('DUE TODAY')
            elif days_until <= 3:
                status = self.style.WARNING(f'DUE IN {days_until} DAYS')
            else:
                status = f'Due in {days_until} days'
            
            self.stdout.write(f'\n{status} - {due_date}:')
            for asset in assets_due:
                location = asset.location.location_code if asset.location else 'N/A'
                assigned = asset.assigned_to_user.full_name if asset.assigned_to_user else 'Unassigned'
                self.stdout.write(
                    f'  • {asset.asset_tag} - {asset.item.item_name} '
                    f'[{location}] ({assigned})'
                )
        
        self.stdout.write(
            self.style.WARNING(f'\n⚠ Total: {total} asset(s) need maintenance')
        )
        
        # TODO: Send notifications to relevant users
        # from notifications.utils import send_maintenance_due_notification
        # send_maintenance_due_notification(assets)