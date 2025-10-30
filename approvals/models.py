"""
Approval Workflow Models
========================
This module contains:
1. ApprovalWorkflow - Define approval workflows for different entity types
2. ApprovalWorkflowStep - Individual steps in a workflow
3. Approval - Track approval instances for documents
4. ApprovalHistory - Audit trail of approval actions

Supports:
- Multi-level approvals
- Parallel approvals (multiple approvers at same step)
- Sequential approvals
- Role-based and user-based approvers
- Conditional approvals (value thresholds)
- Timeout and escalation
- Complete audit trail
"""

import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import timedelta

from core.models import BaseModel, Factory
from users.models import User, Role


# ============================================================================
# APPROVAL WORKFLOW
# ============================================================================

class ApprovalWorkflow(BaseModel):
    """
    Define approval workflows for different entity types.
    
    Examples:
    - "Standard PR Approval" for Purchase Requests under 50,000
    - "High Value PO Approval" for Purchase Orders over 100,000
    - "GRN Quality Check" for Goods Received Notes
    """
    
    ENTITY_TYPES = [
        ('PR', 'Purchase Request'),
        ('PO', 'Purchase Order'),
        ('GRN', 'Goods Received Note'),
        ('ADJUSTMENT', 'Inventory Adjustment'),
        ('TRANSFER', 'Stock Transfer'),
        ('ISSUE', 'Stock Issue'),
        ('ASSET_ASSIGNMENT', 'Asset Assignment'),
        ('MAINTENANCE', 'Maintenance Request'),
    ]
    
    workflow_name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique workflow name"
    )
    entity_type = models.CharField(
        max_length=50,
        choices=ENTITY_TYPES,
        help_text="Entity type this workflow applies to"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Workflow description"
    )
    factory = models.ForeignKey(
        Factory,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='approval_workflows',
        help_text="Factory (NULL = applies to all factories)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Is workflow active?"
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Is this the default workflow for this entity type?"
    )
    
    # Conditions for when this workflow applies
    min_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Minimum value for this workflow to apply"
    )
    max_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Maximum value for this workflow to apply"
    )
    
    class Meta:
        db_table = 'approval_workflows'
        verbose_name = 'Approval Workflow'
        verbose_name_plural = 'Approval Workflows'
        ordering = ['entity_type', 'workflow_name']
        indexes = [
            models.Index(fields=['entity_type', 'is_active']),
            models.Index(fields=['is_default']),
        ]
    
    def __str__(self):
        return f"{self.workflow_name} ({self.get_entity_type_display()})"
    
    def clean(self):
        """Validate workflow data."""
        super().clean()
        
        # Validate min/max value
        if self.min_value and self.max_value:
            if self.min_value > self.max_value:
                raise ValidationError("Minimum value cannot be greater than maximum value.")
        
        # Ensure only one default workflow per entity type
        if self.is_default:
            existing_default = ApprovalWorkflow.objects.filter(
                entity_type=self.entity_type,
                factory=self.factory,
                is_default=True
            ).exclude(id=self.id)
            
            if existing_default.exists():
                raise ValidationError(
                    f"A default workflow already exists for {self.get_entity_type_display()}"
                )
    
    def get_steps(self):
        """Get all workflow steps in order."""
        return self.steps.filter(deleted_at__isnull=True).order_by('step_sequence')
    
    def applies_to_value(self, value):
        """
        Check if this workflow applies to a given value.
        
        Args:
            value: Decimal value to check
        
        Returns:
            bool: True if workflow applies
        """
        if self.min_value and value < self.min_value:
            return False
        if self.max_value and value > self.max_value:
            return False
        return True


# ============================================================================
# APPROVAL WORKFLOW STEP
# ============================================================================

