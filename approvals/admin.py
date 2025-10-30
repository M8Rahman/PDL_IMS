"""
Approval Workflow Admin Configuration
======================================
Register approval models with Django admin interface.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    ApprovalWorkflow, ApprovalWorkflowStep,
    Approval, ApprovalHistory
)


class ApprovalWorkflowStepInline(admin.TabularInline):
    """Inline for workflow steps."""
    model = ApprovalWorkflowStep
    extra = 1
    fields = [
        'step_sequence', 'step_name', 'approver_role', 'approver_user',
        'is_mandatory', 'timeout_hours'
    ]
    ordering = ['step_sequence']


@admin.register(ApprovalWorkflow)
class ApprovalWorkflowAdmin(admin.ModelAdmin):
    list_display = [
        'workflow_name', 'entity_type', 'factory', 'is_default',
        'value_range', 'step_count', 'is_active'
    ]
    list_filter = ['entity_type', 'is_active', 'is_default', 'factory']
    search_fields = ['workflow_name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [ApprovalWorkflowStepInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('workflow_name', 'entity_type', 'description', 'factory')
        }),
        ('Conditions', {
            'fields': ('min_value', 'max_value')
        }),
        ('Status', {
            'fields': ('is_active', 'is_default')
        }),
        ('Audit', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def value_range(self, obj):
        """Display value range."""
        if obj.min_value and obj.max_value:
            return f"{obj.min_value:,.0f} - {obj.max_value:,.0f}"
        elif obj.min_value:
            return f"≥ {obj.min_value:,.0f}"
        elif obj.max_value:
            return f"≤ {obj.max_value:,.0f}"
        return "All values"
    value_range.short_description = 'Value Range'
    
    def step_count(self, obj):
        """Display number of steps."""
        count = obj.steps.filter(deleted_at__isnull=True).count()
        return format_html('<strong>{}</strong> steps', count)
    step_count.short_description = 'Steps'


@admin.register(ApprovalWorkflowStep)
class ApprovalWorkflowStepAdmin(admin.ModelAdmin):
    list_display = [
        'workflow', 'step_sequence', 'step_name', 'approver_display',
        'is_mandatory', 'timeout_hours', 'is_parallel'
    ]
    list_filter = ['workflow', 'is_mandatory', 'is_parallel']
    search_fields = ['step_name', 'workflow__workflow_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Step Information', {
            'fields': ('workflow', 'step_sequence', 'step_name')
        }),
        ('Approver', {
            'fields': ('approver_role', 'approver_user')
        }),
        ('Configuration', {
            'fields': (
                'is_mandatory', 'is_parallel', 'parallel_group',
                'can_delegate'
            )
        }),
        ('Timeout & Escalation', {
            'fields': ('timeout_hours', 'escalation_role')
        }),
        ('Conditions', {
            'fields': ('conditions',),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def approver_display(self, obj):
        """Display approver role or user."""
        if obj.approver_user:
            return format_html(
                '<span style="color: blue;">👤 {}</span>',
                obj.approver_user.full_name
            )
        elif obj.approver_role:
            return format_html(
                '<span style="color: green;">👥 {}</span>',
                obj.approver_role.role_name
            )
        return "—"
    approver_display.short_description = 'Approver'


class ApprovalHistoryInline(admin.TabularInline):
    """Inline for approval history."""
    model = ApprovalHistory
    extra = 0
    readonly_fields = ['action_date', 'step_sequence', 'action', 'approver_user', 'comments']
    fields = ['action_date', 'step_sequence', 'action', 'approver_user', 'comments']
    can_delete = False
    ordering = ['-action_date']
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Approval)
class ApprovalAdmin(admin.ModelAdmin):
    list_display = [
        'entity_number', 'entity_type', 'requested_by', 'requested_at',
        'current_step_display', 'status_badge', 'pending_approvers'
    ]
    list_filter = ['entity_type', 'status', 'requested_at']
    search_fields = ['entity_number', 'requested_by__username']
    readonly_fields = [
        'id', 'entity_type', 'entity_id', 'requested_by', 'requested_at',
        'completed_at', 'created_at', 'updated_at'
    ]
    inlines = [ApprovalHistoryInline]
    date_hierarchy = 'requested_at'
    
    fieldsets = (
        ('Document Information', {
            'fields': ('entity_type', 'entity_id', 'entity_number')
        }),
        ('Workflow', {
            'fields': ('workflow', 'current_step_sequence')
        }),
        ('Request Details', {
            'fields': ('requested_by', 'requested_at', 'remarks', 'metadata')
        }),
        ('Status', {
            'fields': ('status', 'completed_at')
        }),
        ('Audit', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['cancel_approvals']
    
    def current_step_display(self, obj):
        """Display current step."""
        if obj.current_step_sequence:
            step = obj.get_current_step()
            if step:
                return f"Step {obj.current_step_sequence}: {step.step_name}"
            return f"Step {obj.current_step_sequence}"
        return "—"
    current_step_display.short_description = 'Current Step'
    
    def status_badge(self, obj):
        """Display status with color badge."""
        colors = {
            'PENDING': 'gray',
            'IN_PROGRESS': 'blue',
            'APPROVED': 'green',
            'REJECTED': 'red',
            'CANCELLED': 'gray',
            'ESCALATED': 'orange',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def pending_approvers(self, obj):
        """Display users who can approve."""
        if obj.status not in ['PENDING', 'IN_PROGRESS', 'ESCALATED']:
            return "—"
        
        approvers = obj.get_pending_approvers()
        if not approvers:
            return "No approvers"
        
        names = [a.full_name for a in approvers[:3]]
        if approvers.count() > 3:
            names.append(f"+ {approvers.count() - 3} more")
        
        return format_html('<br>'.join(names))
    pending_approvers.short_description = 'Pending Approvers'
    
    def cancel_approvals(self, request, queryset):
        """Bulk action to cancel approvals."""
        count = 0
        for approval in queryset.filter(status__in=['PENDING', 'IN_PROGRESS']):
            approval.cancel(
                user=request.user,
                reason='Cancelled by admin'
            )
            count += 1
        
        self.message_user(request, f'{count} approval(s) cancelled.')
    cancel_approvals.short_description = 'Cancel selected approvals'


@admin.register(ApprovalHistory)
class ApprovalHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'approval', 'step_sequence', 'action', 'approver_user',
        'action_date', 'has_comments'
    ]
    list_filter = ['action', 'action_date']
    search_fields = [
        'approval__entity_number', 'approver_user__username', 'comments'
    ]
    readonly_fields = [
        'id', 'approval', 'step_sequence', 'approver_role', 'approver_user',
        'action', 'action_date', 'delegated_to_user', 'comments',
        'ip_address', 'created_at'
    ]
    date_hierarchy = 'action_date'
    
    fieldsets = (
        ('Approval', {
            'fields': ('approval', 'step_sequence')
        }),
        ('Approver', {
            'fields': ('approver_role', 'approver_user')
        }),
        ('Action', {
            'fields': ('action', 'action_date', 'comments')
        }),
        ('Delegation', {
            'fields': ('delegated_to_user',)
        }),
        ('Technical', {
            'fields': ('ip_address',),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """History is created automatically, not manually."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """History should not be deleted."""
        return False
    
    def has_comments(self, obj):
        """Indicate if comments exist."""
        if obj.comments:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: gray;">—</span>')
    has_comments.short_description = 'Comments'