"""
Procurement Models
==================
This module contains:
1. Purchase Requests (PR) & Lines
2. Purchase Orders (PO) & Lines
3. Goods Received Notes (GRN) & Lines
4. QC Inspections
5. Invoices
6. Stock Batches
7. Stock Movements
"""

import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, Q

from core.models import BaseModel, Factory, Department, Location
from users.models import User
from inventory.models import (
    Item, UnitOfMeasurement, Supplier, Currency
)


# ============================================================================
# PURCHASE REQUEST (PR)
# ============================================================================

class PurchaseRequest(BaseModel):
    """
    Purchase Request - Request to purchase items.
    
    Can be EXTERNAL (buy from supplier) or INTERNAL (issue from stock).
    """
    
    REQUEST_TYPES = [
        ('EXTERNAL', 'External Purchase'),
        ('INTERNAL', 'Internal Issue'),
    ]
    
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('NORMAL', 'Normal'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('CONVERTED_TO_PO', 'Converted to PO'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    pr_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique PR number"
    )
    requester = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='purchase_requests',
        help_text="User who created this PR"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='purchase_requests',
        help_text="Requesting department"
    )
    factory = models.ForeignKey(
        Factory,
        on_delete=models.PROTECT,
        related_name='purchase_requests',
        help_text="Factory"
    )
    request_type = models.CharField(
        max_length=20,
        choices=REQUEST_TYPES,
        default='EXTERNAL',
        help_text="Type of request"
    )
    request_date = models.DateField(
        help_text="Date of request"
    )
    required_by_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date items are needed by"
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='NORMAL',
        help_text="Priority level"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        help_text="Current status"
    )
    justification = models.TextField(
        blank=True,
        null=True,
        help_text="Justification for the request"
    )
    total_estimated_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Total estimated value"
    )
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Currency"
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_prs',
        help_text="User who approved this PR"
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Approval timestamp"
    )
    rejection_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for rejection"
    )
    
    class Meta:
        db_table = 'purchase_requests'
        verbose_name = 'Purchase Request'
        verbose_name_plural = 'Purchase Requests'
        ordering = ['-request_date', '-created_at']
        indexes = [
            models.Index(fields=['pr_number']),
            models.Index(fields=['status', 'factory']),
            models.Index(fields=['requester', 'status']),
        ]
    
    def __str__(self):
        return f"{self.pr_number} - {self.requester.username} ({self.status})"
    
    def save(self, *args, **kwargs):
        """Auto-generate PR number if not set."""
        if not self.pr_number:
            # Format: PR-YYYY-NNNN
            from django.utils import timezone
            year = timezone.now().year
            last_pr = PurchaseRequest.objects.filter(
                pr_number__startswith=f'PR-{year}'
            ).order_by('-pr_number').first()
            
            if last_pr:
                last_num = int(last_pr.pr_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.pr_number = f'PR-{year}-{new_num:04d}'
        
        super().save(*args, **kwargs)


class PurchaseRequestLine(models.Model):
    """
    Individual line items in a Purchase Request.
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('CONVERTED', 'Converted to PO'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pr = models.ForeignKey(
        PurchaseRequest,
        on_delete=models.CASCADE,
        related_name='lines',
        help_text="Purchase request"
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name='pr_lines',
        help_text="Item"
    )
    requested_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(0.001)],
        help_text="Requested quantity"
    )
    uom = models.ForeignKey(
        UnitOfMeasurement,
        on_delete=models.PROTECT,
        help_text="Unit of measurement"
    )
    estimated_unit_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Estimated unit price"
    )
    estimated_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Estimated total (qty × price)"
    )
    required_by_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date item is needed by"
    )
    specification = models.TextField(
        blank=True,
        null=True,
        help_text="Item specifications"
    )
    justification = models.TextField(
        blank=True,
        null=True,
        help_text="Justification for this item"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text="Line status"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'purchase_request_lines'
        verbose_name = 'Purchase Request Line'
        verbose_name_plural = 'Purchase Request Lines'
        ordering = ['pr', 'created_at']
    
    def __str__(self):
        return f"{self.pr.pr_number} - {self.item.sku} ({self.requested_qty} {self.uom.uom_code})"
    
    def save(self, *args, **kwargs):
        """Calculate estimated total."""
        if self.estimated_unit_price and self.requested_qty:
            self.estimated_total = self.estimated_unit_price * self.requested_qty
        super().save(*args, **kwargs)


# ============================================================================
# PURCHASE ORDER (PO)
# ============================================================================

class PurchaseOrder(BaseModel):
    """
    Purchase Order - Official order sent to supplier.
    """
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('APPROVED', 'Approved'),
        ('SENT_TO_SUPPLIER', 'Sent to Supplier'),
        ('PARTIALLY_RECEIVED', 'Partially Received'),
        ('FULLY_RECEIVED', 'Fully Received'),
        ('CLOSED', 'Closed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    po_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique PO number"
    )
    pr = models.ForeignKey(
        PurchaseRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_orders',
        help_text="Source purchase request"
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='purchase_orders',
        help_text="Supplier"
    )
    factory = models.ForeignKey(
        Factory,
        on_delete=models.PROTECT,
        related_name='purchase_orders',
        help_text="Factory"
    )
    po_date = models.DateField(
        help_text="PO date"
    )
    delivery_date = models.DateField(
        help_text="Expected delivery date"
    )
    payment_terms = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Payment terms"
    )
    delivery_address = models.TextField(
        blank=True,
        null=True,
        help_text="Delivery address"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        help_text="PO status"
    )
    
    # Financial fields
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Total amount before taxes"
    )
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        help_text="Currency"
    )
    exchange_rate = models.DecimalField(
        max_digits=15,
        decimal_places=6,
        default=1.0,
        help_text="Exchange rate to base currency"
    )
    total_amount_bdt = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total amount in BDT"
    )
    vat_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="VAT percentage"
    )
    vat_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="VAT amount"
    )
    tax_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Tax percentage"
    )
    tax_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Tax amount"
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Discount percentage"
    )
    discount_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Discount amount"
    )
    grand_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Grand total (after taxes and discounts)"
    )
    
    terms_and_conditions = models.TextField(
        blank=True,
        null=True,
        help_text="Terms and conditions"
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_pos',
        help_text="Approver"
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Approval timestamp"
    )
    
    class Meta:
        db_table = 'purchase_orders'
        verbose_name = 'Purchase Order'
        verbose_name_plural = 'Purchase Orders'
        ordering = ['-po_date', '-created_at']
        indexes = [
            models.Index(fields=['po_number']),
            models.Index(fields=['supplier', 'status']),
            models.Index(fields=['factory', 'status']),
        ]
    
    def __str__(self):
        return f"{self.po_number} - {self.supplier.name} ({self.status})"
    
    def save(self, *args, **kwargs):
        """Auto-generate PO number and calculate totals."""
        if not self.po_number:
            from django.utils import timezone
            year = timezone.now().year
            last_po = PurchaseOrder.objects.filter(
                po_number__startswith=f'PO-{year}'
            ).order_by('-po_number').first()
            
            if last_po:
                last_num = int(last_po.po_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.po_number = f'PO-{year}-{new_num:04d}'
        
        # Calculate grand total
        if self.total_amount:
            self.grand_total = (
                self.total_amount 
                + self.vat_amount 
                + self.tax_amount 
                - self.discount_amount
            )
            self.total_amount_bdt = self.grand_total * self.exchange_rate
        
        super().save(*args, **kwargs)


class PurchaseOrderLine(models.Model):
    """
    Individual line items in a Purchase Order.
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PARTIALLY_RECEIVED', 'Partially Received'),
        ('FULLY_RECEIVED', 'Fully Received'),
        ('CLOSED', 'Closed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    po = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='lines',
        help_text="Purchase order"
    )
    pr_line = models.ForeignKey(
        PurchaseRequestLine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='po_lines',
        help_text="Source PR line"
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name='po_lines',
        help_text="Item"
    )
    ordered_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(0.001)],
        help_text="Ordered quantity"
    )
    received_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Received quantity"
    )
    pending_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(0)],
        help_text="Pending quantity (calculated)"
    )
    uom = models.ForeignKey(
        UnitOfMeasurement,
        on_delete=models.PROTECT,
        help_text="Unit of measurement"
    )
    unit_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Unit price"
    )
    total_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Total price (qty × price)"
    )
    delivery_date = models.DateField(
        null=True,
        blank=True,
        help_text="Expected delivery date"
    )
    specification = models.TextField(
        blank=True,
        null=True,
        help_text="Item specifications"
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
        db_table = 'purchase_order_lines'
        verbose_name = 'Purchase Order Line'
        verbose_name_plural = 'Purchase Order Lines'
        ordering = ['po', 'created_at']
    
    def __str__(self):
        return f"{self.po.po_number} - {self.item.sku} ({self.ordered_qty} {self.uom.uom_code})"
    
    def save(self, *args, **kwargs):
        """Calculate totals and pending qty."""
        self.total_price = self.unit_price * self.ordered_qty
        self.pending_qty = self.ordered_qty - self.received_qty
        
        # Update status based on received qty
        if self.received_qty == 0:
            self.status = 'PENDING'
        elif self.received_qty < self.ordered_qty:
            self.status = 'PARTIALLY_RECEIVED'
        else:
            self.status = 'FULLY_RECEIVED'
        
        super().save(*args, **kwargs)


# ============================================================================
# GOODS RECEIVED NOTE (GRN)
# ============================================================================

class GoodsReceivedNote(BaseModel):
    """
    Goods Received Note - Records receipt of goods from supplier.
    """
    
    QC_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('PASSED', 'Passed'),
        ('REJECTED', 'Rejected'),
        ('PARTIAL', 'Partial Pass'),
    ]
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('QC_PENDING', 'QC Pending'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('POSTED', 'Posted to Stock'),
    ]
    
    grn_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique GRN number"
    )
    po = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='grns',
        help_text="Purchase order"
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='grns',
        help_text="Supplier"
    )
    factory = models.ForeignKey(
        Factory,
        on_delete=models.PROTECT,
        related_name='grns',
        help_text="Factory"
    )
    grn_date = models.DateField(
        help_text="GRN date"
    )
    received_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='received_grns',
        help_text="User who received the goods"
    )
    received_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Receipt timestamp"
    )
    
    # Delivery details
    delivery_challan_no = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Delivery challan number"
    )
    delivery_challan_date = models.DateField(
        null=True,
        blank=True,
        help_text="Delivery challan date"
    )
    vehicle_no = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Vehicle number"
    )
    transporter_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Transporter/carrier name"
    )
    
    # QC fields
    qc_status = models.CharField(
        max_length=20,
        choices=QC_STATUS_CHOICES,
        default='PENDING',
        help_text="QC status"
    )
    qc_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='qc_grns',
        help_text="QC inspector"
    )
    qc_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="QC timestamp"
    )
    
    total_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total value"
    )
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Currency"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        help_text="GRN status"
    )
    remarks = models.TextField(
        blank=True,
        null=True,
        help_text="Remarks"
    )
    
    class Meta:
        db_table = 'goods_received_notes'
        verbose_name = 'Goods Received Note'
        verbose_name_plural = 'Goods Received Notes'
        ordering = ['-grn_date', '-created_at']
        indexes = [
            models.Index(fields=['grn_number']),
            models.Index(fields=['supplier', 'status']),
            models.Index(fields=['po', 'status']),
        ]
    
    def __str__(self):
        return f"{self.grn_number} - {self.supplier.name} ({self.status})"
    
    def save(self, *args, **kwargs):
        """Auto-generate GRN number."""
        if not self.grn_number:
            from django.utils import timezone
            year = timezone.now().year
            last_grn = GoodsReceivedNote.objects.filter(
                grn_number__startswith=f'GRN-{year}'
            ).order_by('-grn_number').first()
            
            if last_grn:
                last_num = int(last_grn.grn_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.grn_number = f'GRN-{year}-{new_num:04d}'
        
        super().save(*args, **kwargs)


class GRNLine(models.Model):
    """
    Individual line items in a GRN.
    """
    
    QC_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('HOLD', 'On Hold'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grn = models.ForeignKey(
        GoodsReceivedNote,
        on_delete=models.CASCADE,
        related_name='lines',
        help_text="Goods received note"
    )
    po_line = models.ForeignKey(
        PurchaseOrderLine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='grn_lines',
        help_text="Source PO line"
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name='grn_lines',
        help_text="Item"
    )
    ordered_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Ordered quantity (from PO)"
    )
    received_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(0.001)],
        help_text="Received quantity"
    )
    accepted_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Accepted quantity (after QC)"
    )
    rejected_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Rejected quantity (after QC)"
    )
    uom = models.ForeignKey(
        UnitOfMeasurement,
        on_delete=models.PROTECT,
        help_text="Unit of measurement"
    )
    unit_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Unit price"
    )
    total_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Total price"
    )
    
    # Batch/Serial tracking
    batch_no = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Batch number"
    )
    lot_no = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Lot number"
    )
    serial_no = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Serial number (for serialized items)"
    )
    manufacture_date = models.DateField(
        null=True,
        blank=True,
        help_text="Manufacture date"
    )
    expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text="Expiry date"
    )
    
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Storage location"
    )
    
    # QC fields
    qc_status = models.CharField(
        max_length=20,
        choices=QC_STATUS_CHOICES,
        default='PENDING',
        help_text="QC status"
    )
    qc_remarks = models.TextField(
        blank=True,
        null=True,
        help_text="QC remarks"
    )
    rejection_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Rejection reason"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'grn_lines'
        verbose_name = 'GRN Line'
        verbose_name_plural = 'GRN Lines'
        ordering = ['grn', 'created_at']
    
    def __str__(self):
        return f"{self.grn.grn_number} - {self.item.sku} ({self.received_qty} {self.uom.uom_code})"
    
    def save(self, *args, **kwargs):
        """Calculate total price."""
        self.total_price = self.unit_price * self.received_qty
        super().save(*args, **kwargs)