class ApprovalWorkflowStep(BaseModel):
    """
    Individual steps in an approval workflow.
    
    Supports:
    - Sequential steps (step 1 → step 2 → step 3)
    - Parallel approvals (multiple approvers at same step)
    - Role-based or user-based approvers
    - Timeout and escalation
    """
    
    workflow = models.ForeignKey(
        ApprovalWorkflow,
        on_delete=models.CASCADE,
        related_name='steps',
        help_text="Parent workflow"
    )
    step_sequence = models.IntegerField(
        help_text="Step sequence (1, 2, 3, etc.)"
    )
    step_name = models.CharField(
        max_length=100,
        help_text="Step name (e.g., 'Department Head Approval')"
    )
    
    # Approver configuration
    approver_role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='workflow_steps',
        help_text="Approver role (any user with this role can approve)"
    )
    approver_user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='workflow_steps',
        help_text="Specific approver user (takes precedence over role)"
    )
    
    # Parallel approval support
    is_parallel = models.BooleanField(
        default=False,
        help_text="Can this step be approved in parallel with other steps?"
    )
    parallel_group = models.IntegerField(
        null=True,
        blank=True,
        help_text="Group number for parallel approvals (same sequence, same group)"
    )
    
    # Step configuration
    is_mandatory = models.BooleanField(
        default=True,
        help_text="Is this step mandatory?"
    )
    can_delegate = models.BooleanField(
        default=True,
        help_text="Can approver delegate to another user?"
    )
    
    # Timeout and escalation
    timeout_hours = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Hours until escalation (NULL = no timeout)"
    )
    escalation_role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='escalation_steps',
        help_text="Escalate to this role if timeout"
    )
    
    # Conditional approval
    conditions = models.JSONField(
        blank=True,
        null=True,
        help_text="JSON conditions for when this step applies"
    )
    
    class Meta:
        db_table = 'approval_workflow_steps'
        verbose_name = 'Approval Workflow Step'
        verbose_name_plural = 'Approval Workflow Steps'
        ordering = ['workflow', 'step_sequence']
        unique_together = ['workflow', 'step_sequence']
        indexes = [
            models.Index(fields=['workflow', 'step_sequence']),
        ]
    
    def __str__(self):
        return f"{self.workflow.workflow_name} - Step {self.step_sequence}: {self.step_name}"
    
    def clean(self):
        """Validate step data."""
        super().clean()
        
        # Must have either role or user
        if not self.approver_role and not self.approver_user:
            raise ValidationError("Step must have either approver_role or approver_user.")
        
        # Parallel group only valid if is_parallel
        if self.parallel_group and not self.is_parallel:
            raise ValidationError("Parallel group can only be set for parallel steps.")
    
    def get_approvers(self):
        """
        Get list of users who can approve this step.
        
        Returns:
            QuerySet of User objects
        """
        if self.approver_user:
            return User.objects.filter(id=self.approver_user.id, is_active=True)
        elif self.approver_role:
            return User.objects.filter(
                user_roles__role=self.approver_role,
                is_active=True
            ).distinct()
        return User.objects.none()


# ============================================================================
# APPROVAL
# ============================================================================

