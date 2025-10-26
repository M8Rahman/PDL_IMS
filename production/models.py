"""
Production Models
=================
This module contains:
1. Work Orders & Breakdowns
2. Yarn Store Operations (Allocations, Issues, Gate Passes)
3. Gray Fabric Operations (Receipts, Inspections, Issues, Knitting Bills)
4. Finish Fabric Operations (Receipts, Issues, Leftover, Dyeing Bills)
5. Internal Requisitions & Issues
6. Stock Transfers & Returns
7. Inventory Adjustments & Stocktaking
"""

import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel, Factory, Department, Location
from users.models import User
from inventory.models import (
    Item, UnitOfMeasurement, Supplier, Buyer, Style, Color, Size, Currency
)
from procurement.models import StockBatch


# ============================================================================
# WORK ORDER (PRODUCTION ORDER)
# ============================================================================

class WorkOrder(BaseModel):
    """
    Work Order - Production order for garments.
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    wo_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Work order number"
    )
    buyer = models.ForeignKey(
        Buyer,
        on_delete=models.PROTECT,
        related_name='work_orders',
        help_text="Buyer"
    )
    style = models.ForeignKey(
        Style,
        on_delete=models.PROTECT,
        related_name='work_orders',
        help_text="Style"
    )
    po_number = models.CharField(
        max_length=100,
        help_text="Buyer's PO number"
    )
    factory = models.ForeignKey(
        Factory,
        on_delete=models.PROTECT,
        related_name='work_orders',
        help_text="Factory"
    )
    order_date = models.DateField(
        help_text="Order date"
    )
    delivery_date = models.DateField(
        help_text="Delivery date"
    )
    order_qty = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Total order quantity"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text="Work order status"
    )
    remarks = models.TextField(
        blank=True,
        null=True,
        help_text="Remarks"
    )
    
    class Meta:
        db_table = 'work_orders'
        verbose_name = 'Work Order'
        verbose_name_plural = 'Work Orders'
        ordering = ['-order_date', '-created_at']
        indexes = [
            models.Index(fields=['wo_number']),
            models.Index(fields=['buyer', 'status']),
            models.Index(fields=['factory', 'status']),
        ]
    
    def __str__(self):
        return f"{self.wo_number} - {self.buyer.name} ({self.status})"
    
    def save(self, *args, **kwargs):
        """Auto-generate WO number."""
        if not self.wo_number:
            from django.utils import timezone
            year = timezone.now().year
            last_wo = WorkOrder.objects.filter(
                wo_number__startswith=f'WO-{year}'
            ).order_by('-wo_number').first()
            
            if last_wo:
                last_num = int(last_wo.wo_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.wo_number = f'WO-{year}-{new_num:04d}'
        
        super().save(*args, **kwargs)


class WorkOrderSizeBreakdown(models.Model):
    """Size breakdown for work orders."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name='size_breakdowns',
        help_text="Work order"
    )
    size = models.ForeignKey(
        Size,
        on_delete=models.PROTECT,
        help_text="Size"
    )
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Quantity for this size"
    )
    
    class Meta:
        db_table = 'wo_size_breakdowns'
        unique_together = ['work_order', 'size']
        verbose_name = 'WO Size Breakdown'
        verbose_name_plural = 'WO Size Breakdowns'
    
    def __str__(self):
        return f"{self.work_order.wo_number} - {self.size.size_code}: {self.quantity}"