# ============================================================================
# QC INSPECTION
# ============================================================================

class QCInspection(BaseModel):
    """
    Quality Control Inspection records for GRNs.
    """
    
    INSPECTION_TYPES = [
        ('VISUAL', 'Visual Inspection'),
        ('DIMENSIONAL', 'Dimensional Check'),
        ('FUNCTIONAL', 'Functional Test'),
        ('LAB_TEST', 'Laboratory Test'),
    ]
    
    STATUS_CHOICES = [
        ('PASS', 'Pass'),
        ('FAIL', 'Fail'),
        ('CONDITIONAL_PASS', 'Conditional Pass'),
        ('HOLD', 'Hold'),
    ]
    
    grn = models.ForeignKey(
        GoodsReceivedNote,
        on_delete=models.CASCADE,
        related_name='qc_inspections',
        help_text="Goods received note"
    )
    inspection_date = models.DateField(
        help_text="Inspection date"
    )
    inspector = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='qc_inspections',
        help_text="QC inspector"
    )
    inspection_type = models.CharField(
        max_length=50,
        choices=INSPECTION_TYPES,
        blank=True,
        null=True,
        help_text="Type of inspection"
    )
    overall_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        help_text="Overall inspection result"
    )
    defects_found = models.JSONField(
        blank=True,
        null=True,
        help_text="JSON array of defects found"
    )
    test_results = models.JSONField(
        blank=True,
        null=True,
        help_text="Lab test results (if applicable)"
    )
    remarks = models.TextField(
        blank=True,
        null=True,
        help_text="Inspector remarks"
    )
    attachments = models.JSONField(
        blank=True,
        null=True,
        help_text="File attachments (file paths)"
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_qc_inspections',
        help_text="Approver"
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Approval timestamp"
    )
    
    class Meta:
        db_table = 'qc_inspections'
        verbose_name = 'QC Inspection'
        verbose_name_plural = 'QC Inspections'
        ordering = ['-inspection_date']
    
    def __str__(self):
        return f"{self.grn.grn_number} - {self.inspection_date} ({self.overall_status})"


