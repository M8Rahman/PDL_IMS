"""
Seed Master Data Command
========================
Populates currencies, UOMs, basic categories, colors, sizes, and statuses.

Usage:
    python manage.py seed_master_data
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from inventory.models import (
    Currency, UnitOfMeasurement, ItemCategory, Color, Size, StatusMaster
)


class Command(BaseCommand):
    help = 'Seeds master data (currencies, UOMs, categories, colors, sizes, statuses)'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting master data seeding...\n')
        
        with transaction.atomic():
            self.seed_currencies()
            self.seed_uoms()
            self.seed_categories()
            self.seed_colors()
            self.seed_sizes()
            self.seed_statuses()
        
        self.stdout.write(self.style.SUCCESS('\n✓ Master data seeding completed successfully!'))

    def seed_currencies(self):
        """Create default currencies."""
        self.stdout.write('Creating currencies...')
        
        currencies = [
            {'code': 'BDT', 'symbol': '৳', 'name': 'Bangladeshi Taka', 'base': True},
            {'code': 'USD', 'symbol': '$', 'name': 'US Dollar', 'base': False},
            {'code': 'EUR', 'symbol': '€', 'name': 'Euro', 'base': False},
            {'code': 'GBP', 'symbol': '£', 'name': 'British Pound', 'base': False},
        ]
        
        for curr in currencies:
            Currency.objects.get_or_create(
                currency_code=curr['code'],
                defaults={
                    'symbol': curr['symbol'],
                    'name': curr['name'],
                    'is_base_currency': curr['base']
                }
            )
        
        self.stdout.write(f'  ✓ Created {len(currencies)} currencies')

    def seed_uoms(self):
        """Create default UOMs."""
        self.stdout.write('Creating UOMs...')
        
        uoms = [
            ('KG', 'Kilogram', 'WEIGHT'),
            ('GM', 'Gram', 'WEIGHT'),
            ('PCS', 'Pieces', 'QUANTITY'),
            ('MTR', 'Meter', 'LENGTH'),
            ('YRD', 'Yard', 'LENGTH'),
            ('ROLL', 'Roll', 'QUANTITY'),
            ('DOZEN', 'Dozen', 'QUANTITY'),
            ('SET', 'Set', 'QUANTITY'),
            ('LTR', 'Liter', 'VOLUME'),
            ('BOX', 'Box', 'QUANTITY'),
        ]
        
        for code, name, uom_type in uoms:
            UnitOfMeasurement.objects.get_or_create(
                uom_code=code,
                defaults={
                    'name': name,
                    'uom_type': uom_type
                }
            )
        
        self.stdout.write(f'  ✓ Created {len(uoms)} UOMs')

    def seed_categories(self):
        """Create default item categories."""
        self.stdout.write('Creating item categories...')
        
        categories = [
            ('YARN', 'Yarn', 'YARN', None),
            ('FABRIC', 'Fabric', 'FABRIC', None),
            ('ACC', 'Accessories', 'ACCESSORIES', None),
            ('GEN', 'General Items', 'GENERAL', None),
            ('SPARE', 'Spare Parts', 'SPARES', None),
            ('IT', 'IT Equipment', 'IT', None),
        ]
        
        for code, name, cat_type, parent in categories:
            ItemCategory.objects.get_or_create(
                category_code=code,
                defaults={
                    'name': name,
                    'category_type': cat_type,
                    'parent_category': parent,
                    'is_active': True
                }
            )
        
        self.stdout.write(f'  ✓ Created {len(categories)} categories')

    def seed_colors(self):
        """Create default colors."""
        self.stdout.write('Creating colors...')
        
        colors = [
            ('WHT', 'White', '#FFFFFF'),
            ('BLK', 'Black', '#000000'),
            ('RED', 'Red', '#FF0000'),
            ('BLUE', 'Blue', '#0000FF'),
            ('GRN', 'Green', '#008000'),
            ('YLW', 'Yellow', '#FFFF00'),
            ('NAVY', 'Navy Blue', '#000080'),
            ('GRY', 'Gray', '#808080'),
        ]
        
        for code, name, hex_code in colors:
            Color.objects.get_or_create(
                color_code=code,
                defaults={
                    'color_name': name,
                    'hex_code': hex_code
                }
            )
        
        self.stdout.write(f'  ✓ Created {len(colors)} colors')

    def seed_sizes(self):
        """Create default sizes."""
        self.stdout.write('Creating sizes...')
        
        sizes = [
            ('XS', 'Extra Small', 1),
            ('S', 'Small', 2),
            ('M', 'Medium', 3),
            ('L', 'Large', 4),
            ('XL', 'Extra Large', 5),
            ('XXL', 'Double Extra Large', 6),
        ]
        
        for code, desc, seq in sizes:
            Size.objects.get_or_create(
                size_code=code,
                defaults={
                    'description': desc,
                    'sequence': seq
                }
            )
        
        self.stdout.write(f'  ✓ Created {len(sizes)} sizes')

    def seed_statuses(self):
        """Create default statuses for various entities."""
        self.stdout.write('Creating statuses...')
        
        # This was already done in seed_initial_data, but we can add more here
        statuses = [
            # GRN Statuses
            ('GRN', 'DRAFT', 'Draft', 1, '#6c757d', True),
            ('GRN', 'SUBMITTED', 'Submitted', 2, '#0d6efd', True),
            ('GRN', 'QC_PENDING', 'QC Pending', 3, '#ffc107', True),
            ('GRN', 'ACCEPTED', 'Accepted', 4, '#28a745', True),
            ('GRN', 'REJECTED', 'Rejected', 5, '#dc3545', True),
            ('GRN', 'POSTED', 'Posted to Stock', 6, '#20c997', True),
        ]
        
        for entity, code, label, seq, color, is_sys in statuses:
            StatusMaster.objects.get_or_create(
                entity_type=entity,
                status_code=code,
                defaults={
                    'status_label': label,
                    'sequence': seq,
                    'color_code': color,
                    'is_system_status': is_sys,
                    'is_active': True
                }
            )
        
        self.stdout.write(f'  ✓ Created statuses')