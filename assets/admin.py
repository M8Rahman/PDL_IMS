"""
Asset Management Admin Configuration
====================================
Register asset models with Django admin interface.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    Asset, AssetAssignmentHistory, AssetMaintenanceRecord,
    AssetDepreciationSchedule
)


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = [
        'asset_tag', 'item', 'serial_no', 'current_status',
        'assigned_to_user', 'location', 'warranty_status_badge',
        'maintenance_status_badge', 'current_book_value'
    ]
    list_filter = [
        'current_status', 'item__category', 'depreciation_method',
        'is_active', 'created_at'
    ]
    search_fields = [
        'asset_tag', 'serial_no', 'item__sku', 'item__item_name',
        'model', 'manufacturer', 'assigned_to_user__full_name'
    ]
    readonly_fields = [
        'id', 'asset_tag', 'accumulated_depreciation', 'current_book_value',
        'warranty_days_remaining', 'is_under_warranty', 'is_maintenance_due',
        'created_at', 'updated_at'
    ]
    date_hierarchy = 'purchase_date'
    
    fieldsets = (
        ('Asset Information', {
            'fields': (
                'item', 'asset_tag', 'serial_no', 'model', 'manufacturer'
            )
        }),
        ('IT-Specific (Optional)', {
            'fields': ('mac_address', 'imei'),
            'classes': ('collapse',)
        }),
        ('Purchase Information', {
            'fields': (
                'po', 'grn', 'purchase_date', 'purchase_price', 'currency',
                'supplier', 'invoice_number'
            )
        }),
        ('Warranty', {
            'fields': (
                'warranty_start_date', 'warranty_end_date', 'warranty_terms',
                'is_under_warranty', 'warranty_days_remaining'
            )
        }),
        ('Current Assignment', {
            'fields': (
                'current_status', 'assigned_to_user', 'assigned_to_department',
                'assigned_at', 'location'
            )
        }),
        ('Depreciation', {
            'fields': (
                'depreciation_method', 'useful_life_years', 'salvage_value',
                'accumulated_depreciation', 'current_book_value'
            )
        }),
        ('Maintenance', {
            'fields': (
                'last_maintenance_date', 'next_maintenance_date',
                'maintenance_frequency_days', 'is_maintenance_due'
            )
        }),
        ('Disposal', {
            'fields': ('disposal_date', 'disposal_reason', 'disposal_value'),
            'classes': ('collapse',)
        }),
        ('Software License', {
            'fields': ('license_key', 'license_expiry_date'),
            'classes': ('collapse',)
        }),
        ('Additional', {
            'fields': ('attachments', 'notes', 'is_active')
        }),
        ('Audit', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_in_stock', 'mark_as_in_repair', 'schedule_maintenance']
    
    def warranty_status_badge(self, obj):
        """Display warranty status with color badge."""
        if obj.is_under_warranty:
            days = obj.warranty_days_remaining
            if days > 90:
                color = 'green'
            elif days > 30:
                color = 'orange'
            else:
                color = 'red'
            return format_html(
                '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">'
                'Under Warranty ({} days)</span>',
                color, days
            )
        return format_html(
            '<span style="background-color: gray; color: white; padding: 3px 10px; border-radius: 3px;">'
            'No Warranty</span>'
        )
    warranty_status_badge.short_description = 'Warranty'
    
    def maintenance_status_badge(self, obj):
        """Display maintenance status with color badge."""
        if obj.is_maintenance_due:
            return format_html(
                '<span style="background-color: red; color: white; padding: 3px 10px; border-radius: 3px;">'
                '⚠ Due: {}</span>',
                obj.next_maintenance_date
            )
        elif obj.next_maintenance_date:
            return format_html(
                '<span style="background-color: green; color: white; padding: 3px 10px; border-radius: 3px;">'
                'Next: {}</span>',
                obj.next_maintenance_date
            )
        return format_html(
            '<span style="background-color: gray; color: white; padding: 3px 10px; border-radius: 3px;">'
            'Not Scheduled</span>'
        )
    maintenance_status_badge.short_description = 'Maintenance'
    
    def mark_as_in_stock(self, request, queryset):
        """Bulk action to mark assets as in stock."""
        count = queryset.update(current_status='IN_STOCK')
        self.message_user(request, f'{count} asset(s) marked as in stock.')
    mark_as_in_stock.short_description = 'Mark as In Stock'
    
    def mark_as_in_repair(self, request, queryset):
        """Bulk action to mark assets as in repair."""
        count = queryset.update(current_status='IN_REPAIR')
        self.message_user(request, f'{count} asset(s) marked as in repair.')
    mark_as_in_repair.short_description = 'Mark as In Repair'
    
    def schedule_maintenance(self, request, queryset):
        """Bulk action to schedule maintenance."""
        count = 0
        for asset in queryset:
            if asset.maintenance_frequency_days:
                asset.schedule_maintenance()
                count += 1
        self.message_user(request, f'Maintenance scheduled for {count} asset(s).')
    schedule_maintenance.short_description = 'Schedule Maintenance'


@admin.register(AssetAssignmentHistory)
class AssetAssignmentHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'asset', 'assignment_type', 'from_user', 'to_user',
        'assigned_at', 'returned_at', 'return_condition'
    ]
    list_filter = [
        'assignment_type', 'return_condition', 'assigned_at'
    ]
    search_fields = [
        'asset__asset_tag', 'asset__serial_no',
        'from_user__full_name', 'to_user__full_name'
    ]
    readonly_fields = ['id', 'assigned_at', 'created_at']
    date_hierarchy = 'assigned_at'
    
    fieldsets = (
        ('Asset & Type', {
            'fields': ('asset', 'assignment_type')
        }),
        ('From', {
            'fields': ('from_user', 'from_department', 'from_location')
        }),
        ('To', {
            'fields': ('to_user', 'to_department', 'to_location')
        }),
        ('Assignment Details', {
            'fields': ('assigned_by', 'assigned_at')
        }),
        ('Return Details', {
            'fields': ('returned_at', 'return_condition')
        }),
        ('Acceptance', {
            'fields': ('acceptance_signature', 'acceptance_date')
        }),
        ('Notes', {
            'fields': ('remarks',)
        }),
        ('Audit', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AssetMaintenanceRecord)
class AssetMaintenanceRecordAdmin(admin.ModelAdmin):
    list_display = [
        'asset', 'maintenance_type', 'maintenance_date',
        'performed_by', 'is_internal', 'cost', 'downtime_hours',
        'next_maintenance_date'
    ]
    list_filter = [
        'maintenance_type', 'is_internal', 'maintenance_date'
    ]
    search_fields = [
        'asset__asset_tag', 'asset__serial_no',
        'performed_by', 'description'
    ]
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'maintenance_date'
    
    fieldsets = (
        ('Asset & Type', {
            'fields': ('asset', 'maintenance_type', 'maintenance_date')
        }),
        ('Performed By', {
            'fields': ('performed_by', 'is_internal', 'vendor')
        }),
        ('Cost', {
            'fields': ('cost', 'currency')
        }),
        ('Work Details', {
            'fields': (
                'description', 'issues_found', 'actions_taken',
                'parts_replaced'
            )
        }),
        ('Scheduling', {
            'fields': ('next_maintenance_date', 'downtime_hours')
        }),
        ('Attachments', {
            'fields': ('attachments',)
        }),
        ('Audit', {
            'fields': ('id', 'created_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Set created_by to current user."""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(AssetDepreciationSchedule)
class AssetDepreciationScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'asset', 'period_start_date', 'period_end_date',
        'opening_book_value', 'depreciation_amount',
        'closing_book_value', 'is_posted', 'posted_at'
    ]
    list_filter = ['is_posted', 'period_start_date']
    search_fields = ['asset__asset_tag', 'asset__serial_no']
    readonly_fields = [
        'id', 'opening_book_value', 'depreciation_amount',
        'closing_book_value', 'created_at'
    ]
    date_hierarchy = 'period_start_date'
    
    fieldsets = (
        ('Asset & Period', {
            'fields': ('asset', 'period_start_date', 'period_end_date')
        }),
        ('Depreciation', {
            'fields': (
                'opening_book_value', 'depreciation_amount',
                'closing_book_value'
            )
        }),
        ('Posting', {
            'fields': ('is_posted', 'posted_at')
        }),
        ('Audit', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_posted']
    
    def mark_as_posted(self, request, queryset):
        """Bulk action to mark depreciation as posted."""
        count = queryset.filter(is_posted=False).update(
            is_posted=True,
            posted_at=timezone.now()
        )
        self.message_user(request, f'{count} depreciation record(s) marked as posted.')
    mark_as_posted.short_description = 'Mark as Posted'


# Inline admin for viewing assignment history on Asset page
class AssetAssignmentHistoryInline(admin.TabularInline):
    model = AssetAssignmentHistory
    extra = 0
    readonly_fields = ['assigned_at', 'returned_at']
    fields = [
        'assignment_type', 'to_user', 'to_department',
        'assigned_at', 'returned_at', 'return_condition'
    ]
    can_delete = False


# Inline admin for viewing maintenance records on Asset page
class AssetMaintenanceRecordInline(admin.TabularInline):
    model = AssetMaintenanceRecord
    extra = 0
    readonly_fields = ['maintenance_date', 'created_at']
    fields = [
        'maintenance_type', 'maintenance_date', 'performed_by',
        'cost', 'next_maintenance_date'
    ]
    can_delete = False