# ============================================================================
# STOCK BATCH
# ============================================================================

class StockBatch(models.Model):
    """
    Stock batches for batch-controlled items.
    
    Tracks inventory by batch/lot number for FIFO valuation.
    """
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('QUARANTINE', 'Quarantine'),
        ('EXPIRED', 'Expired'),
        ('CONSUMED', 'Consumed'),
        ('DISPOSED', 'Disposed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name='stock_batches',
        help_text="Item"
    )
    batch_no = models.CharField(
        max_length=50,
        help_text="Batch number"
    )
    lot_no = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Lot number"
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name='stock_batches',
        help_text="Storage location"
    )
    grn_line = models.ForeignKey(
        GRNLine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_batches',
        help_text="Source GRN line"
    )
    manufacture_date = models.DateField(
        null=True,
        blank=True,
        help_text="Manufacture date"
    )
    expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text="Expiry date"
    )
    qty_received = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(0)],
        help_text="Original received quantity"
    )
    qty_on_hand = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(0)],
        help_text="Current quantity on hand"
    )
    qty_allocated = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Quantity allocated (reserved)"
    )
    qty_available = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Available quantity (on_hand - allocated)"
    )
    uom = models.ForeignKey(
        UnitOfMeasurement,
        on_delete=models.PROTECT,
        help_text="Unit of measurement"
    )
    unit_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Unit cost (for FIFO valuation)"
    )
    total_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Total value (qty × cost)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE',
        help_text="Batch status"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'stock_batches'
        verbose_name = 'Stock Batch'
        verbose_name_plural = 'Stock Batches'
        unique_together = ['item', 'batch_no', 'location']
        ordering = ['item', 'created_at']
        indexes = [
            models.Index(fields=['item', 'location']),
            models.Index(fields=['batch_no']),
            models.Index(fields=['expiry_date']),
        ]
    
    def __str__(self):
        return f"{self.item.sku} - Batch {self.batch_no} @ {self.location.location_code}"
    
    def save(self, *args, **kwargs):
        """Calculate available quantity and total value."""
        self.qty_available = self.qty_on_hand - self.qty_allocated
        self.total_value = self.qty_on_hand * self.unit_cost
        super().save(*args, **kwargs)


