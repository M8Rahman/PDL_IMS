"""
Inventory Admin Configuration
==============================
Register inventory models with Django admin interface.
"""

from django.contrib import admin
from .models import (
    Currency, ExchangeRate, UnitOfMeasurement, ItemCategory, Item,
    ItemUOMConversion, Supplier, ItemSupplier, SupplierEvaluation,
    Buyer, Style, Color, Size, StatusMaster
)


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ['currency_code', 'name', 'symbol', 'is_base_currency']
    list_filter = ['is_base_currency']
    search_fields = ['currency_code', 'name']


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ['from_currency', 'to_currency', 'rate', 'effective_date', 'created_by']
    list_filter = ['from_currency', 'to_currency', 'effective_date']
    search_fields = ['from_currency__currency_code', 'to_currency__currency_code']
    date_hierarchy = 'effective_date'


@admin.register(UnitOfMeasurement)
class UnitOfMeasurementAdmin(admin.ModelAdmin):
    list_display = ['uom_code', 'name', 'uom_type']
    list_filter = ['uom_type']
    search_fields = ['uom_code', 'name']


@admin.register(ItemCategory)
class ItemCategoryAdmin(admin.ModelAdmin):
    list_display = ['category_code', 'name', 'parent_category', 'category_type', 'is_active']
    list_filter = ['category_type', 'is_active']
    search_fields = ['category_code', 'name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['sku', 'item_name', 'category', 'default_uom', 'is_active', 'is_serialized', 'is_batch_controlled']
    list_filter = ['category', 'is_active', 'is_serialized', 'is_batch_controlled', 'is_asset', 'valuation_method']
    search_fields = ['sku', 'item_name', 'description', 'brand', 'manufacturer']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('sku', 'item_name', 'description', 'category', 'brand', 'manufacturer', 'default_uom')
        }),
        ('Stock Control', {
            'fields': ('reorder_level', 'safety_stock', 'min_stock_qty', 'max_stock_qty', 'lead_time_days')
        }),
        ('Attributes', {
            'fields': ('is_serialized', 'is_batch_controlled', 'is_asset', 'is_consumable', 'shelf_life_days')
        }),
        ('Valuation', {
            'fields': ('valuation_method', 'last_purchase_price', 'avg_purchase_price', 'standard_cost')
        }),
        ('Compliance', {
            'fields': ('hsn_code',)
        }),
        ('Status', {
            'fields': ('is_active', 'discontinued_date')
        }),
        ('Audit', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ItemUOMConversion)
class ItemUOMConversionAdmin(admin.ModelAdmin):
    list_display = ['item', 'from_uom', 'to_uom', 'conversion_factor', 'is_active']
    list_filter = ['is_active']
    search_fields = ['item__sku', 'item__item_name']


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['supplier_code', 'name', 'supplier_type', 'country', 'rating', 'is_active']
    list_filter = ['supplier_type', 'country', 'is_active']
    search_fields = ['supplier_code', 'name', 'contact_person', 'email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('supplier_code', 'name', 'supplier_type')
        }),
        ('Contact Information', {
            'fields': ('contact_person', 'phone', 'email', 'address', 'city', 'country')
        }),
        ('Financial', {
            'fields': ('tin_vat', 'payment_terms', 'credit_limit', 'currency')
        }),
        ('Rating & Status', {
            'fields': ('rating', 'is_active')
        }),
        ('Audit', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ItemSupplier)
class ItemSupplierAdmin(admin.ModelAdmin):
    list_display = ['item', 'supplier', 'lead_time_days', 'last_purchase_price', 'is_preferred']
    list_filter = ['is_preferred', 'supplier']
    search_fields = ['item__sku', 'item__item_name', 'supplier__name']


@admin.register(SupplierEvaluation)
class SupplierEvaluationAdmin(admin.ModelAdmin):
    list_display = ['supplier', 'evaluation_date', 'overall_rating', 'evaluated_by']
    list_filter = ['evaluation_date', 'supplier']
    search_fields = ['supplier__name', 'remarks']
    date_hierarchy = 'evaluation_date'


@admin.register(Buyer)
class BuyerAdmin(admin.ModelAdmin):
    list_display = ['buyer_code', 'name', 'country', 'is_active']
    list_filter = ['country', 'is_active']
    search_fields = ['buyer_code', 'name', 'contact_person']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Style)
class StyleAdmin(admin.ModelAdmin):
    list_display = ['style_code', 'style_name', 'buyer', 'season', 'garment_type', 'is_active']
    list_filter = ['buyer', 'season', 'garment_type', 'is_active']
    search_fields = ['style_code', 'style_name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ['color_code', 'color_name', 'pantone_code', 'hex_code']
    search_fields = ['color_code', 'color_name', 'pantone_code']


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ['size_code', 'description', 'sequence']
    ordering = ['sequence']


@admin.register(StatusMaster)
class StatusMasterAdmin(admin.ModelAdmin):
    list_display = ['entity_type', 'status_code', 'status_label', 'sequence', 'color_code', 'is_active', 'is_system_status']
    list_filter = ['entity_type', 'is_active', 'is_system_status']
    search_fields = ['status_code', 'status_label']
    readonly_fields = ['id', 'created_at', 'updated_at']