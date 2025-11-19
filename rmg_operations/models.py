"""
RMG Operations Models
=====================
This module contains:
1. Yarn Allocations & Issues
2. Yarn Gate Passes
3. Knitting Programs
4. Gray Fabric Receipts & Inspections
5. Gray Fabric Issues
6. Finish Fabric Receipts & Issues
7. Fabric Leftover Management
8. Knitting Bills
9. Dyeing Bills
"""

import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from core.models import BaseModel, Factory, Location
from users.models import User
from inventory.models import Item, UnitOfMeasurement, Supplier, Currency
from production.models import WorkOrder


# ============================================================================
# YARN STORE OPERATIONS
# ============================================================================

class YarnAllocation(BaseModel):
    """
    Yarn allocation to work orders.
    
    Links yarn inventory to specific production orders.
    """
    
    STATUS_CHOICES = [
        ('ALLOCATED', 'Allocated'),
        ('ISSUED', 'Issued'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    allocation_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Allocation number"
    )
    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.PROTECT,
        related_name='yarn_allocations',
        help_text="Work order"
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name='yarn_allocations',
        help_text="Yarn item"
    )
    allocated_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(0.001)],
        help_text="Allocated quantity"
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
        help_text="Pending quantity"
    )
    uom = models.ForeignKey(
        UnitOfMeasurement,
        on_delete=models.PROTECT,
        help_text="Unit of measurement"
    )
    allocation_date = models.DateField(
        help_text="Allocation date"
    )
    allocated_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='yarn_allocations_made',
        help_text="Allocated by"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ALLOCATED',
        help_text="Status"
    )
    remarks = models.TextField(
        blank=True,
        null=True,
        help_text="Remarks"
    )
    
    class Meta:
        db_table = 'yarn_allocations'
        verbose_name = 'Yarn Allocation'
        verbose_name_plural = 'Yarn Allocations'
        ordering = ['-allocation_date', '-created_at']
        indexes = [
            models.Index(fields=['allocation_number']),
            models.Index(fields=['work_order', 'status']),
        ]
    
    def __str__(self):
        return f"{self.allocation_number} - WO: {self.work_order.wo_number}"
    
    def save(self, *args, **kwargs):
        """Auto-generate allocation number and calculate pending qty."""
        if not self.allocation_number:
            year = timezone.now().year
            last_alloc = YarnAllocation.objects.filter(
                allocation_number__startswith=f'YALLOC-{year}'
            ).order_by('-allocation_number').first()
            
            if last_alloc:
                last_num = int(last_alloc.allocation_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.allocation_number = f'YALLOC-{year}-{new_num:04d}'
        
        self.pending_qty = self.allocated_qty - self.issued_qty
        super().save(*args, **kwargs)


class YarnIssue(BaseModel):
    """
    Yarn issue for knitting (internal or external).
    """
    
    ISSUE_TYPES = [
        ('KNITTING_INTERNAL', 'Internal Knitting'),
        ('KNITTING_EXTERNAL', 'External Knitting'),
        ('SAMPLE', 'Sample'),
        ('ADDITIONAL', 'Additional Issue'),
    ]
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('APPROVED', 'Approved'),
        ('ISSUED', 'Issued'),
        ('RETURNED', 'Returned'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    yarn_issue_no = models.CharField(
        max_length=50,
        unique=True,
        help_text="Yarn issue number"
    )
    allocation = models.ForeignKey(
        YarnAllocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='yarn_issues',
        help_text="Source allocation"
    )
    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.PROTECT,
        related_name='yarn_issues',
        help_text="Work order"
    )
    issue_type = models.CharField(
        max_length=20,
        choices=ISSUE_TYPES,
        help_text="Issue type"
    )
    issue_date = models.DateField(
        help_text="Issue date"
    )
    factory = models.ForeignKey(
        Factory,
        on_delete=models.PROTECT,
        related_name='yarn_issues',
        help_text="Factory"
    )
    knitting_party = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='yarn_issues_received',
        help_text="Knitting party (for external)"
    )
    issued_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='yarn_issues_made',
        help_text="Issued by"
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='yarn_issues_approved',
        help_text="Approved by"
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
        db_table = 'yarn_issues'
        verbose_name = 'Yarn Issue'
        verbose_name_plural = 'Yarn Issues'
        ordering = ['-issue_date', '-created_at']
        indexes = [
            models.Index(fields=['yarn_issue_no']),
            models.Index(fields=['work_order', 'status']),
        ]
    
    def __str__(self):
        return f"{self.yarn_issue_no} - {self.work_order.wo_number}"
    
    def save(self, *args, **kwargs):
        """Auto-generate yarn issue number."""
        if not self.yarn_issue_no:
            year = timezone.now().year
            last_issue = YarnIssue.objects.filter(
                yarn_issue_no__startswith=f'YISS-{year}'
            ).order_by('-yarn_issue_no').first()
            
            if last_issue:
                last_num = int(last_issue.yarn_issue_no.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.yarn_issue_no = f'YISS-{year}-{new_num:04d}'
        
        super().save(*args, **kwargs)


class YarnIssueLine(models.Model):
    """Line items for yarn issues."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    yarn_issue = models.ForeignKey(
        YarnIssue,
        on_delete=models.CASCADE,
        related_name='lines',
        help_text="Yarn issue"
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name='yarn_issue_lines',
        help_text="Yarn item"
    )
    lot_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Lot number"
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
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='yarn_issue_lines',
        help_text="Source location"
    )
    remarks = models.TextField(
        blank=True,
        null=True,
        help_text="Remarks"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'yarn_issue_lines'
        verbose_name = 'Yarn Issue Line'
        verbose_name_plural = 'Yarn Issue Lines'
    
    def __str__(self):
        return f"{self.yarn_issue.yarn_issue_no} - {self.item.sku}"


class YarnGatePass(BaseModel):
    """
    Gate pass for yarn going out of factory.
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('OUT', 'Out'),
        ('RETURNED', 'Returned'),
    ]
    
    gate_pass_no = models.CharField(
        max_length=50,
        unique=True,
        help_text="Gate pass number"
    )
    yarn_issue = models.ForeignKey(
        YarnIssue,
        on_delete=models.PROTECT,
        related_name='gate_passes',
        help_text="Yarn issue"
    )
    gate_pass_date = models.DateField(
        help_text="Gate pass date"
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
    driver_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Driver phone"
    )
    expected_return_date = models.DateField(
        null=True,
        blank=True,
        help_text="Expected return date"
    )
    actual_return_date = models.DateField(
        null=True,
        blank=True,
        help_text="Actual return date"
    )
    issued_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='gate_passes_issued',
        help_text="Issued by"
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gate_passes_approved',
        help_text="Approved by"
    )
    security_checked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gate_passes_checked',
        help_text="Security checked by"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text="Status"
    )
    remarks = models.TextField(
        blank=True,
        null=True,
        help_text="Remarks"
    )
    
    class Meta:
        db_table = 'yarn_gate_passes'
        verbose_name = 'Yarn Gate Pass'
        verbose_name_plural = 'Yarn Gate Passes'
        ordering = ['-gate_pass_date', '-created_at']
        indexes = [
            models.Index(fields=['gate_pass_no']),
            models.Index(fields=['yarn_issue', 'status']),
        ]
    
    def __str__(self):
        return f"{self.gate_pass_no} - {self.yarn_issue.yarn_issue_no}"
    
    def save(self, *args, **kwargs):
        """Auto-generate gate pass number."""
        if not self.gate_pass_no:
            year = timezone.now().year
            last_gp = YarnGatePass.objects.filter(
                gate_pass_no__startswith=f'YGP-{year}'
            ).order_by('-gate_pass_no').first()
            
            if last_gp:
                last_num = int(last_gp.gate_pass_no.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.gate_pass_no = f'YGP-{year}-{new_num:04d}'
        
        super().save(*args, **kwargs)


# ============================================================================
# KNITTING PROGRAMS
# ============================================================================

class KnittingProgram(BaseModel):
    """
    Knitting program/schedule.
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    program_no = models.CharField(
        max_length=50,
        unique=True,
        help_text="Program number"
    )
    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.PROTECT,
        related_name='knitting_programs',
        help_text="Work order"
    )
    yarn_issue = models.ForeignKey(
        YarnIssue,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='knitting_programs',
        help_text="Yarn issue"
    )
    knitting_party = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='knitting_programs',
        help_text="Knitting party"
    )
    program_date = models.DateField(
        help_text="Program date"
    )
    planned_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(0.001)],
        help_text="Planned quantity"
    )
    actual_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Actual production quantity"
    )
    uom = models.ForeignKey(
        UnitOfMeasurement,
        on_delete=models.PROTECT,
        help_text="Unit of measurement"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text="Status"
    )
    remarks = models.TextField(
        blank=True,
        null=True,
        help_text="Remarks"
    )
    
    class Meta:
        db_table = 'knitting_programs'
        verbose_name = 'Knitting Program'
        verbose_name_plural = 'Knitting Programs'
        ordering = ['-program_date', '-created_at']
        indexes = [
            models.Index(fields=['program_no']),
            models.Index(fields=['work_order', 'status']),
        ]
    
    def __str__(self):
        return f"{self.program_no} - {self.work_order.wo_number}"
    
    def save(self, *args, **kwargs):
        """Auto-generate program number."""
        if not self.program_no:
            year = timezone.now().year
            last_prog = KnittingProgram.objects.filter(
                program_no__startswith=f'KPROG-{year}'
            ).order_by('-program_no').first()
            
            if last_prog:
                last_num = int(last_prog.program_no.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.program_no = f'KPROG-{year}-{new_num:04d}'
        
        super().save(*args, **kwargs)