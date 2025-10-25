"""
User Management & RBAC Models
==============================
This module contains:
1. User - Custom user model extending Django's AbstractBaseUser
2. Role - User roles (SuperAdmin, Manager, Storekeeper, etc.)
3. Permission - Granular permissions
4. UserRole - Many-to-Many relationship between users and roles
5. RolePermission - Many-to-Many relationship between roles and permissions
6. StoreType - Types of stores (Yarn, IT, General, etc.)
7. UserStoreAccess - Store-level access control
8. UserSession - Session tracking
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from core.models import BaseModel, Factory, Department


# ============================================================================
# CUSTOM USER MANAGER
# ============================================================================

class CustomUserManager(BaseUserManager):
    """
    Custom user manager for creating users and superusers.
    """
    
    def create_user(self, username, email, password=None, **extra_fields):
        """Create and save a regular user."""
        if not username:
            raise ValueError('Users must have a username')
        if not email:
            raise ValueError('Users must have an email address')
        
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, email, password=None, **extra_fields):
        """Create and save a superuser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(username, email, password, **extra_fields)


# ============================================================================
# USER MODEL
# ============================================================================

class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model for the IMS.
    
    Extends Django's AbstractBaseUser to use username for login
    and adds custom fields for employee tracking.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Authentication fields
    username = models.CharField(
        max_length=50,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9_]+$',
                message='Username must contain only letters, numbers, and underscores.'
            )
        ],
        help_text="Unique username for login"
    )
    email = models.EmailField(
        unique=True,
        help_text="Email address"
    )
    password = models.CharField(
        max_length=255,
        help_text="Hashed password"
    )
    
    # Personal information
    full_name = models.CharField(
        max_length=100,
        help_text="Full name of the user"
    )
    employee_id = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        help_text="Employee ID from HR system"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Contact phone number"
    )
    
    # Organizational links
    factory = models.ForeignKey(
        Factory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text="Primary factory assignment"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text="Department assignment"
    )
    
    # Status fields
    is_active = models.BooleanField(
        default=True,
        help_text="Is user account active?"
    )
    is_staff = models.BooleanField(
        default=False,
        help_text="Can user access admin site?"
    )
    must_change_password = models.BooleanField(
        default=False,
        help_text="Must user change password on next login?"
    )
    
    # Login tracking
    last_login_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last login timestamp"
    )
    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of last login"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(null=True, blank=True)
    updated_by = models.UUIDField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.UUIDField(null=True, blank=True)
    
    # Required for Django's authentication
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'full_name']
    
    objects = CustomUserManager()
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['username']
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['email']),
            models.Index(fields=['employee_id']),
            models.Index(fields=['factory', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.username} - {self.full_name}"
    
    def get_full_name(self):
        """Return full name."""
        return self.full_name
    
    def get_short_name(self):
        """Return username."""
        return self.username
    
    def update_last_login(self, ip_address=None):
        """Update last login timestamp and IP."""
        self.last_login_at = timezone.now()
        if ip_address:
            self.last_login_ip = ip_address
        self.save(update_fields=['last_login_at', 'last_login_ip'])


# ============================================================================
# ROLE MODEL
# ============================================================================

class Role(BaseModel):
    """
    User roles for RBAC (Role-Based Access Control).
    
    Examples: SuperAdmin, Factory Manager, Storekeeper, QC Inspector
    """
    role_name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique role name"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Role description"
    )
    is_system_role = models.BooleanField(
        default=False,
        help_text="System role (cannot be modified/deleted)"
    )
    
    class Meta:
        db_table = 'roles'
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'
        ordering = ['role_name']
    
    def __str__(self):
        return self.role_name
    
    def get_permissions(self):
        """Get all permissions for this role."""
        return Permission.objects.filter(
            role_permissions__role=self,
            deleted_at__isnull=True
        )


# ============================================================================
# PERMISSION MODEL
# ============================================================================

class Permission(BaseModel):
    """
    Granular permissions for actions within the system.
    
    Examples: 'approve_po', 'create_grn', 'view_yarn_store'
    """
    
    MODULE_CHOICES = [
        ('PROCUREMENT', 'Procurement'),
        ('INVENTORY', 'Inventory'),
        ('PRODUCTION', 'Production'),
        ('QUALITY', 'Quality Control'),
        ('REPORTS', 'Reports'),
        ('ADMIN', 'Administration'),
    ]
    
    permission_key = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique permission key (e.g., 'approve_po')"
    )
    module = models.CharField(
        max_length=50,
        choices=MODULE_CHOICES,
        help_text="Module this permission belongs to"
    )
    module_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Specific module code (e.g., 'YARN_STORE')"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Permission description"
    )
    requires_approval = models.BooleanField(
        default=False,
        help_text="Does this action require approval?"
    )
    approval_threshold = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Value threshold requiring approval"
    )
    
    class Meta:
        db_table = 'permissions'
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'
        ordering = ['module', 'permission_key']
        indexes = [
            models.Index(fields=['permission_key']),
            models.Index(fields=['module']),
        ]
    
    def __str__(self):
        return f"{self.module} - {self.permission_key}"