class WorkOrderColorBreakdown(models.Model):
    """Color breakdown for work orders."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name='color_breakdowns',
        help_text="Work order"
    )
    color = models.ForeignKey(
        Color,
        on_delete=models.PROTECT,
        help_text="Color"
    )
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Quantity for this color"
    )
    
    class Meta:
        db_table = 'wo_color_breakdowns'
        unique_together = ['work_order', 'color']
        verbose_name = 'WO Color Breakdown'
        verbose_name_plural = 'WO Color Breakdowns'
    
    def __str__(self):
        return f"{self.work_order.wo_number} - {self.color.color_name}: {self.quantity}"


class WorkOrderYarnRequirement(models.Model):
    """Yarn requirements for work orders."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name='yarn_requirements',
        help_text="Work order"
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name='wo_yarn_requirements',
        help_text="Yarn item"
    )
    required_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(0.001)],
        help_text="Required quantity"
    )
    uom = models.ForeignKey(
        UnitOfMeasurement,
        on_delete=models.PROTECT,
        help_text="Unit of measurement"
    )
    allocated_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Allocated quantity"
    )
    issued_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Issued quantity"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'wo_yarn_requirements'
        verbose_name = 'WO Yarn Requirement'
        verbose_name_plural = 'WO Yarn Requirements'
    
    def __str__(self):
        return f"{self.work_order.wo_number} - {self.item.sku}: {self.required_qty} {self.uom.uom_code}"


class WorkOrderAccessoryRequirement(models.Model):
    """Accessory requirements for work orders."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name='accessory_requirements',
        help_text="Work order"
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name='wo_accessory_requirements',
        help_text="Accessory item"
    )
    color = models.ForeignKey(
        Color,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Color"
    )
    size = models.ForeignKey(
        Size,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Size"
    )
    required_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(0.001)],
        help_text="Required quantity"
    )
    uom = models.ForeignKey(
        UnitOfMeasurement,
        on_delete=models.PROTECT,
        help_text="Unit of measurement"
    )
    allocated_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Allocated quantity"
    )
    issued_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Issued quantity"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'wo_accessories_requirements'
        verbose_name = 'WO Accessory Requirement'
        verbose_name_plural = 'WO Accessory Requirements'
    
    def __str__(self):
        return f"{self.work_order.wo_number} - {self.item.sku}: {self.required_qty}"


# ============================================================================
# INTERNAL REQUISITION & ISSUE
# ============================================================================

class InternalRequisition(BaseModel):
    """
    Internal requisition for items from stock.
    """
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('APPROVED', 'Approved'),
        ('PARTIALLY_ISSUED', 'Partially Issued'),
        ('FULLY_ISSUED', 'Fully Issued'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    requisition_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Requisition number"
    )
    requester = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='internal_requisitions',
        help_text="Requester"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='internal_requisitions',
        help_text="Department"
    )
    factory = models.ForeignKey(
        Factory,
        on_delete=models.PROTECT,
        related_name='internal_requisitions',
        help_text="Factory"
    )
    requisition_date = models.DateField(
        help_text="Requisition date"
    )
    required_by_date = models.DateField(
        null=True,
        blank=True,
        help_text="Required by date"
    )
    purpose = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Purpose of requisition"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        help_text="Status"
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_internal_requisitions',
        help_text="Approver"
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Approval timestamp"
    )
    rejection_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Rejection reason"
    )
    remarks = models.TextField(
        blank=True,
        null=True,
        help_text="Remarks"
    )
    
    class Meta:
        db_table = 'internal_requisitions'
        verbose_name = 'Internal Requisition'
        verbose_name_plural = 'Internal Requisitions'
        ordering = ['-requisition_date', '-created_at']
        indexes = [
            models.Index(fields=['requisition_number']),
            models.Index(fields=['department', 'status']),
        ]
    
    def __str__(self):
        return f"{self.requisition_number} - {self.department.name} ({self.status})"
    
    def save(self, *args, **kwargs):
        """Auto-generate requisition number."""
        if not self.requisition_number:
            from django.utils import timezone
            year = timezone.now().year
            last_req = InternalRequisition.objects.filter(
                requisition_number__startswith=f'REQ-{year}'
            ).order_by('-requisition_number').first()
            
            if last_req:
                last_num = int(last_req.requisition_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.requisition_number = f'REQ-{year}-{new_num:04d}'
        
        super().save(*args, **kwargs)


class InternalRequisitionLine(models.Model):
    """Line items for internal requisitions."""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('PARTIALLY_ISSUED', 'Partially Issued'),
        ('FULLY_ISSUED', 'Fully Issued'),
        ('REJECTED', 'Rejected'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requisition = models.ForeignKey(
        InternalRequisition,
        on_delete=models.CASCADE,
        related_name='lines',
        help_text="Internal requisition"
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name='internal_requisition_lines',
        help_text="Item"
    )
    requested_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(0.001)],
        help_text="Requested quantity"
    )
    issued_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Issued quantity"
    )
    pending_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(0)],
        help_text="Pending quantity"
    )
    uom = models.ForeignKey(
        UnitOfMeasurement,
        on_delete=models.PROTECT,
        help_text="Unit of measurement"
    )
    purpose = models.TextField(
        blank=True,
        null=True,
        help_text="Purpose"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text="Line status"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'internal_requisition_lines'
        verbose_name = 'Internal Requisition Line'
        verbose_name_plural = 'Internal Requisition Lines'
    
    def __str__(self):
        return f"{self.requisition.requisition_number} - {self.item.sku}"
    
    def save(self, *args, **kwargs):
        """Calculate pending quantity."""
        self.pending_qty = self.requested_qty - self.issued_qty
        
        if self.issued_qty == 0:
            self.status = 'PENDING'
        elif self.issued_qty < self.requested_qty:
            self.status = 'PARTIALLY_ISSUED'
        else:
            self.status = 'FULLY_ISSUED'
        
        super().save(*args, **kwargs)


class StockIssue(BaseModel):
    """
    Stock issue - Issue items to departments.
    """
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('APPROVED', 'Approved'),
        ('ISSUED', 'Issued'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    issue_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Issue number"
    )
    requisition = models.ForeignKey(
        InternalRequisition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_issues',
        help_text="Source requisition"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='stock_issues',
        help_text="Department"
    )
    factory = models.ForeignKey(
        Factory,
        on_delete=models.PROTECT,
        related_name='stock_issues',
        help_text="Factory"
    )
    issue_date = models.DateField(
        help_text="Issue date"
    )
    issued_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='stock_issues_issued',
        help_text="Issued by"
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_issues_approved',
        help_text="Approved by"
    )
    received_by_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Person who received items"
    )
    received_by_signature = models.TextField(
        blank=True,
        null=True,
        help_text="Digital signature"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        help_text="Status"
    )
    remarks = models.TextField(
        blank=True,
        null=True,
        help_text="Remarks"
    )
    
    class Meta:
        db_table = 'stock_issues'
        verbose_name = 'Stock Issue'
        verbose_name_plural = 'Stock Issues'
        ordering = ['-issue_date', '-created_at']
        indexes = [
            models.Index(fields=['issue_number']),
            models.Index(fields=['department', 'status']),
        ]
    
    def __str__(self):
        return f"{self.issue_number} - {self.department.name} ({self.status})"
    
    def save(self, *args, **kwargs):
        """Auto-generate issue number."""
        if not self.issue_number:
            from django.utils import timezone
            year = timezone.now().year
            last_issue = StockIssue.objects.filter(
                issue_number__startswith=f'ISS-{year}'
            ).order_by('-issue_number').first()
            
            if last_issue:
                last_num = int(last_issue.issue_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.issue_number = f'ISS-{year}-{new_num:04d}'
        
        super().save(*args, **kwargs)


class StockIssueLine(models.Model):
    """Line items for stock issues."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    issue = models.ForeignKey(
        StockIssue,
        on_delete=models.CASCADE,
        related_name='lines',
        help_text="Stock issue"
    )
    requisition_line = models.ForeignKey(
        InternalRequisitionLine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='issue_lines',
        help_text="Source requisition line"
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name='issue_lines',
        help_text="Item"
    )
    batch = models.ForeignKey(
        StockBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Stock batch"
    )
    serial_no = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Serial number"
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        help_text="Source location"
    )
    issued_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(0.001)],
        help_text="Issued quantity"
    )
    uom = models.ForeignKey(
        UnitOfMeasurement,
        on_delete=models.PROTECT,
        help_text="Unit of measurement"
    )
    unit_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Unit cost"
    )
    total_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total cost"
    )
    remarks = models.TextField(
        blank=True,
        null=True,
        help_text="Remarks"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'stock_issue_lines'
        verbose_name = 'Stock Issue Line'
        verbose_name_plural = 'Stock Issue Lines'
    
    def __str__(self):
        return f"{self.issue.issue_number} - {self.item.sku}"
    
    def save(self, *args, **kwargs):
        """Calculate total cost."""
        if self.unit_cost and self.issued_qty:
            self.total_cost = self.unit_cost * self.issued_qty
        super().save(*args, **kwargs)


# ============================================================================
# STOCK TRANSFER
# ============================================================================

class StockTransfer(BaseModel):
    """
    Stock transfer between locations.
    """
    
    TRANSFER_TYPES = [
        ('INTERNAL', 'Internal (Same Factory)'),
        ('INTER_FACTORY', 'Inter-Factory'),
        ('INTER_LOCATION', 'Inter-Location'),
    ]
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('APPROVED', 'Approved'),
        ('IN_TRANSIT', 'In Transit'),
        ('RECEIVED', 'Received'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    transfer_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Transfer number"
    )
    from_location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name='transfers_from',
        help_text="From location"
    )
    to_location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name='transfers_to',
        help_text="To location"
    )
    from_factory = models.ForeignKey(
        Factory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='transfers_from',
        help_text="From factory"
    )
    to_factory = models.ForeignKey(
        Factory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='transfers_to',
        help_text="To factory"
    )
    transfer_date = models.DateField(
        help_text="Transfer date"
    )
    transfer_type = models.CharField(
        max_length=20,
        choices=TRANSFER_TYPES,
        default='INTERNAL',
        help_text="Transfer type"
    )
    requested_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='transfers_requested',
        help_text="Requested by"
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transfers_approved',
        help_text="Approved by"
    )
    sent_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transfers_sent',
        help_text="Sent by"
    )
    received_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transfers_received',
        help_text="Received by"
    )
    received_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Receipt timestamp"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        help_text="Status"
    )
    vehicle_no = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Vehicle number"
    )
    driver_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Driver name"
    )
    remarks = models.TextField(
        blank=True,
        null=True,
        help_text="Remarks"
    )
    
    class Meta:
        db_table = 'stock_transfers'
        verbose_name = 'Stock Transfer'
        verbose_name_plural = 'Stock Transfers'
        ordering = ['-transfer_date', '-created_at']
        indexes = [
            models.Index(fields=['transfer_number']),
            models.Index(fields=['from_location', 'to_location']),
        ]
    
    def __str__(self):
        return f"{self.transfer_number} - {self.from_location.location_code} → {self.to_location.location_code}"
    
    def save(self, *args, **kwargs):
        """Auto-generate transfer number."""
        if not self.transfer_number:
            from django.utils import timezone
            year = timezone.now().year
            last_trans = StockTransfer.objects.filter(
                transfer_number__startswith=f'TRN-{year}'
            ).order_by('-transfer_number').first()
            
            if last_trans:
                last_num = int(last_trans.transfer_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.transfer_number = f'TRN-{year}-{new_num:04d}'
        
        super().save(*args, **kwargs)


class StockTransferLine(models.Model):
    """Line items for stock transfers."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transfer = models.ForeignKey(
        StockTransfer,
        on_delete=models.CASCADE,
        related_name='lines',
        help_text="Stock transfer"
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name='transfer_lines',
        help_text="Item"
    )
    batch = models.ForeignKey(
        StockBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Stock batch"
    )
    serial_no = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Serial number"
    )
    transferred_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(0.001)],
        help_text="Transferred quantity"
    )
    received_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Received quantity"
    )
    uom = models.ForeignKey(
        UnitOfMeasurement,
        on_delete=models.PROTECT,
        help_text="Unit of measurement"
    )
    remarks = models.TextField(
        blank=True,
        null=True,
        help_text="Remarks"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'stock_transfer_lines'
        verbose_name = 'Stock Transfer Line'
        verbose_name_plural = 'Stock Transfer Lines'
    
    def __str__(self):
        return f"{self.transfer.transfer_number} - {self.item.sku}"


# ============================================================================
# INVENTORY ADJUSTMENT & STOCKTAKING
# ============================================================================

class InventoryAdjustment(BaseModel):
    """
    Inventory adjustments for stock corrections.
    """
    
    ADJUSTMENT_TYPES = [
        ('INCREASE', 'Increase'),
        ('DECREASE', 'Decrease'),
        ('DAMAGE', 'Damage'),
        ('THEFT', 'Theft/Loss'),
        ('EXPIRY', 'Expiry'),
        ('OBSOLETE', 'Obsolete'),
        ('CORRECTION', 'Correction'),
    ]
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('APPROVED', 'Approved'),
        ('POSTED', 'Posted to Stock'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    adjustment_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Adjustment number"
    )
    factory = models.ForeignKey(
        Factory,
        on_delete=models.PROTECT,
        related_name='inventory_adjustments',
        help_text="Factory"
    )
    adjustment_date = models.DateField(
        help_text="Adjustment date"
    )
    adjustment_type = models.CharField(
        max_length=20,
        choices=ADJUSTMENT_TYPES,
        help_text="Type of adjustment"
    )
    reason = models.TextField(
        help_text="Reason for adjustment"
    )
    performed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='adjustments_performed',
        help_text="Performed by"
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='adjustments_approved',
        help_text="Approved by"
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Approval timestamp"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        help_text="Status"
    )
    total_value_impact = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total value impact"
    )
    attachments = models.JSONField(
        blank=True,
        null=True,
        help_text="Attachments (file paths)"
    )
    remarks = models.TextField(
        blank=True,
        null=True,
        help_text="Remarks"
    )
    
    class Meta:
        db_table = 'inventory_adjustments'
        verbose_name = 'Inventory Adjustment'
        verbose_name_plural = 'Inventory Adjustments'
        ordering = ['-adjustment_date', '-created_at']
        indexes = [
            models.Index(fields=['adjustment_number']),
            models.Index(fields=['factory', 'status']),
        ]
    
    def __str__(self):
        return f"{self.adjustment_number} - {self.adjustment_type} ({self.status})"
    
    def save(self, *args, **kwargs):
        """Auto-generate adjustment number."""
        if not self.adjustment_number:
            from django.utils import timezone
            year = timezone.now().year
            last_adj = InventoryAdjustment.objects.filter(
                adjustment_number__startswith=f'ADJ-{year}'
            ).order_by('-adjustment_number').first()
            
            if last_adj:
                last_num = int(last_adj.adjustment_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.adjustment_number = f'ADJ-{year}-{new_num:04d}'
        
        super().save(*args, **kwargs)


class InventoryAdjustmentLine(models.Model):
    """Line items for inventory adjustments."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    adjustment = models.ForeignKey(
        InventoryAdjustment,
        on_delete=models.CASCADE,
        related_name='lines',
        help_text="Inventory adjustment"
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name='adjustment_lines',
        help_text="Item"
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        help_text="Location"
    )
    batch = models.ForeignKey(
        StockBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Stock batch"
    )
    serial_no = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Serial number"
    )
    system_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(0)],
        help_text="System quantity before adjustment"
    )
    adjusted_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(0)],
        help_text="Quantity after adjustment"
    )
    variance_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        help_text="Variance (adjusted - system)"
    )
    uom = models.ForeignKey(
        UnitOfMeasurement,
        on_delete=models.PROTECT,
        help_text="Unit of measurement"
    )
    unit_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Unit cost"
    )
    value_impact = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Value impact (variance × cost)"
    )
    reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'inventory_adjustment_lines'
        verbose_name = 'Inventory Adjustment Line'
        verbose_name_plural = 'Inventory Adjustment Lines'
    
    def __str__(self):
        return f"{self.adjustment.adjustment_number} - {self.item.sku}"
    
    def save(self, *args, **kwargs):
        """Calculate variance and value impact."""
        self.variance_qty = self.adjusted_qty - self.system_qty
        if self.unit_cost:
            self.value_impact = self.variance_qty * self.unit_cost
        super().save(*args, **kwargs)


