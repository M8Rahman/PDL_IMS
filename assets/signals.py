"""
Asset Management Signals
=========================
Automatic asset creation and updates based on other model changes.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from procurement.models import GRNLine, GoodsReceivedNote
from .models import Asset, create_asset_from_grn_line


@receiver(post_save, sender=GRNLine)
def auto_create_asset_from_grn(sender, instance, created, **kwargs):
    """
    Automatically create Asset records for serialized items when GRN is posted.
    
    Triggers when:
    - GRN line is for a serialized item
    - GRN line has a serial number
    - GRN status is ACCEPTED or POSTED
    """
    # Only create asset if GRN line is for serialized item
    if not instance.item.is_serialized:
        return
    
    # Only create if serial number exists
    if not instance.serial_no:
        return
    
    # Only create if GRN is accepted or posted
    if instance.grn.status not in ['ACCEPTED', 'POSTED']:
        return
    
    # Check if asset already exists for this serial number
    if Asset.objects.filter(serial_no=instance.serial_no).exists():
        return
    
    # Create the asset
    asset = create_asset_from_grn_line(
        grn_line=instance,
        location=instance.location
    )
    
    if asset:
        print(f"✓ Auto-created asset: {asset.asset_tag} for {instance.item.sku}")


@receiver(post_save, sender=GoodsReceivedNote)
def update_assets_on_grn_status_change(sender, instance, created, **kwargs):
    """
    Update asset status when GRN status changes.
    
    If GRN is rejected, we might want to mark assets as quarantined.
    """
    if instance.status == 'REJECTED':
        # Mark all assets from this GRN as requiring review
        assets = Asset.objects.filter(grn=instance, current_status='IN_STOCK')
        # Don't auto-change status, just log for manual review
        if assets.exists():
            print(f"⚠ Warning: {assets.count()} asset(s) from rejected GRN {instance.grn_number} need review")


@receiver(pre_save, sender=Asset)
def validate_asset_assignment(sender, instance, **kwargs):
    """
    Validate asset assignment before saving.
    
    Ensures:
    - If assigned to user, must have department
    - Status matches assignment state
    """
    if instance.assigned_to_user and not instance.assigned_to_department:
        # Auto-set department from user
        if instance.assigned_to_user.department:
            instance.assigned_to_department = instance.assigned_to_user.department
    
    # Ensure status consistency
    if instance.assigned_to_user and instance.current_status == 'IN_STOCK':
        instance.current_status = 'ASSIGNED'
    elif not instance.assigned_to_user and instance.current_status == 'ASSIGNED':
        instance.current_status = 'IN_STOCK'