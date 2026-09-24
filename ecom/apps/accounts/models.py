from typing import Any
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Role(models.Model):
    """
    Staff management role defining cross-department access and granular permissions.
    """
    name = models.CharField(max_length=100, unique=True, help_text="Role title (e.g. 'Inventory Manager', 'CMS Editor')")
    code = models.SlugField(max_length=80, unique=True, help_text="Unique code for internal role checks")
    description = models.TextField(blank=True, help_text="Scope and responsibilities of this role")
    departments = models.ManyToManyField(
        'core.ManagementDepartment',
        blank=True,
        related_name='roles',
        help_text="Management departments accessible by staff with this role"
    )
    permissions = models.ManyToManyField(
        'auth.Permission',
        blank=True,
        related_name='management_roles',
        help_text="Django permissions associated with this role"
    )
    is_superadmin = models.BooleanField(
        default=False,
        help_text="Designates this role as having universal access to all departments"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        verbose_name = 'Management Role'
        verbose_name_plural = 'Management Roles'
        ordering = ['name']

    def __str__(self) -> str:
        return str(self.name)


class UserProfile(models.Model):
    """
    Extends standard Django user model with management roles, department access overrides,
    and staff profile metadata.
    """
    user: Any = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    roles: Any = models.ManyToManyField(
        Role,
        blank=True,
        related_name='user_profiles',
        help_text="Roles assigned to this user"
    )
    department_access: Any = models.ManyToManyField(
        'core.ManagementDepartment',
        blank=True,
        related_name='assigned_user_profiles',
        help_text="Direct department access granted to this user (in addition to role access)"
    )
    is_management_staff = models.BooleanField(
        default=False,
        help_text="Allows user to authenticate into the /management/ portal"
    )
    job_title = models.CharField(max_length=120, blank=True, default="", help_text="Staff job title / designation")
    phone = models.CharField(max_length=30, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        verbose_name = 'User Profile & Staff Access'
        verbose_name_plural = 'User Profiles & Staff Access'

    def __str__(self) -> str:
        username = getattr(self.user, 'username', 'User')
        return f"{username} Profile ({self.job_title or 'Customer/Staff'})"

    @property
    def phone_number(self) -> str:
        return self.phone

    @phone_number.setter
    def phone_number(self, value: str) -> None:
        self.phone = value

    @property
    def role(self):
        return self.roles.first()

    def get_department_access_list(self) -> list:
        """Returns list of accessible department slugs."""
        return list(self.get_accessible_departments().values_list('slug', flat=True))

    def get_accessible_departments(self) -> Any:
        """
        Returns QuerySet of ManagementDepartment objects that this user is authorized to access.
        """
        from apps.core.models import ManagementDepartment
        user = getattr(self, 'user', None)
        is_super = getattr(user, 'is_superuser', False)
        roles = self.roles.all()
        if is_super or any(getattr(r, 'is_superadmin', False) for r in roles):
            return ManagementDepartment.objects.filter(is_active=True)

        direct_depts = self.department_access.filter(is_active=True)
        role_depts = ManagementDepartment.objects.filter(
            roles__in=roles,
            is_active=True
        )
        return (direct_depts | role_depts).distinct()

    def has_department_access(self, dept_slug: str) -> bool:
        """
        Determines if user is authorized for a specific department slug or code.
        """
        user = getattr(self, 'user', None)
        if getattr(user, 'is_superuser', False):
            return True
        roles = self.roles.all()
        if any(getattr(r, 'is_superadmin', False) for r in roles):
            return True

        if self.department_access.filter(slug=dept_slug, is_active=True).exists():
            return True

        if self.roles.filter(departments__slug=dept_slug, departments__is_active=True).exists():
            return True

        return False


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Ensure every User has a linked UserProfile automatically.
    Superusers automatically have is_management_staff=True.
    """
    if kwargs.get('raw', False):
        return

    profile, _ = UserProfile.objects.get_or_create(user=instance)
    if instance.is_superuser and not profile.is_management_staff:
        profile.is_management_staff = True
        profile.job_title = "Super Administrator"
        profile.save()



class Address(models.Model):
    """
    Customer shipping and billing addresses for checkout, order delivery, and account profiles.
    """
    ADDRESS_TYPE_CHOICES = [
        ('shipping', 'Shipping'),
        ('billing', 'Billing'),
    ]
    user: Any = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='addresses'
    )
    full_name = models.CharField(max_length=150, help_text="Recipient contact name")
    phone = models.CharField(max_length=30, blank=True, default='', help_text="Contact phone number for deliveries")
    street_address = models.CharField(max_length=255, help_text="Street line and house/flat number")
    apartment = models.CharField(max_length=100, blank=True, default='', help_text="Suite, unit, building, floor (optional)")
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='United States')
    address_type = models.CharField(max_length=20, choices=ADDRESS_TYPE_CHOICES, default='shipping')
    is_default = models.BooleanField(default=False, help_text="Designates this address as primary for its type")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        verbose_name = 'Customer Address'
        verbose_name_plural = 'Customer Addresses'
        ordering = ['-is_default', '-created_at']

    def __str__(self) -> str:
        return f"{self.full_name} - {self.street_address}, {self.city} ({self.address_type})"

    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(
                user=self.user,
                address_type=self.address_type,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

