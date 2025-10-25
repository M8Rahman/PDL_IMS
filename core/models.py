"""
Core Models - Base Classes and Organizational Structure
========================================================
This module contains:
1. BaseModel - Abstract base class for all models
2. Company - Top-level organization
3. Factory - Manufacturing units
4. Department - Organizational departments
5. Location - Hierarchical storage locations
"""

import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


# ============================================================================
# ABSTRACT BASE MODEL
# ============================================================================

class BaseModel(models.Model):
    """
    Abstract base model that provides common fields for all models.
    
    Fields:
    - UUID as primary key (more secure than auto-increment)
    - created_at, updated_at (automatic timestamps)
    - created_by, updated_by (user tracking)
    - deleted_at, deleted_by (soft delete support)
    
    Usage:
        class MyModel(BaseModel):
            # Your fields here
            pass
    """
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text="Unique identifier (UUID)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when record was last updated"
    )
    
    # User tracking (nullable for system-created records)
    created_by = models.UUIDField(
        null=True,
        blank=True,
        help_text="User who created this record"
    )
    updated_by = models.UUIDField(
        null=True,
        blank=True,
        help_text="User who last updated this record"
    )
    
    # Soft delete fields
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when record was soft-deleted"
    )
    deleted_by = models.UUIDField(
        null=True,
        blank=True,
        help_text="User who deleted this record"
    )
    
    class Meta:
        abstract = True  # This model won't create a database table
        ordering = ['-created_at']  # Default ordering by newest first
    
    def soft_delete(self, user_id=None):
        """
        Soft delete the record (marks as deleted without removing from DB).
        
        Args:
            user_id: UUID of user performing the deletion
        """
        from django.utils import timezone
        self.deleted_at = timezone.now()
        self.deleted_by = user_id
        self.save(update_fields=['deleted_at', 'deleted_by'])
    
    def restore(self):
        """Restore a soft-deleted record."""
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['deleted_at', 'deleted_by'])
    
    @property
    def is_deleted(self):
        """Check if record is soft-deleted."""
        return self.deleted_at is not None


# ============================================================================
# COMPANY MODEL
# ============================================================================

class Company(BaseModel):
    """
    Represents the top-level organization (e.g., PDL Group).
    
    A company can have multiple factories.
    """
    name = models.CharField(
        max_length=200,
        help_text="Company name"
    )
    address = models.TextField(
        blank=True,
        null=True,
        help_text="Company address"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Contact phone number"
    )
    email = models.EmailField(
        blank=True,
        null=True,
        help_text="Contact email address"
    )
    tin_vat = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="TIN/VAT Number",
        help_text="Tax Identification Number / VAT Number"
    )
    timezone = models.CharField(
        max_length=50,
        default='Asia/Dhaka',
        help_text="Company timezone"
    )
    base_currency_code = models.CharField(
        max_length=3,
        default='BDT',
        help_text="Base currency code (ISO 4217)"
    )
    
    class Meta:
        db_table = 'companies'
        verbose_name = 'Company'
        verbose_name_plural = 'Companies'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_active_factories(self):
        """Get all active factories for this company."""
        return self.factories.filter(is_active=True, deleted_at__isnull=True)


# ============================================================================
# FACTORY MODEL
# ============================================================================