# ============================================================================
# USER-ROLE RELATIONSHIP
# ============================================================================

class UserRole(models.Model):
    """Many-to-Many relationship between Users and Roles."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_roles'
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='user_roles'
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_roles'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_roles'
        unique_together = ['user', 'role']
        verbose_name = 'User Role'
        verbose_name_plural = 'User Roles'
    
    def __str__(self):
        return f"{self.user.username} - {self.role.role_name}"


# ============================================================================
# ROLE-PERMISSION RELATIONSHIP
# ============================================================================

class RolePermission(models.Model):
    """Many-to-Many relationship between Roles and Permissions."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='role_permissions'
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name='role_permissions'
    )
    
    class Meta:
        db_table = 'role_permissions'
        unique_together = ['role', 'permission']
        verbose_name = 'Role Permission'
        verbose_name_plural = 'Role Permissions'
    
    def __str__(self):
        return f"{self.role.role_name} - {self.permission.permission_key}"


# ============================================================================
# STORE TYPE MODEL
# ============================================================================

class StoreType(models.Model):
    """
    Types of stores in the factory.
    
    Examples: Yarn Store, IT Store, General Store, etc.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store_code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique store code"
    )
    store_name = models.CharField(
        max_length=100,
        help_text="Store name"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Store description"
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Icon identifier for UI"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Is store type active?"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'store_types'
        verbose_name = 'Store Type'
        verbose_name_plural = 'Store Types'
        ordering = ['store_name']
    
    def __str__(self):
        return self.store_name


# ============================================================================
# USER STORE ACCESS (Store-Level Permissions)
# ============================================================================

class UserStoreAccess(models.Model):
    """
    Store-level access control for users.
    
    Defines which stores a user can access and what actions they can perform.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='store_access'
    )
    store_type = models.ForeignKey(
        StoreType,
        on_delete=models.CASCADE,
        related_name='user_access'
    )
    factory = models.ForeignKey(
        Factory,
        on_delete=models.CASCADE,
        related_name='store_access'
    )
    
    # Granular permissions
    can_view = models.BooleanField(default=True)
    can_create = models.BooleanField(default=False)
    can_update = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    can_approve = models.BooleanField(default=False)
    can_issue = models.BooleanField(default=False)
    can_receive = models.BooleanField(default=False)
    
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_store_access'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_store_access'
        unique_together = ['user', 'store_type', 'factory']
        verbose_name = 'User Store Access'
        verbose_name_plural = 'User Store Access'
        indexes = [
            models.Index(fields=['user', 'store_type']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.store_type.store_name} ({self.factory.factory_code})"


# ============================================================================
# USER SESSION MODEL
# ============================================================================

class UserSession(models.Model):
    """Track user sessions for security and auditing."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    session_token = models.CharField(
        max_length=255,
        unique=True,
        help_text="Session token"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address"
    )
    user_agent = models.TextField(
        blank=True,
        null=True,
        help_text="Browser user agent"
    )
    login_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Login timestamp"
    )
    last_activity_at = models.DateTimeField(
        auto_now=True,
        help_text="Last activity timestamp"
    )
    logout_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Logout timestamp"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Is session active?"
    )
    
    class Meta:
        db_table = 'user_sessions'
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'
        ordering = ['-login_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['session_token']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.login_at}"
    
    def end_session(self):
        """End the session."""
        self.logout_at = timezone.now()
        self.is_active = False
        self.save(update_fields=['logout_at', 'is_active'])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def user_has_permission(user, permission_key):
    """
    Check if user has a specific permission.
    
    Args:
        user: User instance
        permission_key: Permission key to check
    
    Returns:
        bool: True if user has permission
    """
    if user.is_superuser:
        return True
    
    return Permission.objects.filter(
        permission_key=permission_key,
        role_permissions__role__user_roles__user=user,
        deleted_at__isnull=True
    ).exists()


def user_has_store_access(user, store_code, factory_id, permission_type='view'):
    """
    Check if user has access to a specific store.
    
    Args:
        user: User instance
        store_code: Store type code (e.g., 'YARN_STORE')
        factory_id: Factory UUID
        permission_type: Type of access (view, create, update, delete, approve, issue, receive)
    
    Returns:
        bool: True if user has access
    """
    if user.is_superuser:
        return True
    
    permission_field = f'can_{permission_type}'
    
    return UserStoreAccess.objects.filter(
        user=user,
        store_type__store_code=store_code,
        factory_id=factory_id,
        **{permission_field: True}
    ).exists()