# ============================================================================
# STOCK MOVEMENT
# ============================================================================

class StockMovement(models.Model):
    """
    Stock movement ledger - records all inventory transactions.
    
    This is the single source of truth for all stock changes.
    """
    
    MOVEMENT_TYPES = [
        ('PURCHASE_IN', 'Purchase Receipt'),
        ('ISSUE_OUT', 'Issue to Department'),
        ('TRANSFER', 'Location Transfer'),
        ('ADJUSTMENT_IN', 'Adjustment Increase'),
        ('ADJUSTMENT_OUT', 'Adjustment Decrease'),
        ('RETURN_IN', 'Return to Stock'),
        ('RETURN_OUT', 'Return to Supplier'),
        ('SCRAP', 'Scrap/Disposal'),
        ('PRODUCTION_IN', 'Production Receipt'),
        ('PRODUCTION_OUT', 'Production Issue'),
        ('DAMAGE', 'Damage'),
        ('THEFT', 'Theft/Loss'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name='stock_movements',
        help_text="Item"
    )
    from_location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='stock_movements_from',
        help_text="Source location"
    )
    to_location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='stock_movements_to',
        help_text="Destination location"
    )
    movement_type = models.CharField(
        max_length=20,
        choices=MOVEMENT_TYPES,
        help_text="Type of movement"
    )
    reference_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Reference document type (GRN, PO, ISSUE, etc.)"
    )
    reference_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Reference document ID"
    )
    reference_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Reference document number"
    )
    batch = models.ForeignKey(
        StockBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movements',
        help_text="Stock batch"
    )
    serial_no = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Serial number (for serialized items)"
    )
    quantity = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(0.001)],
        help_text="Movement quantity"
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
        help_text="Unit cost at time of movement"
    )
    total_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total value (qty × cost)"
    )
    fiscal_year = models.IntegerField(
        null=True,
        blank=True,
        help_text="Fiscal year"
    )
    fiscal_month = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text="Fiscal month"
    )
    transaction_date = models.DateField(
        help_text="Transaction date"
    )
    transaction_time = models.DateTimeField(
        auto_now_add=True,
        help_text="Transaction timestamp"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='stock_movements_created',
        help_text="User who created this movement"
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements_approved',
        help_text="Approver"
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Approval timestamp"
    )
    reason_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Reason code for movement"
    )
    remarks = models.TextField(
        blank=True,
        null=True,
        help_text="Remarks"
    )
    is_reversed = models.BooleanField(
        default=False,
        help_text="Is this movement reversed?"
    )
    reversed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements_reversed',
        help_text="User who reversed this movement"
    )
    reversed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Reversal timestamp"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'stock_movements'
        verbose_name = 'Stock Movement'
        verbose_name_plural = 'Stock Movements'
        ordering = ['-transaction_date', '-transaction_time']
        indexes = [
            models.Index(fields=['item', 'transaction_date']),
            models.Index(fields=['movement_type', 'transaction_date']),
            models.Index(fields=['from_location', 'transaction_date']),
            models.Index(fields=['to_location', 'transaction_date']),
            models.Index(fields=['reference_type', 'reference_id']),
        ]
    
    def __str__(self):
        return f"{self.movement_type} - {self.item.sku} ({self.quantity} {self.uom.uom_code}) on {self.transaction_date}"
    
    def save(self, *args, **kwargs):
        """Calculate total value and fiscal period."""
        if self.unit_cost and self.quantity:
            self.total_value = self.unit_cost * self.quantity
        
        # Calculate fiscal year and month from transaction date
        if self.transaction_date:
            self.fiscal_year = self.transaction_date.year
            self.fiscal_month = self.transaction_date.month
        
        super().save(*args, **kwargs)
    
    def reverse_movement(self, user):
        """
        Reverse this stock movement.
        Creates an opposite movement to cancel this one.
        """
        if self.is_reversed:
            raise ValidationError("This movement has already been reversed.")
        
        # Create reverse movement
        reverse_movement = StockMovement.objects.create(
            item=self.item,
            from_location=self.to_location,  # Swap locations
            to_location=self.from_location,
            movement_type=self.movement_type,
            reference_type=f"REVERSAL_{self.reference_type}",
            reference_id=self.id,
            reference_number=f"REV-{self.reference_number}",
            batch=self.batch,
            serial_no=self.serial_no,
            quantity=self.quantity,
            uom=self.uom,
            unit_cost=self.unit_cost,
            transaction_date=self.transaction_date,
            created_by=user,
            reason_code="REVERSAL",
            remarks=f"Reversal of movement {self.id}"
        )
        
        # Mark original as reversed
        self.is_reversed = True
        self.reversed_by = user
        from django.utils import timezone
        self.reversed_at = timezone.now()
        self.save(update_fields=['is_reversed', 'reversed_by', 'reversed_at'])
        
        return reverse_movement


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_current_stock(item, location=None):
    """
    Get current stock quantity for an item.
    
    Args:
        item: Item instance or item_id
        location: Location instance or location_id (optional)
    
    Returns:
        Decimal: Current stock quantity
    """
    from django.db.models import Sum, Q
    
    movements = StockMovement.objects.filter(
        item=item,
        is_reversed=False
    )
    
    if location:
        movements = movements.filter(
            Q(from_location=location) | Q(to_location=location)
        )
    
    # Calculate IN movements (to_location matches)
    in_qty = movements.filter(
        to_location=location if location else None,
        movement_type__in=[
            'PURCHASE_IN', 'ADJUSTMENT_IN', 'RETURN_IN', 
            'PRODUCTION_IN', 'TRANSFER'
        ]
    ).aggregate(total=Sum('quantity'))['total'] or 0
    
    # Calculate OUT movements (from_location matches)
    out_qty = movements.filter(
        from_location=location if location else None,
        movement_type__in=[
            'ISSUE_OUT', 'ADJUSTMENT_OUT', 'RETURN_OUT', 
            'SCRAP', 'PRODUCTION_OUT', 'DAMAGE', 'THEFT', 'TRANSFER'
        ]
    ).aggregate(total=Sum('quantity'))['total'] or 0
    
    return in_qty - out_qty


def get_item_valuation(item, location=None):
    """
    Get current valuation of an item using FIFO method.
    
    Args:
        item: Item instance or item_id
        location: Location instance or location_id (optional)
    
    Returns:
        dict: {quantity, value, avg_cost}
    """
    batches = StockBatch.objects.filter(
        item=item,
        qty_on_hand__gt=0,
        status='ACTIVE'
    )
    
    if location:
        batches = batches.filter(location=location)
    
    batches = batches.order_by('created_at')  # FIFO
    
    total_qty = sum(b.qty_on_hand for b in batches)
    total_value = sum(b.total_value for b in batches)
    avg_cost = total_value / total_qty if total_qty > 0 else 0
    
    return {
        'quantity': total_qty,
        'value': total_value,
        'avg_cost': avg_cost
    }