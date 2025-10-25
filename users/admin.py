"""
Users Admin Configuration
=========================
Register user management models with Django admin interface.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Role, Permission, UserRole, RolePermission,
    StoreType, UserStoreAccess, UserSession
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'full_name', 'factory', 'department', 'is_active', 'is_staff']
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'factory', 'department']
    search_fields = ['username', 'email', 'full_name', 'employee_id']
    ordering = ['username']
    
    fieldsets = (
        ('Authentication', {
            'fields': ('username', 'email', 'password')
        }),
        ('Personal Information', {
            'fields': ('full_name', 'employee_id', 'phone')
        }),
        ('Organization', {
            'fields': ('factory', 'department')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'must_change_password')
        }),
        ('Login Information', {
            'fields': ('last_login_at', 'last_login_ip')
        }),
        ('Audit', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'full_name', 'factory'),
        }),
    )
    
    readonly_fields = ['id', 'last_login_at', 'last_login_ip', 'created_at', 'updated_at']


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['role_name', 'is_system_role', 'created_at']
    search_fields = ['role_name', 'description']
    list_filter = ['is_system_role', 'created_at']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['permission_key', 'module', 'module_code', 'requires_approval']
    list_filter = ['module', 'requires_approval']
    search_fields = ['permission_key', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'assigned_by', 'assigned_at']
    list_filter = ['role', 'assigned_at']
    search_fields = ['user__username', 'role__role_name']
    readonly_fields = ['id', 'assigned_at']


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ['role', 'permission']
    list_filter = ['role']
    search_fields = ['role__role_name', 'permission__permission_key']


@admin.register(StoreType)
class StoreTypeAdmin(admin.ModelAdmin):
    list_display = ['store_code', 'store_name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['store_code', 'store_name']
    readonly_fields = ['id', 'created_at']


@admin.register(UserStoreAccess)
class UserStoreAccessAdmin(admin.ModelAdmin):
    list_display = ['user', 'store_type', 'factory', 'can_view', 'can_create', 'can_approve']
    list_filter = ['store_type', 'factory', 'can_view', 'can_create', 'can_approve']
    search_fields = ['user__username', 'store_type__store_name']
    readonly_fields = ['id', 'assigned_at']


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'ip_address', 'login_at', 'logout_at', 'is_active']
    list_filter = ['is_active', 'login_at']
    search_fields = ['user__username', 'ip_address']
    readonly_fields = ['id', 'login_at', 'last_activity_at']