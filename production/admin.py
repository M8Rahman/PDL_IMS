"""
Production Admin Configuration
===============================
Register production models with Django admin interface.
"""

from django.contrib import admin
from .models import (
    WorkOrder, WorkOrderSizeBreakdown, WorkOrderColorBreakdown,
    WorkOrderYarnRequirement, WorkOrderAccessoryRequirement,
    InternalRequisition, InternalRequisitionLine,
    StockIssue, StockIssueLine,
    StockTransfer, StockTransferLine,
    InventoryAdjustment, InventoryAdjustmentLine,
    StocktakeSession, StocktakeLine
)


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ['wo_number', 'buyer', 'style', 'factory', 'order_date', 'delivery_date', 'order_qty', 'status']
    list_filter = ['status', 'buyer', 'factory', 'order_date']
    search_fields = ['wo_number', 'po_number', 'buyer__name', 'style__style_name']
    readonly_fields = ['id', 'wo_number', 'created_at', 'updated_at']
    date_hierarchy = 'order_date'


@admin.register(InternalRequisition)
class InternalRequisitionAdmin(admin.ModelAdmin):
    list_display = ['requisition_number', 'requester', 'department', 'requisition_date', 'status']
    list_filter = ['status', 'department', 'factory', 'requisition_date']
    search_fields = ['requisition_number', 'requester__username', 'purpose']
    readonly_fields = ['id', 'requisition_number', 'created_at', 'updated_at']
    date_hierarchy = 'requisition_date'


@admin.register(InternalRequisitionLine)
class InternalRequisitionLineAdmin(admin.ModelAdmin):
    list_display = ['requisition', 'item', 'requested_qty', 'issued_qty', 'pending_qty', 'uom', 'status']
    list_filter = ['status']
    search_fields = ['requisition__requisition_number', 'item__sku']
    readonly_fields = ['pending_qty']


@admin.register(StockIssue)
class StockIssueAdmin(admin.ModelAdmin):
    list_display = ['issue_number', 'department', 'issue_date', 'issued_by', 'received_by_name', 'status']
    list_filter = ['status', 'department', 'factory', 'issue_date']
    search_fields = ['issue_number', 'received_by_name']
    readonly_fields = ['id', 'issue_number', 'created_at', 'updated_at']
    date_hierarchy = 'issue_date'


@admin.register(StockIssueLine)
class StockIssueLineAdmin(admin.ModelAdmin):
    list_display = ['issue', 'item', 'issued_qty', 'uom', 'location', 'unit_cost']
    search_fields = ['issue__issue_number', 'item__sku']
    readonly_fields = ['total_cost']


@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display = ['transfer_number', 'from_location', 'to_location', 'transfer_date', 'transfer_type', 'status']
    list_filter = ['status', 'transfer_type', 'transfer_date']
    search_fields = ['transfer_number', 'vehicle_no']
    readonly_fields = ['id', 'transfer_number', 'created_at', 'updated_at']
    date_hierarchy = 'transfer_date'


@admin.register(StockTransferLine)
class StockTransferLineAdmin(admin.ModelAdmin):
    list_display = ['transfer', 'item', 'transferred_qty', 'received_qty', 'uom']
    search_fields = ['transfer__transfer_number', 'item__sku']


@admin.register(InventoryAdjustment)
class InventoryAdjustmentAdmin(admin.ModelAdmin):
    list_display = ['adjustment_number', 'factory', 'adjustment_date', 'adjustment_type', 'total_value_impact', 'status']
    list_filter = ['status', 'adjustment_type', 'factory', 'adjustment_date']
    search_fields = ['adjustment_number', 'reason']
    readonly_fields = ['id', 'adjustment_number', 'created_at', 'updated_at']
    date_hierarchy = 'adjustment_date'


@admin.register(InventoryAdjustmentLine)
class InventoryAdjustmentLineAdmin(admin.ModelAdmin):
    list_display = ['adjustment', 'item', 'location', 'system_qty', 'adjusted_qty', 'variance_qty', 'value_impact']
    search_fields = ['adjustment__adjustment_number', 'item__sku']
    readonly_fields = ['variance_qty', 'value_impact']


@admin.register(StocktakeSession)
class StocktakeSessionAdmin(admin.ModelAdmin):
    list_display = ['stocktake_number', 'factory', 'stocktake_type', 'start_date', 'end_date', 'status']
    list_filter = ['status', 'stocktake_type', 'factory', 'start_date']
    search_fields = ['stocktake_number']
    readonly_fields = ['id', 'stocktake_number', 'created_at', 'updated_at']
    date_hierarchy = 'start_date'


@admin.register(StocktakeLine)
class StocktakeLineAdmin(admin.ModelAdmin):
    list_display = ['stocktake', 'item', 'location', 'system_qty', 'counted_qty', 'variance_qty', 'status']
    list_filter = ['status', 'location']
    search_fields = ['stocktake__stocktake_number', 'item__sku']
    readonly_fields = ['variance_qty']