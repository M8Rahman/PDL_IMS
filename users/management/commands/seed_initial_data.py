"""
Seed Initial Data Command
=========================
Populates the database with initial store types, roles, and permissions.

Usage:
    python manage.py seed_initial_data
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import StoreType, Role, Permission, RolePermission


class Command(BaseCommand):
    help = 'Seeds initial data (store types, roles, permissions)'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting data seeding...\n')
        
        with transaction.atomic():
            self.seed_store_types()
            self.seed_roles()
            self.seed_permissions()
            self.assign_permissions_to_roles()
        
        self.stdout.write(self.style.SUCCESS('\n✓ Data seeding completed successfully!'))

    def seed_store_types(self):
        """Create default store types."""
        self.stdout.write('Creating store types...')
        
        store_types = [
            {'code': 'YARN_STORE', 'name': 'Yarn Store', 'desc': 'Yarn inventory management', 'icon': 'yarn'},
            {'code': 'GRAY_FABRIC_STORE', 'name': 'Gray Fabric Store', 'desc': 'Gray fabric storage and tracking', 'icon': 'fabric'},
            {'code': 'FINISH_FABRIC_STORE', 'name': 'Finish Fabric Store', 'desc': 'Finished fabric after dyeing', 'icon': 'fabric-finished'},
            {'code': 'ACCESSORIES_STORE', 'name': 'Accessories Store', 'desc': 'Trims, buttons, zippers, etc.', 'icon': 'accessories'},
            {'code': 'GENERAL_STORE', 'name': 'General Store', 'desc': 'General consumables and supplies', 'icon': 'box'},
            {'code': 'SPARES_STORE', 'name': 'Spare Parts Store', 'desc': 'Machine parts and spares', 'icon': 'cog'},
            {'code': 'IT_STORE', 'name': 'IT Store', 'desc': 'IT equipment and peripherals', 'icon': 'computer'},
            {'code': 'MAINTENANCE_STORE', 'name': 'Maintenance Store', 'desc': 'Electrical, plumbing supplies', 'icon': 'tools'},
        ]
        
        for st in store_types:
            StoreType.objects.get_or_create(
                store_code=st['code'],
                defaults={
                    'store_name': st['name'],
                    'description': st['desc'],
                    'icon': st['icon'],
                    'is_active': True
                }
            )
        
        self.stdout.write(f'  ✓ Created {len(store_types)} store types')

    def seed_roles(self):
        """Create default roles."""
        self.stdout.write('Creating roles...')
        
        roles = [
            {'name': 'SuperAdmin', 'desc': 'Full system access', 'system': True},
            {'name': 'Factory Manager', 'desc': 'Factory-level management access', 'system': True},
            {'name': 'Inventory Manager', 'desc': 'Manages all inventory operations', 'system': True},
            {'name': 'Storekeeper', 'desc': 'Store operations (receive, issue)', 'system': False},
            {'name': 'Procurement Officer', 'desc': 'Purchase requisitions and orders', 'system': False},
            {'name': 'QC Inspector', 'desc': 'Quality control and inspections', 'system': False},
            {'name': 'IT Admin', 'desc': 'IT store and asset management', 'system': False},
            {'name': 'Department Head', 'desc': 'Approve requisitions for department', 'system': False},
            {'name': 'Requester', 'desc': 'Create requisitions only', 'system': False},
            {'name': 'Auditor', 'desc': 'Read-only access to all data', 'system': True},
        ]
        
        for r in roles:
            Role.objects.get_or_create(
                role_name=r['name'],
                defaults={
                    'description': r['desc'],
                    'is_system_role': r['system']
                }
            )
        
        self.stdout.write(f'  ✓ Created {len(roles)} roles')

    def seed_permissions(self):
        """Create default permissions."""
        self.stdout.write('Creating permissions...')
        
        permissions = [
            # Yarn Store
            ('yarn_store.view', 'INVENTORY', 'YARN_STORE', 'View yarn store data'),
            ('yarn_store.create', 'INVENTORY', 'YARN_STORE', 'Create yarn records'),
            ('yarn_store.update', 'INVENTORY', 'YARN_STORE', 'Update yarn records'),
            ('yarn_store.delete', 'INVENTORY', 'YARN_STORE', 'Delete yarn records'),
            ('yarn_store.issue', 'INVENTORY', 'YARN_STORE', 'Issue yarn for knitting'),
            ('yarn_store.approve', 'INVENTORY', 'YARN_STORE', 'Approve yarn transactions'),
            
            # IT Store
            ('it_store.view', 'INVENTORY', 'IT_STORE', 'View IT store data'),
            ('it_store.create', 'INVENTORY', 'IT_STORE', 'Create IT asset records'),
            ('it_store.update', 'INVENTORY', 'IT_STORE', 'Update IT asset records'),
            ('it_store.assign', 'INVENTORY', 'IT_STORE', 'Assign IT assets to users'),
            ('it_store.approve', 'INVENTORY', 'IT_STORE', 'Approve IT asset assignments'),
            
            # General Store
            ('general_store.view', 'INVENTORY', 'GENERAL_STORE', 'View general store data'),
            ('general_store.create', 'INVENTORY', 'GENERAL_STORE', 'Create general items'),
            ('general_store.issue', 'INVENTORY', 'GENERAL_STORE', 'Issue general items'),
            ('general_store.approve', 'INVENTORY', 'GENERAL_STORE', 'Approve general store requisitions'),
            
            # Procurement
            ('procurement.view_pr', 'PROCUREMENT', None, 'View purchase requisitions'),
            ('procurement.create_pr', 'PROCUREMENT', None, 'Create purchase requisitions'),
            ('procurement.approve_pr', 'PROCUREMENT', None, 'Approve purchase requisitions'),
            ('procurement.create_po', 'PROCUREMENT', None, 'Create purchase orders'),
            ('procurement.approve_po', 'PROCUREMENT', None, 'Approve purchase orders'),
            
            # GRN & QC
            ('grn.create', 'INVENTORY', None, 'Create goods received notes'),
            ('grn.qc_inspect', 'QUALITY', None, 'Perform QC inspection'),
            ('grn.approve', 'INVENTORY', None, 'Approve GRN'),
            
            # Reports
            ('reports.view_stock', 'REPORTS', None, 'View stock reports'),
            ('reports.view_valuation', 'REPORTS', None, 'View stock valuation reports'),
            ('reports.export', 'REPORTS', None, 'Export reports'),
        ]
        
        for perm in permissions:
            Permission.objects.get_or_create(
                permission_key=perm[0],
                defaults={
                    'module': perm[1],
                    'module_code': perm[2],
                    'description': perm[3]
                }
            )
        
        self.stdout.write(f'  ✓ Created {len(permissions)} permissions')

    def assign_permissions_to_roles(self):
        """Assign permissions to roles."""
        self.stdout.write('Assigning permissions to roles...')
        
        # Get roles
        superadmin = Role.objects.get(role_name='SuperAdmin')
        inv_manager = Role.objects.get(role_name='Inventory Manager')
        storekeeper = Role.objects.get(role_name='Storekeeper')
        
        # SuperAdmin gets all permissions
        all_permissions = Permission.objects.all()
        for perm in all_permissions:
            RolePermission.objects.get_or_create(role=superadmin, permission=perm)
        
        # Inventory Manager gets all inventory permissions
        inv_permissions = Permission.objects.filter(module='INVENTORY')
        for perm in inv_permissions:
            RolePermission.objects.get_or_create(role=inv_manager, permission=perm)
        
        # Storekeeper gets view and basic operations
        storekeeper_perms = Permission.objects.filter(
            permission_key__in=[
                'yarn_store.view', 'yarn_store.create', 'yarn_store.issue',
                'it_store.view', 'general_store.view', 'general_store.issue',
                'grn.create'
            ]
        )
        for perm in storekeeper_perms:
            RolePermission.objects.get_or_create(role=storekeeper, permission=perm)
        
        self.stdout.write('  ✓ Permissions assigned to roles')