"""
Setup Default Approval Workflows
=================================
Creates default approval workflows for various entity types.

Usage:
    python manage.py setup_approval_workflows
    python manage.py setup_approval_workflows --reset  # Delete and recreate
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from approvals.models import ApprovalWorkflow, ApprovalWorkflowStep
from users.models import Role
from core.models import Factory


class Command(BaseCommand):
    help = 'Setup default approval workflows'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing workflows and recreate',
        )

    def handle(self, *args, **options):
        reset = options.get('reset', False)
        
        if reset:
            self.stdout.write('Deleting existing approval workflows...')
            ApprovalWorkflow.objects.all().delete()
        
        self.stdout.write('Setting up approval workflows...\n')
        
        with transaction.atomic():
            self.create_pr_workflows()
            self.create_po_workflows()
            self.create_grn_workflows()
            self.create_adjustment_workflows()
            self.create_transfer_workflows()
        
        self.stdout.write(self.style.SUCCESS('\n✓ Approval workflows setup completed!'))

    def create_pr_workflows(self):
        """Create Purchase Request approval workflows."""
        self.stdout.write('Creating PR workflows...')
        
        # Get roles
        try:
            dept_head = Role.objects.get(role_name='Department Head')
            procurement = Role.objects.get(role_name='Procurement Officer')
            manager = Role.objects.get(role_name='Factory Manager')
        except Role.DoesNotExist:
            self.stdout.write(self.style.ERROR('  ✗ Required roles not found. Run seed_initial_data first.'))
            return
        
        # Low Value PR (< 50,000 BDT)
        workflow1, created = ApprovalWorkflow.objects.get_or_create(
            workflow_name='Low Value PR Approval',
            defaults={
                'entity_type': 'PR',
                'description': 'For PRs below 50,000 BDT',
                'max_value': 50000,
                'is_active': True,
                'is_default': False
            }
        )
        if created:
            ApprovalWorkflowStep.objects.create(
                workflow=workflow1,
                step_sequence=1,
                step_name='Department Head Approval',
                approver_role=dept_head,
                is_mandatory=True,
                timeout_hours=24
            )
            self.stdout.write('  ✓ Created: Low Value PR Approval')
        
        # Medium Value PR (50,000 - 500,000 BDT)
        workflow2, created = ApprovalWorkflow.objects.get_or_create(
            workflow_name='Medium Value PR Approval',
            defaults={
                'entity_type': 'PR',
                'description': 'For PRs between 50,000 and 500,000 BDT',
                'min_value': 50000,
                'max_value': 500000,
                'is_active': True,
                'is_default': True
            }
        )
        if created:
            ApprovalWorkflowStep.objects.create(
                workflow=workflow2,
                step_sequence=1,
                step_name='Department Head Approval',
                approver_role=dept_head,
                is_mandatory=True,
                timeout_hours=24
            )
            ApprovalWorkflowStep.objects.create(
                workflow=workflow2,
                step_sequence=2,
                step_name='Procurement Review',
                approver_role=procurement,
                is_mandatory=True,
                timeout_hours=48
            )
            self.stdout.write('  ✓ Created: Medium Value PR Approval')
        
        # High Value PR (> 500,000 BDT)
        workflow3, created = ApprovalWorkflow.objects.get_or_create(
            workflow_name='High Value PR Approval',
            defaults={
                'entity_type': 'PR',
                'description': 'For PRs above 500,000 BDT',
                'min_value': 500000,
                'is_active': True,
                'is_default': False
            }
        )
        if created:
            ApprovalWorkflowStep.objects.create(
                workflow=workflow3,
                step_sequence=1,
                step_name='Department Head Approval',
                approver_role=dept_head,
                is_mandatory=True,
                timeout_hours=24
            )
            ApprovalWorkflowStep.objects.create(
                workflow=workflow3,
                step_sequence=2,
                step_name='Procurement Review',
                approver_role=procurement,
                is_mandatory=True,
                timeout_hours=48
            )
            ApprovalWorkflowStep.objects.create(
                workflow=workflow3,
                step_sequence=3,
                step_name='Management Approval',
                approver_role=manager,
                is_mandatory=True,
                timeout_hours=72,
                escalation_role=manager
            )
            self.stdout.write('  ✓ Created: High Value PR Approval')

    def create_po_workflows(self):
        """Create Purchase Order approval workflows."""
        self.stdout.write('Creating PO workflows...')
        
        try:
            procurement = Role.objects.get(role_name='Procurement Officer')
            manager = Role.objects.get(role_name='Factory Manager')
        except Role.DoesNotExist:
            return
        
        # Standard PO (< 100,000 BDT)
        workflow1, created = ApprovalWorkflow.objects.get_or_create(
            workflow_name='Standard PO Approval',
            defaults={
                'entity_type': 'PO',
                'description': 'For POs below 100,000 BDT',
                'max_value': 100000,
                'is_active': True,
                'is_default': True
            }
        )
        if created:
            ApprovalWorkflowStep.objects.create(
                workflow=workflow1,
                step_sequence=1,
                step_name='Procurement Manager Approval',
                approver_role=procurement,
                is_mandatory=True,
                timeout_hours=48
            )
            self.stdout.write('  ✓ Created: Standard PO Approval')
        
        # High Value PO (> 100,000 BDT)
        workflow2, created = ApprovalWorkflow.objects.get_or_create(
            workflow_name='High Value PO Approval',
            defaults={
                'entity_type': 'PO',
                'description': 'For POs above 100,000 BDT',
                'min_value': 100000,
                'is_active': True,
                'is_default': False
            }
        )
        if created:
            ApprovalWorkflowStep.objects.create(
                workflow=workflow2,
                step_sequence=1,
                step_name='Procurement Manager Approval',
                approver_role=procurement,
                is_mandatory=True,
                timeout_hours=48
            )
            ApprovalWorkflowStep.objects.create(
                workflow=workflow2,
                step_sequence=2,
                step_name='Factory Manager Approval',
                approver_role=manager,
                is_mandatory=True,
                timeout_hours=72
            )
            self.stdout.write('  ✓ Created: High Value PO Approval')

    def create_grn_workflows(self):
        """Create GRN approval workflows."""
        self.stdout.write('Creating GRN workflows...')
        
        try:
            qc = Role.objects.get(role_name='QC Inspector')
            storekeeper = Role.objects.get(role_name='Storekeeper')
        except Role.DoesNotExist:
            return
        
        workflow, created = ApprovalWorkflow.objects.get_or_create(
            workflow_name='GRN QC & Posting',
            defaults={
                'entity_type': 'GRN',
                'description': 'Quality check and stock posting for GRN',
                'is_active': True,
                'is_default': True
            }
        )
        if created:
            ApprovalWorkflowStep.objects.create(
                workflow=workflow,
                step_sequence=1,
                step_name='QC Inspection',
                approver_role=qc,
                is_mandatory=True,
                timeout_hours=24
            )
            ApprovalWorkflowStep.objects.create(
                workflow=workflow,
                step_sequence=2,
                step_name='Post to Stock',
                approver_role=storekeeper,
                is_mandatory=True,
                timeout_hours=48
            )
            self.stdout.write('  ✓ Created: GRN QC & Posting')

    def create_adjustment_workflows(self):
        """Create Inventory Adjustment workflows."""
        self.stdout.write('Creating Adjustment workflows...')
        
        try:
            inv_manager = Role.objects.get(role_name='Inventory Manager')
            manager = Role.objects.get(role_name='Factory Manager')
        except Role.DoesNotExist:
            return
        
        workflow, created = ApprovalWorkflow.objects.get_or_create(
            workflow_name='Inventory Adjustment Approval',
            defaults={
                'entity_type': 'ADJUSTMENT',
                'description': 'Approval for inventory adjustments',
                'is_active': True,
                'is_default': True
            }
        )
        if created:
            ApprovalWorkflowStep.objects.create(
                workflow=workflow,
                step_sequence=1,
                step_name='Inventory Manager Review',
                approver_role=inv_manager,
                is_mandatory=True,
                timeout_hours=24
            )
            ApprovalWorkflowStep.objects.create(
                workflow=workflow,
                step_sequence=2,
                step_name='Management Approval',
                approver_role=manager,
                is_mandatory=True,
                timeout_hours=48
            )
            self.stdout.write('  ✓ Created: Inventory Adjustment Approval')

    def create_transfer_workflows(self):
        """Create Stock Transfer workflows."""
        self.stdout.write('Creating Transfer workflows...')
        
        try:
            storekeeper = Role.objects.get(role_name='Storekeeper')
            inv_manager = Role.objects.get(role_name='Inventory Manager')
        except Role.DoesNotExist:
            return
        
        workflow, created = ApprovalWorkflow.objects.get_or_create(
            workflow_name='Stock Transfer Approval',
            defaults={
                'entity_type': 'TRANSFER',
                'description': 'Approval for stock transfers',
                'is_active': True,
                'is_default': True
            }
        )
        if created:
            ApprovalWorkflowStep.objects.create(
                workflow=workflow,
                step_sequence=1,
                step_name='Storekeeper Authorization',
                approver_role=storekeeper,
                is_mandatory=True,
                timeout_hours=12
            )
            ApprovalWorkflowStep.objects.create(
                workflow=workflow,
                step_sequence=2,
                step_name='Inventory Manager Approval',
                approver_role=inv_manager,
                is_mandatory=True,
                timeout_hours=24
            )
            self.stdout.write('  ✓ Created: Stock Transfer Approval')