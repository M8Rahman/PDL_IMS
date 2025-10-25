"""
Inventory Master Data Models
=============================
This module contains:
1. Currency & Exchange Rates
2. Unit of Measurement (UOM)
3. Item Categories
4. Items (with stock control parameters)
5. Item UOM Conversions
6. Suppliers & Item-Supplier mapping
7. Supplier Evaluations
8. Buyers, Styles, Colors, Sizes (RMG specific)
9. Status Master (centralized status management)
"""

import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel
from users.models import User


# ============================================================================
# CURRENCY MODELS
# ============================================================================

class Currency(models.Model):
    """
    Currency master data.
    
    Stores currency information and exchange rates.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    currency_code = models.CharField(
        max_length=3,
        unique=True,
        help_text="ISO 4217 currency code (e.g., BDT, USD, EUR)"
    )
    symbol = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Currency symbol (e.g., ৳, $, €)"
    )
    name = models.CharField(
        max_length=50,
        help_text="Currency name"
    )
    is_base_currency = models.BooleanField(
        default=False,
        help_text="Is this the base currency for the system?"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'currencies'
        verbose_name = 'Currency'
        verbose_name_plural = 'Currencies'
        ordering = ['currency_code']
    
    def __str__(self):
        return f"{self.currency_code} - {self.name}"
    
    def clean(self):
        """Ensure only one base currency exists."""
        super().clean()
        if self.is_base_currency:
            existing_base = Currency.objects.filter(is_base_currency=True).exclude(id=self.id)
            if existing_base.exists():
                raise ValidationError("Only one base currency can be set.")


class ExchangeRate(models.Model):
    """
    Exchange rates between currencies.
    
    Stores historical exchange rates for currency conversion.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name='exchange_rates_from',
        help_text="Source currency"
    )
    to_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name='exchange_rates_to',
        help_text="Target currency"
    )
    rate = models.DecimalField(
        max_digits=15,
        decimal_places=6,
        validators=[MinValueValidator(0)],
        help_text="Exchange rate"
    )
    effective_date = models.DateField(
        help_text="Date from which this rate is effective"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who created this rate"
    )
    
    class Meta:
        db_table = 'exchange_rates'
        verbose_name = 'Exchange Rate'
        verbose_name_plural = 'Exchange Rates'
        unique_together = ['from_currency', 'to_currency', 'effective_date']
        ordering = ['-effective_date']
        indexes = [
            models.Index(fields=['from_currency', 'to_currency', '-effective_date']),
        ]
    
    def __str__(self):
        return f"{self.from_currency.currency_code} → {self.to_currency.currency_code}: {self.rate} ({self.effective_date})"
    
    def clean(self):
        """Validate exchange rate data."""
        super().clean()
        if self.from_currency == self.to_currency:
            raise ValidationError("From and To currencies must be different.")


# ============================================================================
# UNIT OF MEASUREMENT (UOM)
# ============================================================================