class StocktakeSession(BaseModel):
    """
    Stocktaking session for physical inventory count.
    """
    
    STOCKTAKE_TYPES = [
        ('FULL', 'Full Stocktake'),
        ('CYCLE', 'Cycle Count'),
        ('SPOT', 'Spot Check'),
    ]
    
    STATUS_CHOICES = [
        ('PLANNED', 'Planned'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('APPROVED', 'Approved'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    stocktake_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Stocktake number"
    )
    factory = models.ForeignKey(
        Factory,
        on_delete=models.PROTECT,
        related_name='stocktake_sessions',
        help_text="Factory"
    )
    stocktake_type = models.CharField(
        max_length=20,
        choices=STOCKTAKE_TYPES,
        default='FULL',
        help_text="Type of stocktake"
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='stocktake_sessions',
        help_text="Location (NULL for full factory)"
    )
    start_date = models.DateField(
        help_text="Start date"
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="End date"
    )
    scheduled_date = models.DateField(
        null=True,
        blank=True,
        help_text="Scheduled date"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PLANNED',
        help_text="Status"
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stocktakes_approved',
        help_text="Approved by"
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Approval timestamp"
    )
    remarks = models.TextField(
        blank=True,
        null=True,
        help_text="Remarks"
    )
    
    class Meta:
        db_table = 'stocktake_sessions'
        verbose_name = 'Stocktake Session'
        verbose_name_plural = 'Stocktake Sessions'
        ordering = ['-start_date', '-created_at']
        indexes = [
            models.Index(fields=['stocktake_number']),
            models.Index(fields=['factory', 'status']),
        ]
    
    def __str__(self):
        return f"{self.stocktake_number} - {self.stocktake_type} ({self.status})"
    
    def save(self, *args, **kwargs):
        """Auto-generate stocktake number."""
        if not self.stocktake_number:
            from django.utils import timezone
            year = timezone.now().year
            last_st = StocktakeSession.objects.filter(
                stocktake_number__startswith=f'ST-{year}'
            ).order_by('-stocktake_number').first()
            
            if last_st:
                last_num = int(last_st.stocktake_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.stocktake_number = f'ST-{year}-{new_num:04d}'
        
        super().save(*args, **kwargs)


class StocktakeLine(models.Model):
    """Individual items counted during stocktake."""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COUNTED', 'Counted'),
        ('VERIFIED', 'Verified'),
        ('ADJUSTED', 'Adjusted'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stocktake = models.ForeignKey(
        StocktakeSession,
        on_delete=models.CASCADE,
        related_name='lines',
        help_text="Stocktake session"
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name='stocktake_lines',
        help_text="Item"
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        help_text="Location"
    )
    batch = models.ForeignKey(
        StockBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Stock batch"
    )
    serial_no = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Serial number"
    )
    system_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(0)],
        help_text="System quantity"
    )
    counted_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Counted quantity"
    )
    variance_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Variance (counted - system)"
    )
    uom = models.ForeignKey(
        UnitOfMeasurement,
        on_delete=models.PROTECT,
        help_text="Unit of measurement"
    )
    counted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stocktake_counted',
        help_text="Counted by"
    )
    counted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Count timestamp"
    )
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stocktake_verified',
        help_text="Verified by"
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Verification timestamp"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text="Line status"
    )
    remarks = models.TextField(
        blank=True,
        null=True,
        help_text="Remarks"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'stocktake_lines'
        verbose_name = 'Stocktake Line'
        verbose_name_plural = 'Stocktake Lines'
    
    def __str__(self):
        return f"{self.stocktake.stocktake_number} - {self.item.sku}"
    
    def save(self, *args, **kwargs):
        """Calculate variance."""
        if self.counted_qty is not None:
            self.variance_qty = self.counted_qty - self.system_qty
        super().save(*args, **kwargs)