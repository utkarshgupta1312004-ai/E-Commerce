from typing import Any
from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models
from django.urls import reverse


class ManagementDepartment(models.Model):
    """
    Represents an internal management department/module in the e-commerce system.
    Configurable via Django Admin to control cards in the /management/ portal.
    """
    name = models.CharField(max_length=100, unique=True, help_text="User-facing department name (e.g. 'Inventory Management')")
    slug = models.SlugField(max_length=80, unique=True, help_text="URL slug identifier (e.g. 'inventory')")
    code = models.CharField(max_length=50, unique=True, help_text="Internal code namespace (e.g. 'inventory')")
    description = models.TextField(help_text="Short description displayed on the management card")
    icon = models.CharField(max_length=60, default="layers", help_text="Lucide icon name (e.g. 'package', 'users', 'shopping-cart')")
    url_name = models.CharField(max_length=150, blank=True, default="", help_text="Target URL or named route if customized")
    required_permission = models.CharField(max_length=100, blank=True, default="", help_text="Optional permission codename required for access (e.g. 'inventory.view_inventory')")
    login_required = models.BooleanField(default=True, help_text="Require authentication to access this department")
    is_active = models.BooleanField(default=True, db_index=True, help_text="Whether this department is visible and accessible")
    display_order = models.PositiveIntegerField(default=0, help_text="Ordering rank on the management portal grid")
    accent_color = models.CharField(
        max_length=30,
        default="blue",
        help_text="Theme color identifier: blue, emerald, amber, purple, rose, indigo, slate, cyan"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        verbose_name = 'Management Department'
        verbose_name_plural = 'Management Departments'
        ordering = ['display_order', 'name']

    def __str__(self) -> str:
        return str(self.name)

    def get_absolute_url(self) -> str:
        return f"/management/#{self.slug}"


class DepartmentAccount(models.Model):
    """
    Credentials and account status for an existing ManagementDepartment.
    Managed exclusively by Super Administrators to enable department-level logins.
    """
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_SUSPENDED = 'SUSPENDED'
    STATUS_INACTIVE = 'INACTIVE'
    STATUS_PENDING = 'PENDING'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_SUSPENDED, 'Suspended'),
        (STATUS_INACTIVE, 'Inactive'),
        (STATUS_PENDING, 'Pending'),
    ]

    department = models.OneToOneField(
        ManagementDepartment,
        on_delete=models.CASCADE,
        related_name='account',
        help_text="Target management department associated with this account"
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='department_account',
        help_text="Linked Django User of the project for auth-based login and permissions"
    )
    login_id = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique department login identifier (e.g. 'CMS001', 'INV001')"
    )
    password_hash = models.CharField(
        max_length=255,
        help_text="Securely hashed password (never stored in plaintext)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        help_text="Operational access state of the department account"
    )
    last_login = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the most recent successful department authentication"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        verbose_name = 'Department Account'
        verbose_name_plural = 'Department Accounts'
        ordering = ['department__display_order', 'department__name']

    def __str__(self) -> str:
        return f"{self.department.name} ({self.login_id}) - {self.status}"

    def set_password(self, raw_password: str) -> None:
        from django.contrib.auth.hashers import make_password
        self.password_hash = make_password(raw_password)
        if self.user:
            self.user.set_password(raw_password)
            self.user.save(update_fields=['password'])

    def check_password(self, raw_password: str) -> bool:
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password_hash)

    @property
    def is_active(self) -> bool:
        return self.status == self.STATUS_ACTIVE

    def sync_user(self, raw_password: str = None) -> Any:
        """
        Ensures a standard Django User exists for this department account,
        adds it to the 'Cartivo Department' group, sets staff flags, and keeps
        passwords and active status synchronized.
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()

        dept_group, _ = Group.objects.get_or_create(name='Cartivo Department')

        user = self.user
        if not user:
            user = User.objects.filter(username=self.login_id).first()

        if not user:
            user = User.objects.create_user(
                username=self.login_id,
                email=f"{self.login_id.lower()}@cartivo.internal",
                first_name=self.department.name[:30],
                is_staff=True,
                is_active=(self.status == self.STATUS_ACTIVE)
            )
        else:
            user.username = self.login_id
            user.first_name = self.department.name[:30]
            user.is_staff = True
            user.is_active = (self.status == self.STATUS_ACTIVE)

        if raw_password:
            user.set_password(raw_password)
        elif self.password_hash:
            user.password = self.password_hash

        user.save()

        # Add to Cartivo Department group
        user.groups.add(dept_group)
        # Remove from Customer group if present
        customer_group = Group.objects.filter(name='Customer').first()
        if customer_group:
            user.groups.remove(customer_group)

        # Sync UserProfile
        if hasattr(user, 'profile'):
            user.profile.is_management_staff = True
            user.profile.job_title = f"{self.department.name} Staff"
            user.profile.save()
            user.profile.department_access.add(self.department)

        if self.user_id != user.id:
            self.user = user
            DepartmentAccount.objects.filter(pk=self.pk).update(user=user)

        return user


