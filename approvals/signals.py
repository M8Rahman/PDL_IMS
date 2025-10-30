# approvals/signals.py
"""
Approval Workflow Signals
==========================
Auto-trigger approval creation for various entities.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from procurement.models import PurchaseRequest, PurchaseOrder, GoodsReceivedNote
from production.models import InventoryAdjustment, StockTransfer
from assets.models import Asset, AssetMaintenanceRecord
from .models import create_approval


@receiver(post_save, sender=PurchaseRequest)
def auto_create_pr_approval(sender, instance, created, **kwargs):
    """
    Auto-create approval when PR is submitted.
    
    Triggers when PR status changes to SUBMITTED.
    """
    # Only create approval if status is SUBMITTED and no approval exists yet
    if instance.status == 'SUBMITTED':
        from .models import Approval
        
        # Check if approval already exists
        if Approval.objects.filter(
            entity_type='PR',
            entity_id=instance.id
        ).exists():
            return
        
        # Create approval
        try:
            approval = create_approval(
                entity_type='PR',
                entity_id=instance.id,
                entity_number=instance.pr_number,
                requested_by=instance.requester,
                value=instance.total_estimated_value,
                remarks=instance.justification
            )
            print(f"✓ Created approval for PR {instance.pr_number}")
        except Exception as e:
            print(f"✗ Failed to create approval for PR {instance.pr_number}: {e}")


@receiver(post_save, sender=PurchaseOrder)
def auto_create_po_approval(sender, instance, created, **kwargs):
    """
    Auto-create approval when PO is submitted.
    
    Triggers when PO status changes to SUBMITTED.
    """
    if instance.status == 'SUBMITTED':
        from .models import Approval
        
        # Check if approval already exists
        if Approval.objects.filter(
            entity_type='PO',
            entity_id=instance.id
        ).exists():
            return
        
        # Create approval
        try:
            approval = create_approval(
                entity_type='PO',
                entity_id=instance.id,
                entity_number=instance.po_number,
                requested_by=instance.created_by if instance.created_by else instance.pr.requester if instance.pr else None,
                value=instance.grand_total
            )
            print(f"✓ Created approval for PO {instance.po_number}")
        except Exception as e:
            print(f"✗ Failed to create approval for PO {instance.po_number}: {e}")


@receiver(post_save, sender=GoodsReceivedNote)
def auto_create_grn_approval(sender, instance, created, **kwargs):
    """
    Auto-create approval when GRN is submitted.
    
    Triggers when GRN status changes to SUBMITTED.
    """
    if instance.status == 'SUBMITTED':
        from .models import Approval
        
        # Check if approval already exists
        if Approval.objects.filter(
            entity_type='GRN',
            entity_id=instance.id
        ).exists():
            return
        
        # Create approval
        try:
            approval = create_approval(
                entity_type='GRN',
                entity_id=instance.id,
                entity_number=instance.grn_number,
                requested_by=instance.received_by,
                value=instance.total_value
            )
            print(f"✓ Created approval for GRN {instance.grn_number}")
        except Exception as e:
            print(f"✗ Failed to create approval for GRN {instance.grn_number}: {e}")


@receiver(post_save, sender=InventoryAdjustment)
def auto_create_adjustment_approval(sender, instance, created, **kwargs):
    """
    Auto-create approval when Adjustment is submitted.
    """
    if instance.status == 'SUBMITTED':
        from .models import Approval
        
        if Approval.objects.filter(
            entity_type='ADJUSTMENT',
            entity_id=instance.id
        ).exists():
            return
        
        try:
            approval = create_approval(
                entity_type='ADJUSTMENT',
                entity_id=instance.id,
                entity_number=instance.adjustment_number,
                requested_by=instance.performed_by,
                value=abs(instance.total_value_impact) if instance.total_value_impact else None,
                remarks=instance.reason
            )
            print(f"✓ Created approval for Adjustment {instance.adjustment_number}")
        except Exception as e:
            print(f"✗ Failed to create approval for Adjustment {instance.adjustment_number}: {e}")


@receiver(post_save, sender=StockTransfer)
def auto_create_transfer_approval(sender, instance, created, **kwargs):
    """
    Auto-create approval when Transfer is submitted.
    """
    if instance.status == 'SUBMITTED':
        from .models import Approval
        
        if Approval.objects.filter(
            entity_type='TRANSFER',
            entity_id=instance.id
        ).exists():
            return
        
        try:
            approval = create_approval(
                entity_type='TRANSFER',
                entity_id=instance.id,
                entity_number=instance.transfer_number,
                requested_by=instance.requested_by if instance.requested_by else instance.created_by,
                remarks=instance.remarks
            )
            print(f"✓ Created approval for Transfer {instance.transfer_number}")
        except Exception as e:
            print(f"✗ Failed to create approval for Transfer {instance.transfer_number}: {e}")