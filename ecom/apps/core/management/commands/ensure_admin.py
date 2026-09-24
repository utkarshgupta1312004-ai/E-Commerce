import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Create an initial superuser from environment variables if one does not already exist."

    def handle(self, *args, **options):
        username = (os.environ.get("DJANGO_SUPERUSER_USERNAME") or "").strip()
        password = (os.environ.get("DJANGO_SUPERUSER_PASSWORD") or "").strip()
        email = (os.environ.get("DJANGO_SUPERUSER_EMAIL") or "admin@cartivo.local").strip()

        if not username or not password:
            self.stdout.write(
                self.style.WARNING(
                    "DJANGO_SUPERUSER_USERNAME or DJANGO_SUPERUSER_PASSWORD not provided; skipping automated superuser creation."
                )
            )
            return

        user = User.objects.filter(username=username).first()
        if user:
            self.stdout.write(
                self.style.SUCCESS(f"Superuser '{username}' already exists.")
            )
        else:
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(
                self.style.SUCCESS(f"Successfully created superuser '{username}'.")
            )