class UnitOfMeasurement(models.Model):
    """
    Unit of Measurement master data.
    
    Examples: KG (Kilogram), PCS (Pieces), MTR (Meter), YRD (Yard), ROLL
    """
    
    UOM_TYPES = [
        ('WEIGHT', 'Weight'),
        ('LENGTH', 'Length'),
        ('QUANTITY', 'Quantity'),
        ('VOLUME', 'Volume'),
        ('AREA', 'Area'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uom_code = models.CharField(
        max_length=10,
        unique=True,
        help_text="UOM code (e.g., KG, PCS, MTR)"
    )
    name = models.CharField(
        max_length=50,
        help_text="Full name of UOM"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of UOM"
    )
    uom_type = models.CharField(
        max_length=20,
        choices=UOM_TYPES,
        blank=True,
        null=True,
        help_text="Type of measurement"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'uoms'
        verbose_name = 'Unit of Measurement'
        verbose_name_plural = 'Units of Measurement'
        ordering = ['uom_code']
    
    def __str__(self):
        return f"{self.uom_code} - {self.name}"
    
    def clean(self):
        """Validate UOM data."""
        super().clean()
        if self.uom_code:
            self.uom_code = self.uom_code.upper()


# ============================================================================
# ITEM CATEGORY
# ============================================================================

class ItemCategory(BaseModel):
    """
    Hierarchical item categories.
    
    Examples: Yarn > Cotton Yarn, Accessories > Buttons > Metal Buttons
    """
    
    CATEGORY_TYPES = [
        ('YARN', 'Yarn'),
        ('FABRIC', 'Fabric'),
        ('ACCESSORIES', 'Accessories'),
        ('GENERAL', 'General'),
        ('SPARES', 'Spare Parts'),
        ('IT', 'IT Equipment'),
    ]
    
    parent_category = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='sub_categories',
        help_text="Parent category"
    )
    category_code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique category code"
    )
    name = models.CharField(
        max_length=100,
        help_text="Category name"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Category description"
    )
    category_type = models.CharField(
        max_length=20,
        choices=CATEGORY_TYPES,
        blank=True,
        null=True,
        help_text="Type of category"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Is category active?"
    )
    
    class Meta:
        db_table = 'item_categories'
        verbose_name = 'Item Category'
        verbose_name_plural = 'Item Categories'
        ordering = ['category_code']
    
    def __str__(self):
        return f"{self.category_code} - {self.name}"
    
    def get_full_path(self):
        """Get full category path (e.g., 'Yarn > Cotton Yarn > Carded')."""
        if self.parent_category:
            return f"{self.parent_category.get_full_path()} > {self.name}"
        return self.name


# ============================================================================
# ITEM MODEL
# ============================================================================

class Item(BaseModel):
    """
    Item master data with stock control parameters.
    
    Represents all inventory items (yarn, fabric, accessories, spares, IT equipment, etc.)
    """
    
    VALUATION_METHODS = [
        ('FIFO', 'First In, First Out'),
        ('AVERAGE', 'Weighted Average'),
        ('STANDARD', 'Standard Cost'),
    ]
    
    # Basic Information
    sku = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='SKU',
        help_text="Stock Keeping Unit (unique identifier)"
    )
    item_name = models.CharField(
        max_length=200,
        help_text="Item name"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed description"
    )
    category = models.ForeignKey(
        ItemCategory,
        on_delete=models.PROTECT,
        related_name='items',
        help_text="Item category"
    )
    brand = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Brand name"
    )
    manufacturer = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Manufacturer name"
    )
    default_uom = models.ForeignKey(
        UnitOfMeasurement,
        on_delete=models.PROTECT,
        related_name='items',
        help_text="Default unit of measurement"
    )
    
    # Stock Control Parameters
    reorder_level = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Minimum stock before reorder alert"
    )
    safety_stock = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Buffer stock to prevent shortages"
    )
    min_stock_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Minimum stock quantity"
    )
    max_stock_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Maximum stock quantity"
    )
    lead_time_days = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Lead time in days"
    )
    
    # Attributes
    is_serialized = models.BooleanField(
        default=False,
        help_text="Track by serial number?"
    )
    is_batch_controlled = models.BooleanField(
        default=False,
        help_text="Track by batch/lot number?"
    )
    is_asset = models.BooleanField(
        default=False,
        help_text="Is this a fixed asset?"
    )
    is_consumable = models.BooleanField(
        default=True,
        help_text="Is this a consumable item?"
    )
    shelf_life_days = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Shelf life in days (for expirable items)"
    )
    
    # Valuation
    valuation_method = models.CharField(
        max_length=20,
        choices=VALUATION_METHODS,
        default='FIFO',
        help_text="Stock valuation method"
    )
    last_purchase_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Last purchase price"
    )
    avg_purchase_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Average purchase price"
    )
    standard_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Standard cost"
    )
    
    # Compliance
    hsn_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='HSN Code',
        help_text="Harmonized System Nomenclature code for tax/customs"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Is item active?"
    )
    discontinued_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when item was discontinued"
    )
    
    class Meta:
        db_table = 'items'
        verbose_name = 'Item'
        verbose_name_plural = 'Items'
        ordering = ['sku']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.sku} - {self.item_name}"
    
    def clean(self):
        """Validate item data."""
        super().clean()
        if self.sku:
            self.sku = self.sku.upper()
        
        if self.max_stock_qty and self.max_stock_qty < self.min_stock_qty:
            raise ValidationError("Maximum stock must be greater than minimum stock.")
    
    def get_current_stock(self):
        """Get current stock quantity (placeholder - will be implemented with stock_balance)."""
        # This will be implemented when we create stock_movements and stock_balance
        return 0


# ============================================================================
# ITEM UOM CONVERSION
# ============================================================================

