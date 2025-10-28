"""
Asset Report Command
====================
Generates a comprehensive asset report.

Usage:
    python manage.py asset_report
    python manage.py asset_report --status ASSIGNED
    python manage.py asset_report --export report.csv
"""

from django.core.management.base import BaseCommand
from assets.models import Asset
import csv


class Command(BaseCommand):
    help = 'Generates asset report'

    def add_arguments(self, parser):
        parser.add_argument(
            '--status',
            type=str,
            help='Filter by status',
        )
        parser.add_argument(
            '--export',
            type=str,
            help='Export to CSV file',
        )

    def handle(self, *args, **options):
        status_filter = options.get('status')
        export_file = options.get('export')
        
        # Get assets
        assets = Asset.objects.filter(is_active=True)
        if status_filter:
            assets = assets.filter(current_status=status_filter)
        
        # Calculate summary
        total_count = assets.count()
        total_value = sum(
            asset.current_book_value or 0 
            for asset in assets 
            if asset.current_book_value
        )
        
        # Display summary
        self.stdout.write('\n=== ASSET REPORT ===\n')
        self.stdout.write(f'Total Assets: {total_count}')
        self.stdout.write(f'Total Book Value: {total_value:,.2f} BDT\n')
        
        # Status breakdown
        status_counts = {}
        for asset in assets:
            status = asset.current_status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        self.stdout.write('Status Breakdown:')
        for status, count in sorted(status_counts.items()):
            self.stdout.write(f'  {status}: {count}')
        
        # Export to CSV if requested
        if export_file:
            with open(export_file, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    'Asset Tag', 'Serial No', 'Item', 'Status',
                    'Assigned To', 'Location', 'Purchase Date',
                    'Purchase Price', 'Current Book Value', 'Warranty End'
                ])
                
                for asset in assets:
                    writer.writerow([
                        asset.asset_tag,
                        asset.serial_no,
                        asset.item.item_name,
                        asset.current_status,
                        asset.assigned_to_user.full_name if asset.assigned_to_user else '',
                        asset.location.location_code if asset.location else '',
                        asset.purchase_date,
                        asset.purchase_price,
                        asset.current_book_value,
                        asset.warranty_end_date
                    ])
            
            self.stdout.write(
                self.style.SUCCESS(f'\n✓ Report exported to {export_file}')
            )