"""
Asset Management Models
=======================
This module contains:
1. Asset - Fixed assets and serialized equipment (IT, machinery, tools)
2. AssetAssignmentHistory - Track asset assignments to users/departments
3. AssetMaintenanceRecord - Track maintenance, repairs, and inspections
4. AssetDepreciation - Calculate and track depreciation

Supports:
- IT asset management (laptops, desktops, phones, printers)
- Serialized equipment tracking (machines, tools)
- Assignment tracking with signatures
- Warranty management
- Maintenance scheduling
- Depreciation calculation (Straight-line, Declining Balance)
- Software license management
"""

import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from core.models import BaseModel, Factory, Department, Location
from users.models import User
from inventory.models import Item, Supplier, Currency
from procurement.models import PurchaseOrder, GoodsReceivedNote


# ============================================================================
# ASSET MODEL
# ============================================================================

class Asset(BaseModel):
    """
    Fixed Asset / Serialized Equipment tracking.
    
    Tracks IT equipment, machinery, tools, and any serialized items.
    Supports warranty, assignment, depreciation, and maintenance.
    """
    
    STATUS_CHOICES = [
        ('IN_STOCK', 'In Stock'),
        ('ASSIGNED', 'Assigned'),
        ('IN_REPAIR', 'In Repair'),
        ('RETIRED', 'Retired'),
        ('DISPOSED', 'Disposed'),
        ('LOST', 'Lost'),
        ('STOLEN', 'Stolen'),
    ]
    
    DEPRECIATION_METHODS = [
        ('STRAIGHT_LINE', 'Straight Line'),
        ('DECLINING_BALANCE', 'Declining Balance'),
        ('NO_DEPRECIATION', 'No Depreciation'),
    ]
    
    # Basic Information
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name='assets',
        help_text="Item master reference"
    )
    asset_tag = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique asset tag/barcode (e.g., 'AST-2025-0001')"
    )
    serial_no = models.CharField(
        max_length=100,
        unique=True,
        help_text="Serial number from manufacturer"
    )
    model = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Model number/name"
    )
    manufacturer = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Manufacturer name"
    )
    
    # IT-Specific Fields
    mac_address = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="MAC address (for network devices)"
    )
    imei = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="IMEI number (for mobile devices)",
        verbose_name="IMEI"
    )
    
    # Purchase Information
    po = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assets',
        help_text="Source purchase order"
    )
    grn = models.ForeignKey(
        GoodsReceivedNote,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assets',
        help_text="Source GRN"
    )
    purchase_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of purchase"
    )
    purchase_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Original purchase price"
    )
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Purchase currency"
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assets_supplied',
        help_text="Supplier"
    )
    invoice_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Invoice number"
    )
    
    # Warranty Information
    warranty_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Warranty start date"
    )
    warranty_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Warranty end date"
    )
    warranty_terms = models.TextField(
        blank=True,
        null=True,
        help_text="Warranty terms and conditions"
    )
    
    # Current Assignment
    current_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='IN_STOCK',
        help_text="Current asset status"
    )
    assigned_to_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_assets',
        help_text="Currently assigned to user"
    )
    assigned_to_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_assets',
        help_text="Currently assigned to department"
    )
    assigned_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Assignment timestamp"
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='assets',
        help_text="Current location"
    )
    
    # Depreciation
    depreciation_method = models.CharField(
        max_length=20,
        choices=DEPRECIATION_METHODS,
        default='STRAIGHT_LINE',
        help_text="Depreciation calculation method"
    )
    useful_life_years = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        help_text="Expected useful life in years"
    )
    salvage_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Estimated salvage value at end of life"
    )
    current_book_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Current book value (after depreciation)"
    )
    accumulated_depreciation = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Total accumulated depreciation"
    )
    
    # Maintenance
    last_maintenance_date = models.DateField(
        null=True,
        blank=True,
        help_text="Last maintenance date"
    )
    next_maintenance_date = models.DateField(
        null=True,
        blank=True,
        help_text="Next scheduled maintenance date"
    )
    maintenance_frequency_days = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Maintenance frequency in days"
    )
    
    # Disposal
    disposal_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of disposal"
    )
    disposal_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for disposal"
    )
    disposal_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Sale/scrap value at disposal"
    )
    
    # Software License (for IT assets)
    license_key = models.TextField(
        blank=True,
        null=True,
        help_text="Software license key(s)"
    )
    license_expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text="License expiry date"
    )
    
    # Attachments & Notes
    attachments = models.JSONField(
        blank=True,
        null=True,
        help_text="File attachments (JSON array of file paths)"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Is asset active?"
    )
    
    class Meta:
        db_table = 'assets'
        verbose_name = 'Asset'
        verbose_name_plural = 'Assets'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['asset_tag']),
            models.Index(fields=['serial_no']),
            models.Index(fields=['item', 'current_status']),
            models.Index(fields=['assigned_to_user', 'current_status']),
            models.Index(fields=['current_status', 'is_active']),
            models.Index(fields=['next_maintenance_date']),
            models.Index(fields=['warranty_end_date']),
        ]
    
    def __str__(self):
        return f"{self.asset_tag} - {self.item.item_name}"
    
    def save(self, *args, **kwargs):
        """Auto-generate asset tag and calculate depreciation."""
        if not self.asset_tag:
            self.asset_tag = self._generate_asset_tag()
        
        # Calculate current book value
        if self.purchase_price and self.depreciation_method != 'NO_DEPRECIATION':
            self.calculate_depreciation()
        
        super().save(*args, **kwargs)
    
    def _generate_asset_tag(self):
        """Generate unique asset tag."""
        year = timezone.now().year
        last_asset = Asset.objects.filter(
            asset_tag__startswith=f'AST-{year}'
        ).order_by('-asset_tag').first()
        
        if last_asset:
            last_num = int(last_asset.asset_tag.split('-')[-1])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f'AST-{year}-{new_num:05d}'
    
    def calculate_depreciation(self):
        """
        Calculate accumulated depreciation and current book value.
        
        Methods:
        1. Straight Line: (Cost - Salvage) / Useful Life
        2. Declining Balance: Book Value × (2 / Useful Life)
        """
        if not self.purchase_date or not self.purchase_price or not self.useful_life_years:
            return
        
        cost = self.purchase_price
        salvage = self.salvage_value or Decimal('0')
        years_passed = self._calculate_years_since_purchase()
        
        if self.depreciation_method == 'STRAIGHT_LINE':
            annual_depreciation = (cost - salvage) / Decimal(str(self.useful_life_years))
            self.accumulated_depreciation = min(
                annual_depreciation * Decimal(str(years_passed)),
                cost - salvage  # Cap at depreciable amount
            )
        
        elif self.depreciation_method == 'DECLINING_BALANCE':
            rate = Decimal('2') / Decimal(str(self.useful_life_years))
            remaining_value = cost
            
            for _ in range(int(years_passed)):
                depreciation = remaining_value * rate
                remaining_value -= depreciation
                if remaining_value < salvage:
                    remaining_value = salvage
                    break
            
            self.accumulated_depreciation = cost - remaining_value
        
        self.current_book_value = max(cost - self.accumulated_depreciation, salvage)
    
    def _calculate_years_since_purchase(self):
        """Calculate fractional years since purchase date."""
        if not self.purchase_date:
            return 0
        
        delta = timezone.now().date() - self.purchase_date
        return Decimal(str(delta.days)) / Decimal('365.25')
    
    def assign_to_user(self, user, assigned_by=None):
        """
        Assign asset to a user.
        
        Args:
            user: User instance
            assigned_by: User who performed the assignment
        """
        # Create assignment history
        AssetAssignmentHistory.objects.create(
            asset=self,
            from_user=self.assigned_to_user,
            to_user=user,
            from_department=self.assigned_to_department,
            to_department=user.department,
            from_location=self.location,
            to_location=user.department.factory.locations.first() if user.department else None,
            assignment_type='NEW_ASSIGNMENT' if not self.assigned_to_user else 'TRANSFER',
            assigned_by=assigned_by
        )
        
        # Update asset
        self.assigned_to_user = user
        self.assigned_to_department = user.department
        self.assigned_at = timezone.now()
        self.current_status = 'ASSIGNED'
        self.save()
    
    def return_to_stock(self, returned_by, return_condition='GOOD', remarks=None):
        """
        Return asset to stock.
        
        Args:
            returned_by: User who returned the asset
            return_condition: Condition of returned asset
            remarks: Return remarks
        """
        # Create return history
        history = AssetAssignmentHistory.objects.create(
            asset=self,
            from_user=self.assigned_to_user,
            to_user=None,
            from_department=self.assigned_to_department,
            to_department=None,
            assignment_type='RETURN',
            assigned_by=returned_by,
            return_condition=return_condition,
            remarks=remarks
        )
        history.returned_at = timezone.now()
        history.save()
        
        # Update asset
        self.assigned_to_user = None
        self.assigned_to_department = None
        self.current_status = 'IN_STOCK'
        self.save()
    
    def schedule_maintenance(self, maintenance_date=None):
        """
        Schedule next maintenance.
        
        Args:
            maintenance_date: Specific date for next maintenance (optional)
        """
        if maintenance_date:
            self.next_maintenance_date = maintenance_date
        elif self.maintenance_frequency_days:
            base_date = self.last_maintenance_date or timezone.now().date()
            self.next_maintenance_date = base_date + relativedelta(days=self.maintenance_frequency_days)
        
        self.save()
    
    @property
    def is_under_warranty(self):
        """Check if asset is currently under warranty."""
        if not self.warranty_end_date:
            return False
        return timezone.now().date() <= self.warranty_end_date
    
    @property
    def is_maintenance_due(self):
        """Check if maintenance is due."""
        if not self.next_maintenance_date:
            return False
        return timezone.now().date() >= self.next_maintenance_date
    
    @property
    def warranty_days_remaining(self):
        """Calculate days remaining in warranty."""
        if not self.warranty_end_date:
            return None
        delta = self.warranty_end_date - timezone.now().date()
        return max(delta.days, 0)