class ItemUOMConversion(models.Model):
    """
    UOM conversions for specific items.
    
    Example: For fabric, 1 ROLL = 40 MTR
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name='uom_conversions',
        help_text="Item"
    )
    from_uom = models.ForeignKey(
        UnitOfMeasurement,
        on_delete=models.PROTECT,
        related_name='conversions_from',
        help_text="From UOM"
    )
    to_uom = models.ForeignKey(
        UnitOfMeasurement,
        on_delete=models.PROTECT,
        related_name='conversions_to',
        help_text="To UOM"
    )
    conversion_factor = models.DecimalField(
        max_digits=15,
        decimal_places=6,
        validators=[MinValueValidator(0.000001)],
        help_text="Conversion factor (e.g., 1 ROLL = 40 MTR, factor = 40)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Is conversion active?"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'item_uom_conversions'
        verbose_name = 'Item UOM Conversion'
        verbose_name_plural = 'Item UOM Conversions'
        unique_together = ['item', 'from_uom', 'to_uom']
    
    def __str__(self):
        return f"{self.item.sku}: 1 {self.from_uom.uom_code} = {self.conversion_factor} {self.to_uom.uom_code}"
    
    def convert(self, quantity):
        """Convert quantity from from_uom to to_uom."""
        return quantity * self.conversion_factor


# ============================================================================
# SUPPLIER MODEL
# ============================================================================

class Supplier(BaseModel):
    """
    Supplier master data.
    
    Stores information about suppliers/vendors.
    """
    
    SUPPLIER_TYPES = [
        ('YARN', 'Yarn Supplier'),
        ('FABRIC', 'Fabric Supplier'),
        ('ACCESSORIES', 'Accessories Supplier'),
        ('GENERAL', 'General Supplier'),
        ('SERVICE', 'Service Provider'),
    ]
    
    supplier_code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique supplier code"
    )
    name = models.CharField(
        max_length=200,
        help_text="Supplier name"
    )
    contact_person = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Contact person name"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Phone number"
    )
    email = models.EmailField(
        blank=True,
        null=True,
        help_text="Email address"
    )
    address = models.TextField(
        blank=True,
        null=True,
        help_text="Address"
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="City"
    )
    country = models.CharField(
        max_length=50,
        default='Bangladesh',
        help_text="Country"
    )
    tin_vat = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='TIN/VAT',
        help_text="Tax Identification Number / VAT Number"
    )
    payment_terms = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Payment terms (e.g., '30 days', 'Advance', 'LC')"
    )
    credit_limit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Credit limit"
    )
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Default currency"
    )
    supplier_type = models.CharField(
        max_length=50,
        choices=SUPPLIER_TYPES,
        blank=True,
        null=True,
        help_text="Type of supplier"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Is supplier active?"
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Supplier rating (0-5)"
    )
    
    class Meta:
        db_table = 'suppliers'
        verbose_name = 'Supplier'
        verbose_name_plural = 'Suppliers'
        ordering = ['supplier_code']
        indexes = [
            models.Index(fields=['supplier_code']),
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.supplier_code} - {self.name}"


# ============================================================================
# ITEM-SUPPLIER MAPPING
# ============================================================================

class ItemSupplier(models.Model):
    """
    Link items to their suppliers with pricing and lead time info.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name='item_suppliers',
        help_text="Item"
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name='supplied_items',
        help_text="Supplier"
    )
    lead_time_days = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Lead time in days"
    )
    min_order_qty = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Minimum order quantity"
    )
    last_purchase_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Last purchase price"
    )
    last_purchase_date = models.DateField(
        null=True,
        blank=True,
        help_text="Last purchase date"
    )
    is_preferred = models.BooleanField(
        default=False,
        help_text="Is this the preferred supplier for this item?"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'item_suppliers'
        verbose_name = 'Item Supplier'
        verbose_name_plural = 'Item Suppliers'
        unique_together = ['item', 'supplier']
    
    def __str__(self):
        return f"{self.item.sku} - {self.supplier.supplier_code}"


# ============================================================================
# SUPPLIER EVALUATION
# ============================================================================

class SupplierEvaluation(models.Model):
    """
    Periodic supplier performance evaluations.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name='evaluations',
        help_text="Supplier"
    )
    evaluation_date = models.DateField(
        help_text="Evaluation date"
    )
    on_time_delivery_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="On-time delivery score (0-5)"
    )
    quality_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Quality score (0-5)"
    )
    price_competitiveness_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Price competitiveness score (0-5)"
    )
    communication_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Communication score (0-5)"
    )
    overall_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Overall rating (0-5)"
    )
    remarks = models.TextField(
        blank=True,
        null=True,
        help_text="Evaluation remarks"
    )
    evaluated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Evaluator"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'supplier_evaluations'
        verbose_name = 'Supplier Evaluation'
        verbose_name_plural = 'Supplier Evaluations'
        ordering = ['-evaluation_date']
    
    def __str__(self):
        return f"{self.supplier.name} - {self.evaluation_date} (Rating: {self.overall_rating})"
    
    def save(self, *args, **kwargs):
        """Calculate overall rating as average of all scores."""
        if not self.overall_rating:
            scores = [
                self.on_time_delivery_score,
                self.quality_score,
                self.price_competitiveness_score,
                self.communication_score
            ]
            self.overall_rating = sum(scores) / len(scores)
        super().save(*args, **kwargs)

# ============================================================================
# RMG SPECIFIC MODELS
# ============================================================================

class Buyer(BaseModel):
    """
    Buyer/Customer master data (for RMG industry).
    
    Stores information about garment buyers.
    """
    buyer_code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique buyer code"
    )
    name = models.CharField(
        max_length=200,
        help_text="Buyer name"
    )
    contact_person = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Contact person"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Phone number"
    )
    email = models.EmailField(
        blank=True,
        null=True,
        help_text="Email address"
    )
    address = models.TextField(
        blank=True,
        null=True,
        help_text="Address"
    )
    country = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Country"
    )
    payment_terms = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Payment terms"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Is buyer active?"
    )
    
    class Meta:
        db_table = 'buyers'
        verbose_name = 'Buyer'
        verbose_name_plural = 'Buyers'
        ordering = ['buyer_code']
        indexes = [
            models.Index(fields=['buyer_code']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return f"{self.buyer_code} - {self.name}"


class Style(BaseModel):
    """
    Garment styles for buyers.
    
    Each buyer has multiple styles (e.g., T-Shirt Style A, Trouser Style B).
    """
    buyer = models.ForeignKey(
        Buyer,
        on_delete=models.PROTECT,
        related_name='styles',
        help_text="Buyer"
    )
    style_code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique style code"
    )
    style_name = models.CharField(
        max_length=200,
        help_text="Style name"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Style description"
    )
    season = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Season (e.g., 'Spring 2025', 'Winter 2024')"
    )
    garment_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Garment type (T-Shirt, Trouser, Jacket, etc.)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Is style active?"
    )
    
    class Meta:
        db_table = 'styles'
        verbose_name = 'Style'
        verbose_name_plural = 'Styles'
        ordering = ['style_code']
        indexes = [
            models.Index(fields=['buyer', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.style_code} - {self.style_name}"


class Color(models.Model):
    """
    Color master data for garments.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    color_code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique color code"
    )
    color_name = models.CharField(
        max_length=100,
        help_text="Color name (e.g., 'Navy Blue', 'Red')"
    )
    pantone_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Pantone color code"
    )
    hex_code = models.CharField(
        max_length=7,
        blank=True,
        null=True,
        help_text="Hex color code (e.g., #FF5733)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'colors'
        verbose_name = 'Color'
        verbose_name_plural = 'Colors'
        ordering = ['color_name']
    
    def __str__(self):
        return f"{self.color_code} - {self.color_name}"


class Size(models.Model):
    """
    Size master data for garments.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    size_code = models.CharField(
        max_length=10,
        unique=True,
        help_text="Size code (e.g., XS, S, M, L, XL, XXL)"
    )
    description = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Size description"
    )
    sequence = models.IntegerField(
        default=0,
        help_text="Sequence for sorting (1=XS, 2=S, 3=M, etc.)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'sizes'
        verbose_name = 'Size'
        verbose_name_plural = 'Sizes'
        ordering = ['sequence', 'size_code']
    
    def __str__(self):
        return self.size_code


# ============================================================================
# STATUS MASTER (Centralized Status Management)
# ============================================================================

class StatusMaster(BaseModel):
    """
    Centralized status management for all entities.
    
    Replaces hardcoded status values with configurable statuses.
    """
    
    ENTITY_TYPES = [
        ('PR', 'Purchase Request'),
        ('PO', 'Purchase Order'),
        ('GRN', 'Goods Received Note'),
        ('TRANSFER', 'Stock Transfer'),
        ('ISSUE', 'Stock Issue'),
        ('ADJUSTMENT', 'Inventory Adjustment'),
        ('WORK_ORDER', 'Work Order'),
    ]
    
    entity_type = models.CharField(
        max_length=50,
        choices=ENTITY_TYPES,
        help_text="Entity type this status applies to"
    )
    status_code = models.CharField(
        max_length=50,
        help_text="Status code (e.g., 'DRAFT', 'APPROVED')"
    )
    status_label = models.CharField(
        max_length=100,
        help_text="Human-readable status label"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Status description"
    )
    sequence = models.IntegerField(
        default=0,
        help_text="Display sequence in workflows"
    )
    color_code = models.CharField(
        max_length=7,
        blank=True,
        null=True,
        help_text="Hex color code for UI (e.g., #28a745)"
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Icon identifier for UI"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Is status active?"
    )
    is_system_status = models.BooleanField(
        default=False,
        help_text="System status (cannot be modified/deleted)"
    )
    
    class Meta:
        db_table = 'status_master'
        verbose_name = 'Status'
        verbose_name_plural = 'Statuses'
        unique_together = ['entity_type', 'status_code']
        ordering = ['entity_type', 'sequence']
        indexes = [
            models.Index(fields=['entity_type', 'status_code']),
        ]
    
    def __str__(self):
        return f"{self.entity_type} - {self.status_label}"