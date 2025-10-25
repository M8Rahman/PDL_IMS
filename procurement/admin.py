"""
Procurement Admin Configuration
================================
Register procurement models with Django admin interface.
"""

from django.contrib import admin
from .models import (
    PurchaseRequest, PurchaseRequestLine,
    PurchaseOrder, PurchaseOrderLine,
    GoodsReceivedNote, GRNLine, QCInspection,
    StockBatch, StockMovement
)


@admin.register(PurchaseRequest)
class PurchaseRequestAdmin(admin.ModelAdmin):
    list_display = ['pr_number', 'requester', 'factory', 'request_type', 'status', 'request_date', 'priority']
    list_filter = ['status', 'request_type', 'priority', 'factory', 'request_date']
    search_fields = ['pr_number', 'requester__username', 'justification']
    readonly_fields = ['id', 'pr_number', 'created_at', 'updated_at']
    date_hierarchy = 'request_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('pr_number', 'requester', 'department', 'factory', 'request_type')
        }),
        ('Schedule', {
            'fields': ('request_date', 'required_by_date', 'priority')
        }),
        ('Details', {
            'fields': ('justification', 'total_estimated_value', 'currency')
        }),
        ('Status', {
            'fields': ('status', 'approved_by', 'approved_at', 'rejection_reason')
        }),
        ('Audit', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PurchaseRequestLine)
class PurchaseRequestLineAdmin(admin.ModelAdmin):
    list_display = ['pr', 'item', 'requested_qty', 'uom', 'estimated_unit_price', 'status']
    list_filter = ['status', 'pr__status']
    search_fields = ['pr__pr_number', 'item__sku', 'item__item_name']


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['po_number', 'supplier', 'factory', 'po_date', 'delivery_date', 'status', 'grand_total', 'currency']
    list_filter = ['status', 'factory', 'supplier', 'po_date']
    search_fields = ['po_number', 'supplier__name']
    readonly_fields = ['id', 'po_number', 'grand_total', 'total_amount_bdt', 'created_at', 'updated_at']
    date_hierarchy = 'po_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('po_number', 'pr', 'supplier', 'factory')
        }),
        ('Schedule', {
            'fields': ('po_date', 'delivery_date', 'payment_terms', 'delivery_address')
        }),
        ('Financial', {
            'fields': ('total_amount', 'currency', 'exchange_rate', 'total_amount_bdt', 
                      'vat_percentage', 'vat_amount', 'tax_percentage', 'tax_amount',
                      'discount_percentage', 'discount_amount', 'grand_total')
        }),
        ('Terms', {
            'fields': ('terms_and_conditions',)
        }),
        ('Status & Approval', {
            'fields': ('status', 'approved_by', 'approved_at')
        }),
        ('Audit', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PurchaseOrderLine)
class PurchaseOrderLineAdmin(admin.ModelAdmin):
    list_display = ['po', 'item', 'ordered_qty', 'received_qty', 'pending_qty', 'uom', 'unit_price', 'status']
    list_filter = ['status', 'po__status']
    search_fields = ['po__po_number', 'item__sku', 'item__item_name']
    readonly_fields = ['pending_qty', 'total_price']


@admin.register(GoodsReceivedNote)
class GoodsReceivedNoteAdmin(admin.ModelAdmin):
    list_display = ['grn_number', 'supplier', 'factory', 'grn_date', 'received_by', 'qc_status', 'status']
    list_filter = ['status', 'qc_status', 'factory', 'supplier', 'grn_date']
    search_fields = ['grn_number', 'supplier__name', 'delivery_challan_no']
    readonly_fields = ['id', 'grn_number', 'received_at', 'created_at', 'updated_at']
    date_hierarchy = 'grn_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('grn_number', 'po', 'supplier', 'factory')
        }),
        ('Receipt Details', {
            'fields': ('grn_date', 'received_by', 'received_at', 'delivery_challan_no', 
                      'delivery_challan_date', 'vehicle_no', 'transporter_name')
        }),
        ('Quality Control', {
            'fields': ('qc_status', 'qc_by', 'qc_at')
        }),
        ('Financial', {
            'fields': ('total_value', 'currency')
        }),
        ('Status', {
            'fields': ('status', 'remarks')
        }),
        ('Audit', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(GRNLine)
class GRNLineAdmin(admin.ModelAdmin):
    list_display = ['grn', 'item', 'received_qty', 'accepted_qty', 'rejected_qty', 'uom', 'qc_status']
    list_filter = ['qc_status', 'grn__status']
    search_fields = ['grn__grn_number', 'item__sku', 'batch_no', 'serial_no']
    readonly_fields = ['total_price']


@admin.register(QCInspection)
class QCInspectionAdmin(admin.ModelAdmin):
    list_display = ['grn', 'inspection_date', 'inspector', 'inspection_type', 'overall_status']
    list_filter = ['overall_status', 'inspection_type', 'inspection_date']
    search_fields = ['grn__grn_number', 'inspector__username']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'inspection_date'


@admin.register(StockBatch)
class StockBatchAdmin(admin.ModelAdmin):
    list_display = ['item', 'batch_no', 'location', 'qty_on_hand', 'qty_allocated', 'qty_available', 'unit_cost', 'status']
    list_filter = ['status', 'location', 'item__category']
    search_fields = ['item__sku', 'item__item_name', 'batch_no', 'lot_no']
    readonly_fields = ['id', 'qty_available', 'total_value', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Item & Location', {
            'fields': ('item', 'batch_no', 'lot_no', 'location', 'grn_line')
        }),
        ('Dates', {
            'fields': ('manufacture_date', 'expiry_date')
        }),
        ('Quantities', {
            'fields': ('qty_received', 'qty_on_hand', 'qty_allocated', 'qty_available', 'uom')
        }),
        ('Valuation', {
            'fields': ('unit_cost', 'total_value')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Audit', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['transaction_date', 'movement_type', 'item', 'quantity', 'uom', 'from_location', 'to_location', 'reference_number', 'is_reversed']
    list_filter = ['movement_type', 'transaction_date', 'is_reversed', 'from_location', 'to_location']
    search_fields = ['item__sku', 'item__item_name', 'reference_number', 'batch__batch_no']
    readonly_fields = ['id', 'total_value', 'fiscal_year', 'fiscal_month', 'transaction_time', 'created_at']
    date_hierarchy = 'transaction_date'
    
    fieldsets = (
        ('Movement Details', {
            'fields': ('item', 'movement_type', 'from_location', 'to_location')
        }),
        ('Reference', {
            'fields': ('reference_type', 'reference_id', 'reference_number')
        }),
        ('Batch/Serial', {
            'fields': ('batch', 'serial_no')
        }),
        ('Quantity & Value', {
            'fields': ('quantity', 'uom', 'unit_cost', 'total_value')
        }),
        ('Transaction', {
            'fields': ('transaction_date', 'transaction_time', 'fiscal_year', 'fiscal_month')
        }),
        ('Approval', {
            'fields': ('created_by', 'approved_by', 'approved_at', 'reason_code', 'remarks')
        }),
        ('Reversal', {
            'fields': ('is_reversed', 'reversed_by', 'reversed_at')
        }),
        ('Audit', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',)
        }),
    )