# ============================================================================
# ASSET ASSIGNMENT HISTORY
# ============================================================================

class AssetAssignmentHistory(models.Model):
    """
    Track asset assignment history.
    
    Records all asset assignments, transfers, and returns.
    """
    
    ASSIGNMENT_TYPES = [
        ('NEW_ASSIGNMENT', 'New Assignment'),
        ('TRANSFER', 'Transfer'),
        ('RETURN', 'Return to Stock'),
        ('RETIREMENT', 'Retirement'),
    ]
    
    RETURN_CONDITIONS = [
        ('GOOD', 'Good Condition'),
        ('FAIR', 'Fair Condition'),
        ('DAMAGED', 'Damaged'),
        ('LOST', 'Lost'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='assignment_history',
        help_text="Asset"
    )
    
    # From/To tracking
    from_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asset_assignments_from',
        help_text="From user"
    )
    to_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asset_assignments_to',
        help_text="To user"
    )
    from_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asset_assignments_from',
        help_text="From department"
    )
    to_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asset_assignments_to',
        help_text="To department"
    )
    from_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asset_assignments_from',
        help_text="From location"
    )
    to_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asset_assignments_to',
        help_text="To location"
    )
    
    # Assignment details
    assignment_type = models.CharField(
        max_length=20,
        choices=ASSIGNMENT_TYPES,
        help_text="Type of assignment"
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asset_assignments_made',
        help_text="User who made the assignment"
    )
    assigned_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Assignment timestamp"
    )
    
    # Return details
    returned_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Return timestamp"
    )
    return_condition = models.CharField(
        max_length=20,
        choices=RETURN_CONDITIONS,
        null=True,
        blank=True,
        help_text="Condition of asset on return"
    )
    
    # Acceptance
    acceptance_signature = models.TextField(
        blank=True,
        null=True,
        help_text="Digital signature or acknowledgment"
    )
    acceptance_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of acceptance"
    )
    
    remarks = models.TextField(
        blank=True,
        null=True,
        help_text="Assignment remarks"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'asset_assignment_history'
        verbose_name = 'Asset Assignment History'
        verbose_name_plural = 'Asset Assignment Histories'
        ordering = ['-assigned_at']
        indexes = [
            models.Index(fields=['asset', '-assigned_at']),
            models.Index(fields=['to_user', '-assigned_at']),
            models.Index(fields=['assignment_type']),
        ]
    
    def __str__(self):
        if self.to_user:
            return f"{self.asset.asset_tag} → {self.to_user.full_name} ({self.assigned_at})"
        return f"{self.asset.asset_tag} - {self.assignment_type} ({self.assigned_at})"


# ============================================================================
# ASSET MAINTENANCE RECORD
# ============================================================================

class AssetMaintenanceRecord(models.Model):
    """
    Track asset maintenance, repairs, and inspections.
    """
    
    MAINTENANCE_TYPES = [
        ('PREVENTIVE', 'Preventive Maintenance'),
        ('CORRECTIVE', 'Corrective/Repair'),
        ('UPGRADE', 'Upgrade'),
        ('INSPECTION', 'Inspection'),
        ('CALIBRATION', 'Calibration'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='maintenance_records',
        help_text="Asset"
    )
    maintenance_type = models.CharField(
        max_length=20,
        choices=MAINTENANCE_TYPES,
        help_text="Type of maintenance"
    )
    maintenance_date = models.DateField(
        help_text="Date of maintenance"
    )
    
    # Performed by
    performed_by = models.CharField(
        max_length=100,
        help_text="Person/team who performed maintenance"
    )
    is_internal = models.BooleanField(
        default=True,
        help_text="Was maintenance done internally?"
    )
    vendor = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asset_maintenance',
        help_text="External vendor (if applicable)"
    )
    
    # Cost tracking
    cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Maintenance cost"
    )
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Currency"
    )
    
    # Details
    description = models.TextField(
        help_text="Description of work performed"
    )
    issues_found = models.TextField(
        blank=True,
        null=True,
        help_text="Issues found during maintenance"
    )
    actions_taken = models.TextField(
        blank=True,
        null=True,
        help_text="Actions taken / repairs made"
    )
    parts_replaced = models.JSONField(
        blank=True,
        null=True,
        help_text="JSON array of parts replaced"
    )
    
    # Scheduling
    next_maintenance_date = models.DateField(
        null=True,
        blank=True,
        help_text="Next scheduled maintenance date"
    )
    
    # Downtime tracking
    downtime_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Hours of downtime"
    )
    
    # Attachments
    attachments = models.JSONField(
        blank=True,
        null=True,
        help_text="File attachments (photos, invoices, reports)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='maintenance_records_created',
        help_text="User who created this record"
    )
    
    class Meta:
        db_table = 'asset_maintenance_records'
        verbose_name = 'Asset Maintenance Record'
        verbose_name_plural = 'Asset Maintenance Records'
        ordering = ['-maintenance_date']
        indexes = [
            models.Index(fields=['asset', '-maintenance_date']),
            models.Index(fields=['maintenance_type', '-maintenance_date']),
            models.Index(fields=['next_maintenance_date']),
        ]
    
    def __str__(self):
        return f"{self.asset.asset_tag} - {self.maintenance_type} ({self.maintenance_date})"
    
    def save(self, *args, **kwargs):
        """Update asset's last/next maintenance dates."""
        super().save(*args, **kwargs)
        
        # Update asset
        self.asset.last_maintenance_date = self.maintenance_date
        if self.next_maintenance_date:
            self.asset.next_maintenance_date = self.next_maintenance_date
        else:
            self.asset.schedule_maintenance()
        
        self.asset.save()