class Approval(models.Model):
    """
    Track approval instances for documents.
    
    Created when a document needs approval.
    Tracks current step, status, and completion.
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
        ('ESCALATED', 'Escalated'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Document reference
    entity_type = models.CharField(
        max_length=50,
        help_text="Entity type (PR, PO, GRN, etc.)"
    )
    entity_id = models.UUIDField(
        help_text="Entity UUID"
    )
    entity_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Human-readable reference (PR-2025-0001, etc.)"
    )
    
    # Workflow
    workflow = models.ForeignKey(
        ApprovalWorkflow,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='approvals',
        help_text="Workflow being used"
    )
    current_step_sequence = models.IntegerField(
        null=True,
        blank=True,
        help_text="Current step sequence number"
    )
    
    # Request details
    requested_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='approval_requests',
        help_text="User who requested approval"
    )
    requested_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When approval was requested"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text="Current approval status"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When approval was completed"
    )
    
    # Additional context
    remarks = models.TextField(
        blank=True,
        null=True,
        help_text="Requestor remarks"
    )
    metadata = models.JSONField(
        blank=True,
        null=True,
        help_text="Additional context (value, urgency, etc.)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'approvals'
        verbose_name = 'Approval'
        verbose_name_plural = 'Approvals'
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['status', 'requested_at']),
            models.Index(fields=['requested_by', 'status']),
        ]
    
    def __str__(self):
        return f"{self.entity_type} {self.entity_number} - {self.status}"
    
    def get_current_step(self):
        """Get the current workflow step."""
        if not self.workflow or not self.current_step_sequence:
            return None
        return self.workflow.steps.filter(
            step_sequence=self.current_step_sequence
        ).first()
    
    def get_pending_approvers(self):
        """Get users who can approve the current step."""
        current_step = self.get_current_step()
        if not current_step:
            return User.objects.none()
        return current_step.get_approvers()
    
    def advance_to_next_step(self):
        """
        Advance approval to the next step.
        
        Returns:
            bool: True if advanced, False if workflow complete
        """
        if not self.workflow:
            return False
        
        steps = self.workflow.get_steps()
        
        if self.current_step_sequence is None:
            # Start at first step
            first_step = steps.first()
            if first_step:
                self.current_step_sequence = first_step.step_sequence
                self.status = 'IN_PROGRESS'
                self.save()
                return True
            return False
        
        # Find next step
        next_step = steps.filter(
            step_sequence__gt=self.current_step_sequence
        ).first()
        
        if next_step:
            self.current_step_sequence = next_step.step_sequence
            self.save()
            return True
        else:
            # No more steps - approval complete
            self.status = 'APPROVED'
            self.completed_at = timezone.now()
            self.save()
            return False
    
    def reject(self, user, comments=None):
        """
        Reject the approval.
        
        Args:
            user: User who rejected
            comments: Rejection comments
        """
        self.status = 'REJECTED'
        self.completed_at = timezone.now()
        self.save()
        
        # Create history entry
        ApprovalHistory.objects.create(
            approval=self,
            step_sequence=self.current_step_sequence,
            approver_user=user,
            action='REJECTED',
            comments=comments
        )
    
    def cancel(self, user, reason=None):
        """
        Cancel the approval.
        
        Args:
            user: User who cancelled
            reason: Cancellation reason
        """
        self.status = 'CANCELLED'
        self.completed_at = timezone.now()
        self.save()
        
        # Create history entry
        ApprovalHistory.objects.create(
            approval=self,
            step_sequence=self.current_step_sequence,
            approver_user=user,
            action='CANCELLED',
            comments=reason
        )
    
    def check_timeout(self):
        """
        Check if current step has timed out.
        
        Returns:
            bool: True if timed out
        """
        current_step = self.get_current_step()
        if not current_step or not current_step.timeout_hours:
            return False
        
        # Get last action time
        last_action = self.history.filter(
            step_sequence=self.current_step_sequence
        ).order_by('-action_date').first()
        
        reference_time = last_action.action_date if last_action else self.requested_at
        timeout_time = reference_time + timedelta(hours=current_step.timeout_hours)
        
        return timezone.now() > timeout_time
    
    def escalate(self):
        """Escalate approval due to timeout."""
        current_step = self.get_current_step()
        if not current_step or not current_step.escalation_role:
            return False
        
        self.status = 'ESCALATED'
        self.save()
        
        # Create history entry
        ApprovalHistory.objects.create(
            approval=self,
            step_sequence=self.current_step_sequence,
            action='ESCALATED',
            comments=f'Escalated to {current_step.escalation_role.role_name} due to timeout'
        )
        
        return True


# ============================================================================
# APPROVAL HISTORY
# ============================================================================

class ApprovalHistory(models.Model):
    """
    Audit trail of all approval actions.
    
    Immutable record of who did what and when.
    """
    
    ACTION_CHOICES = [
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('DELEGATED', 'Delegated'),
        ('ESCALATED', 'Escalated'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    approval = models.ForeignKey(
        Approval,
        on_delete=models.CASCADE,
        related_name='history',
        help_text="Parent approval"
    )
    step_sequence = models.IntegerField(
        help_text="Step sequence number at time of action"
    )
    
    # Approver details
    approver_role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='approval_history',
        help_text="Approver role"
    )
    approver_user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='approval_history',
        help_text="User who took action"
    )
    
    # Action
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        help_text="Action taken"
    )
    action_date = models.DateTimeField(
        auto_now_add=True,
        help_text="When action was taken"
    )
    
    # Delegation
    delegated_to_user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='delegated_approvals',
        help_text="User to whom approval was delegated"
    )
    
    # Details
    comments = models.TextField(
        blank=True,
        null=True,
        help_text="Approver comments"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of approver"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'approval_history'
        verbose_name = 'Approval History'
        verbose_name_plural = 'Approval Histories'
        ordering = ['-action_date']
        indexes = [
            models.Index(fields=['approval', '-action_date']),
            models.Index(fields=['approver_user', '-action_date']),
            models.Index(fields=['action', '-action_date']),
        ]
    
    def __str__(self):
        return f"{self.approval.entity_number} - {self.action} by {self.approver_user.username}"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_approval(entity_type, entity_id, entity_number, requested_by, value=None, remarks=None):
    """
    Create an approval instance for an entity.
    
    Args:
        entity_type: Type of entity (PR, PO, GRN, etc.)
        entity_id: UUID of entity
        entity_number: Human-readable reference
        requested_by: User requesting approval
        value: Value for workflow selection (optional)
        remarks: Requestor remarks (optional)
    
    Returns:
        Approval instance
    """
    # Find applicable workflow
    workflows = ApprovalWorkflow.objects.filter(
        entity_type=entity_type,
        is_active=True,
        deleted_at__isnull=True
    )
    
    # Filter by value if provided
    if value:
        workflows = [w for w in workflows if w.applies_to_value(value)]
    
    # Get default workflow or first match
    workflow = None
    for w in workflows:
        if w.is_default:
            workflow = w
            break
    if not workflow and workflows:
        workflow = workflows[0]
    
    if not workflow:
        raise ValidationError(f"No active workflow found for {entity_type}")
    
    # Create approval
    approval = Approval.objects.create(
        entity_type=entity_type,
        entity_id=entity_id,
        entity_number=entity_number,
        workflow=workflow,
        requested_by=requested_by,
        remarks=remarks,
        metadata={'value': str(value)} if value else None,
        status='PENDING'
    )
    
    # Advance to first step
    approval.advance_to_next_step()
    
    return approval


def approve_step(approval, user, comments=None, ip_address=None):
    """
    Approve current step.
    
    Args:
        approval: Approval instance
        user: User approving
        comments: Approval comments (optional)
        ip_address: IP address (optional)
    
    Returns:
        bool: True if approval complete, False if more steps remaining
    """
    current_step = approval.get_current_step()
    if not current_step:
        raise ValidationError("No current step to approve")
    
    # Check if user can approve this step
    if user not in current_step.get_approvers():
        raise ValidationError("User is not authorized to approve this step")
    
    # Create history entry
    ApprovalHistory.objects.create(
        approval=approval,
        step_sequence=approval.current_step_sequence,
        approver_role=current_step.approver_role,
        approver_user=user,
        action='APPROVED',
        comments=comments,
        ip_address=ip_address
    )
    
    # Advance to next step
    workflow_complete = not approval.advance_to_next_step()
    
    return workflow_complete