class Factory(BaseModel):
    """
    Represents a manufacturing unit/factory.
    
    Each factory belongs to one company and can have multiple departments.
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,  # Prevent deletion if factories exist
        related_name='factories',
        help_text="Parent company"
    )
    factory_code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique factory code (e.g., 'PDL-F1')"
    )
    name = models.CharField(
        max_length=200,
        help_text="Factory name"
    )
    address = models.TextField(
        blank=True,
        null=True,
        help_text="Factory address"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Contact phone number"
    )
    email = models.EmailField(
        blank=True,
        null=True,
        help_text="Contact email address"
    )
    manager_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Factory manager name"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Is factory currently active?"
    )
    
    class Meta:
        db_table = 'factories'
        verbose_name = 'Factory'
        verbose_name_plural = 'Factories'
        ordering = ['factory_code']
        indexes = [
            models.Index(fields=['company', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.factory_code} - {self.name}"
    
    def clean(self):
        """Validate factory data."""
        super().clean()
        if self.factory_code:
            self.factory_code = self.factory_code.upper()


# ============================================================================
# DEPARTMENT MODEL
# ============================================================================

class Department(BaseModel):
    """
    Represents organizational departments within a factory.
    
    Examples: Production, QC, IT, Admin, Warehouse, etc.
    Note: manager_id will be set after User model is created.
    """
    factory = models.ForeignKey(
        Factory,
        on_delete=models.PROTECT,
        related_name='departments',
        help_text="Factory this department belongs to"
    )
    dept_code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique department code (e.g., 'IT-001')"
    )
    name = models.CharField(
        max_length=100,
        help_text="Department name"
    )
    cost_center_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Cost center code for accounting"
    )
    # manager_id will be added as FK to User model later
    manager_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Department manager (User ID)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Is department currently active?"
    )
    
    class Meta:
        db_table = 'departments'
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'
        ordering = ['dept_code']
        indexes = [
            models.Index(fields=['factory', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.dept_code} - {self.name}"
    
    def clean(self):
        """Validate department data."""
        super().clean()
        if self.dept_code:
            self.dept_code = self.dept_code.upper()


# ============================================================================
# LOCATION MODEL (Hierarchical Storage)
# ============================================================================

class Location(BaseModel):
    """
    Hierarchical storage location model.
    
    Structure: Warehouse > Building > Floor > Room > Rack > Bin
    
    Example path: 'WH1/B1/F2/RM05/RK03/BN12'
    """
    
    LOCATION_TYPES = [
        ('WAREHOUSE', 'Warehouse'),
        ('BUILDING', 'Building'),
        ('FLOOR', 'Floor'),
        ('ROOM', 'Room'),
        ('RACK', 'Rack'),
        ('BIN', 'Bin'),
    ]
    
    factory = models.ForeignKey(
        Factory,
        on_delete=models.PROTECT,
        related_name='locations',
        help_text="Factory this location belongs to"
    )
    parent_location = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='child_locations',
        help_text="Parent location in hierarchy"
    )
    location_code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique location code"
    )
    name = models.CharField(
        max_length=200,
        help_text="Location name"
    )
    location_type = models.CharField(
        max_length=20,
        choices=LOCATION_TYPES,
        help_text="Type of location"
    )
    path = models.TextField(
        blank=True,
        null=True,
        help_text="Full hierarchical path (e.g., 'WH1/B1/F2/RM05')"
    )
    capacity_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Storage capacity quantity"
    )
    capacity_uom = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Unit of measurement for capacity"
    )
    depth_level = models.IntegerField(
        default=0,
        help_text="Depth in hierarchy (0 = root)"
    )
    max_depth = models.IntegerField(
        default=5,
        help_text="Maximum allowed depth"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Is location currently active?"
    )
    
    class Meta:
        db_table = 'locations'
        verbose_name = 'Location'
        verbose_name_plural = 'Locations'
        ordering = ['path', 'location_code']
        indexes = [
            models.Index(fields=['factory', 'is_active']),
            models.Index(fields=['parent_location']),
            models.Index(fields=['path']),
        ]
    
    def __str__(self):
        return f"{self.location_code} - {self.name}"
    
    def clean(self):
        """
        Validate location data.
        - Check for circular references
        - Validate depth level
        - Generate path
        """
        super().clean()
        
        # Prevent self-referencing
        if self.parent_location and self.parent_location.id == self.id:
            raise ValidationError("Location cannot be its own parent.")
        
        # Calculate and validate depth
        self.depth_level = self._calculate_depth()
        if self.depth_level > 5:
            raise ValidationError("Location hierarchy cannot exceed 5 levels.")
        
        # Generate path
        self.path = self._generate_path()
    
    def _calculate_depth(self):
        """Calculate depth level in hierarchy."""
        if not self.parent_location:
            return 0
        
        depth = 0
        current = self.parent_location
        visited = {self.id}  # Track visited to prevent infinite loops
        
        while current and depth < 10:  # Safety limit
            if current.id in visited:
                raise ValidationError("Circular reference detected in location hierarchy.")
            visited.add(current.id)
            depth += 1
            current = current.parent_location
        
        return depth
    
    def _generate_path(self):
        """Generate full hierarchical path."""
        if not self.parent_location:
            return self.location_code
        
        parent_path = self.parent_location.path or self.parent_location.location_code
        return f"{parent_path}/{self.location_code}"
    
    def save(self, *args, **kwargs):
        """Override save to ensure clean is called."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_children(self):
        """Get all child locations."""
        return self.child_locations.filter(is_active=True, deleted_at__isnull=True)
    
    def get_full_hierarchy(self):
        """Get full hierarchy as list (root to this location)."""
        hierarchy = [self]
        current = self.parent_location
        
        while current:
            hierarchy.insert(0, current)
            current = current.parent_location
        
        return hierarchy