import os
from pathlib import Path
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Populate database from seed_data.json fixture if database is unpopulated."

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force load fixture even if products or categories already exist.'
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        
        # Check if database already has core catalog data
        try:
            from apps.catalog.models import Category, Product
            category_count = Category.objects.count()
            product_count = Product.objects.count()
        except Exception as e:
            category_count = 0
            product_count = 0

        if not force and (category_count > 0 or product_count > 0):
            self.stdout.write(
                self.style.SUCCESS(
                    f"Database already populated ({category_count} categories, {product_count} products). Skipping seed."
                )
            )
            return

        # Candidate paths for seed_data.json fixture
        base_dir = Path(settings.BASE_DIR)
        candidates = [
            base_dir / 'fixtures' / 'seed_data.json',
            base_dir / 'ecom' / 'fixtures' / 'seed_data.json',
            base_dir / 'data.json',
            base_dir / 'ecom' / 'data.json',
            Path(__file__).resolve().parent.parent.parent.parent / 'fixtures' / 'seed_data.json',
        ]

        fixture_file = None
        for path in candidates:
            if path.exists() and path.stat().st_size > 0:
                fixture_file = path
                break

        if not fixture_file:
            self.stdout.write(
                self.style.WARNING("No seed_data.json or data.json fixture found to seed database.")
            )
            return

        self.stdout.write(f"Seeding database from fixture: {fixture_file} ...")
        try:
            call_command('loaddata', str(fixture_file))
            try:
                from apps.catalog.models import Category, Product
                cat_count = Category.objects.count()
                prod_count = Product.objects.count()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully populated database: {cat_count} categories, {prod_count} products loaded."
                    )
                )
            except Exception:
                self.stdout.write(self.style.SUCCESS("Successfully loaded fixture."))
        except Exception as err:
            self.stdout.write(
                self.style.ERROR(f"Error loading fixture: {err}")
            )
