from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.core.models import ManagementDepartment
from apps.core.management_data import DEPARTMENTS_DATA
from apps.accounts.models import Role, UserProfile

User = get_user_model()


class Command(BaseCommand):
    help = "Seed or update the 20 internal management departments and default staff roles."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding 20 internal management departments..."))

        departments_by_slug = {}
        created_count = 0
        updated_count = 0

        for item in DEPARTMENTS_DATA:
            dept, created = ManagementDepartment.objects.update_or_create(
                slug=item["slug"],
                defaults={
                    "name": item["name"],
                    "code": item["code"],
                    "description": item["description"],
                    "icon": item["icon"],
                    "accent_color": item.get("accent_color", "blue"),
                    "display_order": item["display_order"],
                    "is_active": True,
                    "login_required": True,
                }
            )
            departments_by_slug[item["slug"]] = dept
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Successfully processed {len(departments_by_slug)} departments ({created_count} created, {updated_count} updated)."
        ))

        # Seed standard management roles
        self.stdout.write(self.style.NOTICE("Configuring standard management roles..."))

        roles_spec = [
            {
                "name": "Super Administrator",
                "code": "super_admin",
                "description": "Universal administrator with unrestricted access to all 20 internal departments.",
                "is_superadmin": True,
                "dept_slugs": list(departments_by_slug.keys()),
            },
            {
                "name": "Inventory Manager",
                "code": "inventory_manager",
                "description": "Full access to inventory tracking, stock movements, and product catalog visibility.",
                "is_superadmin": False,
                "dept_slugs": ["inventory", "catalog"],
            },
            {
                "name": "CMS Content Manager",
                "code": "cms_manager",
                "description": "Full access to hero banners, homepage layout, navigation menus, and engagement analytics.",
                "is_superadmin": False,
                "dept_slugs": ["cms", "analytics"],
            },
            {
                "name": "Operations & Logistics Manager",
                "code": "operations_manager",
                "description": "End-to-end management of orders, shipping partners, and warehouse fulfillment.",
                "is_superadmin": False,
                "dept_slugs": ["orders", "shipping", "fulfillment", "inventory"],
            },
            {
                "name": "Customer Support Lead",
                "code": "support_lead",
                "description": "Management of customer helpdesk inquiries, user profiles, and product reviews moderation.",
                "is_superadmin": False,
                "dept_slugs": ["support", "accounts", "reviews"],
            },
            {
                "name": "Marketing & Promotions Lead",
                "code": "marketing_lead",
                "description": "Management of promotional campaigns, discount coupons, and store analytics.",
                "is_superadmin": False,
                "dept_slugs": ["promotions", "analytics", "recommendations"],
            },
        ]

        for r_spec in roles_spec:
            role, r_created = Role.objects.get_or_create(
                code=r_spec["code"],
                defaults={
                    "name": r_spec["name"],
                    "description": r_spec["description"],
                    "is_superadmin": r_spec["is_superadmin"],
                }
            )
            # Assign departments to role
            matched_depts = [departments_by_slug[s] for s in r_spec["dept_slugs"] if s in departments_by_slug]
            role.departments.set(matched_depts)
            role.save()
            action_text = "Created" if r_created else "Verified"
            self.stdout.write(f"  [{action_text}] Role: {role.name} ({len(matched_depts)} depts assigned)")

        # Ensure all existing superusers have UserProfile configured
        super_role = Role.objects.filter(code="super_admin").first()
        superusers = User.objects.filter(is_superuser=True)
        for su in superusers:
            profile, _ = UserProfile.objects.get_or_create(user=su)
            profile.is_management_staff = True
            profile.job_title = "Super Administrator"
            if super_role:
                profile.roles.add(super_role)
            profile.save()
            self.stdout.write(self.style.SUCCESS(f"  Configured staff profile for superuser '{su.username}'."))

        self.stdout.write(self.style.SUCCESS("Management department seeding completed successfully!"))