# ============================================================================
# ASSET DEPRECIATION SCHEDULE
# ============================================================================

class AssetDepreciationSchedule(models.Model):
    """
    Monthly depreciation schedule for assets.
    
    Auto-generated for accounting/reporting purposes.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='depreciation_schedule',
        help_text="Asset"
    )
    period_start_date = models.DateField(
        help_text="Depreciation period start"
    )
    period_end_date = models.DateField(
        help_text="Depreciation period end"
    )
    opening_book_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Book value at period start"
    )
    depreciation_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Depreciation for this period"
    )
    closing_book_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Book value at period end"
    )
    is_posted = models.BooleanField(
        default=False,
        help_text="Has this depreciation been posted to accounting?"
    )
    posted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When depreciation was posted"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'asset_depreciation_schedule'
        verbose_name = 'Asset Depreciation Schedule'
        verbose_name_plural = 'Asset Depreciation Schedules'
        ordering = ['asset', 'period_start_date']
        unique_together = ['asset', 'period_start_date']
        indexes = [
            models.Index(fields=['asset', 'period_start_date']),
            models.Index(fields=['is_posted']),
        ]
    
    def __str__(self):
        return f"{self.asset.asset_tag} - {self.period_start_date}"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_asset_from_grn_line(grn_line, location=None):
    """
    Auto-create asset records for serialized items from GRN.
    
    Args:
        grn_line: GRNLine instance
        location: Location for the asset (optional)
    
    Returns:
        Asset instance or None
    """
    if not grn_line.item.is_serialized or not grn_line.serial_no:
        return None
    
    # Check if asset already exists
    if Asset.objects.filter(serial_no=grn_line.serial_no).exists():
        return None
    
    asset = Asset.objects.create(
        item=grn_line.item,
        serial_no=grn_line.serial_no,
        po=grn_line.grn.po,
        grn=grn_line.grn,
        purchase_date=grn_line.grn.grn_date,
        purchase_price=grn_line.unit_price,
        currency=grn_line.grn.currency,
        supplier=grn_line.grn.supplier,
        location=location or grn_line.location,
        current_status='IN_STOCK',
        # Set default depreciation if item is an asset
        depreciation_method='STRAIGHT_LINE' if grn_line.item.is_asset else 'NO_DEPRECIATION',
        useful_life_years=5 if grn_line.item.is_asset else None,  # Default 5 years
    )
    
    return asset


def generate_depreciation_schedule(asset, start_date=None, end_date=None):
    """
    Generate monthly depreciation schedule for an asset.
    
    Args:
        asset: Asset instance
        start_date: Start date (defaults to purchase date)
        end_date: End date (defaults to end of useful life)
    """
    if asset.depreciation_method == 'NO_DEPRECIATION':
        return
    
    if not asset.purchase_date or not asset.useful_life_years:
        return
    
    start = start_date or asset.purchase_date
    end = end_date or (asset.purchase_date + relativedelta(years=asset.useful_life_years))
    
    current_date = start.replace(day=1)  # Start of month
    book_value = asset.purchase_price
    salvage = asset.salvage_value or Decimal('0')
    
    while current_date < end and book_value > salvage:
        period_end = (current_date + relativedelta(months=1)) - relativedelta(days=1)
        
        # Calculate monthly depreciation
        if asset.depreciation_method == 'STRAIGHT_LINE':
            total_depreciation = asset.purchase_price - salvage
            months = asset.useful_life_years * 12
            monthly_depreciation = total_depreciation / Decimal(str(months))
        else:  # DECLINING_BALANCE
            annual_rate = Decimal('2') / Decimal(str(asset.useful_life_years))
            monthly_rate = annual_rate / Decimal('12')
            monthly_depreciation = book_value * monthly_rate
        
        # Don't depreciate below salvage value
        if book_value - monthly_depreciation < salvage:
            monthly_depreciation = book_value - salvage
        
        closing_book_value = book_value - monthly_depreciation
        
        # Create schedule entry
        AssetDepreciationSchedule.objects.get_or_create(
            asset=asset,
            period_start_date=current_date,
            defaults={
                'period_end_date': period_end,
                'opening_book_value': book_value,
                'depreciation_amount': monthly_depreciation,
                'closing_book_value': closing_book_value,
            }
        )
        
        book_value = closing_book_value
        current_date = current_date + relativedelta(months=1)