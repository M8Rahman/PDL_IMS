"""
Core Admin Configuration
========================
Register core models with Django admin interface.
"""

from django.contrib import admin
from .models import Company, Factory, Department, Location


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'base_currency_code', 'timezone', 'created_at']
    search_fields = ['name', 'email']
    list_filter = ['base_currency_code', 'created_at']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Factory)
class FactoryAdmin(admin.ModelAdmin):
    list_display = ['factory_code', 'name', 'company', 'is_active', 'created_at']
    list_filter = ['company', 'is_active', 'created_at']
    search_fields = ['factory_code', 'name', 'address']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['dept_code', 'name', 'factory', 'is_active', 'created_at']
    list_filter = ['factory', 'is_active', 'created_at']
    search_fields = ['dept_code', 'name', 'cost_center_code']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['location_code', 'name', 'location_type', 'factory', 'depth_level', 'is_active']
    list_filter = ['factory', 'location_type', 'is_active']
    search_fields = ['location_code', 'name', 'path']
    readonly_fields = ['id', 'path', 'depth_level', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('location_code', 'name', 'location_type', 'factory')
        }),
        ('Hierarchy', {
            'fields': ('parent_location', 'path', 'depth_level')
        }),
        ('Capacity', {
            'fields': ('capacity_qty', 'capacity_uom')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Audit', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )