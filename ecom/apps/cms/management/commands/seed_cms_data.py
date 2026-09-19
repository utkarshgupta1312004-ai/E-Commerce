from decimal import Decimal
from django.core.management.base import BaseCommand
from apps.catalog.models import Category, Brand, Product, ProductImage
from apps.cms.models import (
    NavbarItem,
    CategoryNavItem,
    PromoBanner,
    HomepageCategoryItem,
    TrustBadge,
    HomepageSection,
    HomepageSectionProduct,
)


class Command(BaseCommand):
    help = "Seed CMS database models with initial content mirroring current storefront design."

    def handle(self, *args, **options):
        self.stdout.write("Seeding CMS and catalog data...")

        # 1. Seed Navbar Items
        NavbarItem.objects.all().delete()
        nav_new = NavbarItem.objects.create(
            title="New Arrivals",
            url="/products/?sort=newest",
            display_order=1,
            is_active=True,
        )
        nav_collections = NavbarItem.objects.create(
            title="Collections",
            url="/products/",
            display_order=2,
            is_active=True,
        )
        # Add dropdown items under Collections
        NavbarItem.objects.create(
            title="Summer Essentials",
            url="/products/?collection=summer",
            parent=nav_collections,
            display_order=1,
            is_active=True,
        )
        NavbarItem.objects.create(
            title="Luxury Acoustic Series",
            url="/products/?collection=acoustic",
            parent=nav_collections,
            display_order=2,
            is_active=True,
        )
        NavbarItem.objects.create(
            title="Titanium Chrono Club",
            url="/products/?collection=titanium",
            parent=nav_collections,
            display_order=3,
            is_active=True,
        )

        nav_categories = NavbarItem.objects.create(
            title="Categories",
            url="/products/",
            display_order=3,
            is_active=True,
        )
        NavbarItem.objects.create(
            title="Acoustic Audio",
            url="/category/audio/",
            parent=nav_categories,
            display_order=1,
            is_active=True,
        )
        NavbarItem.objects.create(
            title="Precision Watches",
            url="/category/timepieces/",
            parent=nav_categories,
            display_order=2,
            is_active=True,
        )
        NavbarItem.objects.create(
            title="Minimal Apparel",
            url="/category/apparel/",
            parent=nav_categories,
            display_order=3,
            is_active=True,
        )

        nav_sale = NavbarItem.objects.create(
            title="Sale",
            url="/products/?sale=true",
            badge_text="20%",
            badge_color="amber",
            display_order=4,
            is_active=True,
        )
        self.stdout.write(self.style.SUCCESS("[OK] Seeded Navbar items & dropdowns"))

        # 2. Seed Catalog Categories & Brands
        cat_audio, _ = Category.objects.get_or_create(
            slug="audio",
            defaults={"name": "Acoustic Audio", "description": "Headphones, speakers & drivers", "icon_name": "headphones"}
        )
        cat_watches, _ = Category.objects.get_or_create(
            slug="timepieces",
            defaults={"name": "Precision Watches", "description": "Automatic & smart chronographs", "icon_name": "watch"}
        )
        cat_apparel, _ = Category.objects.get_or_create(
            slug="apparel",
            defaults={"name": "Minimal Apparel", "description": "Organic cotton & merino wool", "icon_name": "shirt"}
        )
        cat_accessories, _ = Category.objects.get_or_create(
            slug="accessories",
            defaults={"name": "Leather Goods", "description": "Wallets, folios & tech sleeves", "icon_name": "briefcase"}
        )

        brand_cartivo, _ = Brand.objects.get_or_create(slug="cartivo", defaults={"name": "Cartivo Atelier"})
        brand_aura, _ = Brand.objects.get_or_create(slug="aura-sound", defaults={"name": "Aura Sound"})

        # 3. Seed Category Sub-Nav items (14 Flipkart-style items)
        CategoryNavItem.objects.all().delete()
        category_nav_data = [
            ("For You", None, "/", "sparkles", True, 1),
            ("Fashion", cat_apparel, "/category/fashion/", "shirt", False, 2),
            ("Mobiles", None, "/category/mobiles/", "smartphone", False, 3),
            ("Electronics", None, "/category/electronics/", "laptop", False, 4),
            ("Beauty", None, "/category/beauty/", "sparkle", False, 5),
            ("Home", None, "/category/home/", "lamp", False, 6),
            ("Appliances", None, "/category/appliances/", "tv", False, 7),
            ("Toys & Baby", None, "/category/toys/", "smile", False, 8),
            ("Food & Grocery", None, "/category/grocery/", "utensils", False, 9),
            ("Auto Acc.", None, "/category/auto/", "shield", False, 10),
            ("Sports & Fitness", None, "/category/sports/", "activity", False, 11),
            ("Furniture", None, "/category/furniture/", "armchair", False, 12),
            ("Books & Media", None, "/category/books/", "book-open", False, 13),
            ("2 Wheelers", None, "/category/vehicles/", "bike", False, 14),
        ]
        for title, cat, url, icon, highlight, order in category_nav_data:
            CategoryNavItem.objects.create(
                title=title,
                category=cat,
                custom_url=url,
                icon_name=icon,
                is_highlighted=highlight,
                display_order=order,
                is_active=True,
            )
        self.stdout.write(self.style.SUCCESS("[OK] Seeded 14 Category Sub-Nav items"))

        # 4. Seed Promotional Banners (Flipkart-Style Marquee Carousel)
        PromoBanner.objects.all().delete()
        PromoBanner.objects.create(
            title="VIRAT V1 5G",
            subtitle="CARTIVO | Exclusive",
            price_tag="From ₹14,499",
            description="Now with 128 GB storage",
            badge_text="BIG BACHAT DAYS",
            image_url="https://images.unsplash.com/photo-1598327105666-5b89351aff97?q=80&w=600&auto=format&fit=crop",
            button_text="Buy Now",
            button_url="/products/",
            bg_gradient="linear-gradient(135deg, #090a0f 0%, #171d2c 50%, #0c1017 100%)",
            border_color="rgba(51, 65, 85, 0.8)",
            text_color_theme="dark",
            display_order=1,
            is_active=True,
        )
        PromoBanner.objects.create(
            title="Ortho Slippers",
            subtitle="Cartivo Health Care",
            price_tag="Under ₹499",
            description="Ultra-Soft Cushion Sole",
            badge_text="BIG BACHAT DAYS",
            image_url="https://images.unsplash.com/photo-1608231387042-66d1773070a5?q=80&w=600&auto=format&fit=crop",
            button_text="Grab Deal",
            button_url="/category/footwear/",
            bg_gradient="linear-gradient(135deg, #38bdf8 0%, #22d3ee 50%, #2dd4bf 100%)",
            border_color="#67e8f9",
            text_color_theme="light",
            display_order=2,
            is_active=True,
        )
        PromoBanner.objects.create(
            title="Galaxy Ultra 5G",
            subtitle="Special Tech Launch",
            price_tag="From ₹24,999*",
            description="Snapdragon 8 Gen 3 Processor",
            badge_text="SPECIAL DEAL",
            image_url="https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?q=80&w=600&auto=format&fit=crop",
            button_text="Shop Now",
            button_url="/products/",
            bg_gradient="linear-gradient(135deg, #fbbf24 0%, #fb923c 50%, #f59e0b 100%)",
            border_color="#fcd34d",
            text_color_theme="light",
            display_order=3,
            is_active=True,
        )
        PromoBanner.objects.create(
            title="Titanium Pulse 4",
            subtitle="Luxury Smart Chrono",
            price_tag="Flat 35% Off",
            description="Sapphire crystal glass dial",
            badge_text="FLASH OFFER",
            image_url="https://images.unsplash.com/photo-1523275335684-37898b6baf30?q=80&w=600&auto=format&fit=crop",
            button_text="Explore",
            button_url="/category/timepieces/",
            bg_gradient="linear-gradient(135deg, #064e3b 0%, #0f766e 50%, #022c22 100%)",
            border_color="rgba(16, 185, 129, 0.4)",
            text_color_theme="dark",
            display_order=4,
            is_active=True,
        )
        PromoBanner.objects.create(
            title="Aura Pro Wireless",
            subtitle="Studio Hi-Res Audio",
            price_tag="Under ₹1,999",
            description="Active 40dB Noise Cancellation",
            badge_text="HOT PICK",
            image_url="https://images.unsplash.com/photo-1505740420928-5e560c06d30e?q=80&w=600&auto=format&fit=crop",
            button_text="Shop Audio",
            button_url="/category/audio/",
            bg_gradient="linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #0f172a 100%)",
            border_color="rgba(99, 102, 241, 0.4)",
            text_color_theme="dark",
            display_order=5,
            is_active=True,
        )
        self.stdout.write(self.style.SUCCESS("[OK] Seeded Promotional Banners"))

        # 5. Seed Trust Badges
        TrustBadge.objects.all().delete()
        TrustBadge.objects.create(
            title="Complimentary Delivery",
            subtitle="Free global transit on orders $150+",
            icon_name="truck",
            color_theme="blue",
            display_order=1,
            is_active=True,
        )
        TrustBadge.objects.create(
            title="Secure Payment",
            subtitle="256-bit encrypted checkout",
            icon_name="shield-check",
            color_theme="emerald",
            display_order=2,
            is_active=True,
        )
        TrustBadge.objects.create(
            title="30-Day Returns",
            subtitle="Doorstep pick-up guarantee",
            icon_name="rotate-ccw",
            color_theme="amber",
            display_order=3,
            is_active=True,
        )
        TrustBadge.objects.create(
            title="24/7 Concierge Care",
            subtitle="White-glove shopping assistance",
            icon_name="headphones",
            color_theme="purple",
            display_order=4,
            is_active=True,
        )
        self.stdout.write(self.style.SUCCESS("[OK] Seeded Trust Badges"))

        # 6. Seed Curated Homepage Categories
        HomepageCategoryItem.objects.all().delete()
        HomepageCategoryItem.objects.create(
            category=cat_audio,
            custom_title="Acoustic & Audio",
            custom_subtitle="Headphones, speakers & drivers",
            custom_image_url="https://images.unsplash.com/photo-1546435770-a3e426bf472b?q=80&w=800&auto=format&fit=crop",
            badge_text="18 Products",
            badge_color="blue",
            display_order=1,
            is_active=True,
        )
        HomepageCategoryItem.objects.create(
            category=cat_watches,
            custom_title="Precision Watches",
            custom_subtitle="Automatic & smart chronographs",
            custom_image_url="https://images.unsplash.com/photo-1523275335684-37898b6baf30?q=80&w=800&auto=format&fit=crop",
            badge_text="24 Products",
            badge_color="amber",
            display_order=2,
            is_active=True,
        )
        HomepageCategoryItem.objects.create(
            category=cat_apparel,
            custom_title="Minimal Apparel",
            custom_subtitle="Organic cotton & merino wool",
            custom_image_url="https://images.unsplash.com/photo-1521572267360-ee0c2909d518?q=80&w=800&auto=format&fit=crop",
            badge_text="42 Products",
            badge_color="emerald",
            display_order=3,
            is_active=True,
        )
        HomepageCategoryItem.objects.create(
            category=cat_accessories,
            custom_title="Leather Goods",
            custom_subtitle="Wallets, folios & tech sleeves",
            custom_image_url="https://images.unsplash.com/photo-1627123424574-724758594e93?q=80&w=800&auto=format&fit=crop",
            badge_text="31 Products",
            badge_color="purple",
            display_order=4,
            is_active=True,
        )
        self.stdout.write(self.style.SUCCESS("[OK] Seeded Homepage Category Showcases"))

        # 7. Seed Catalog Products
        Product.objects.all().delete()
        prod1 = Product.objects.create(
            title="Titanium Smart Chronograph",
            slug="titanium-smart-chronograph",
            description="Grade 5 titanium casing with sapphire glass and fitness metrics.",
            category=cat_watches,
            brand=brand_cartivo,
            base_price=Decimal("389.00"),
            compare_at_price=Decimal("440.00"),
            rating=Decimal("5.0"),
            review_count=96,
            badge_text="Best Seller",
            is_trending=True,
            is_featured=True,
            is_active=True,
        )
        ProductImage.objects.create(
            product=prod1,
            image_url="https://images.unsplash.com/photo-1546868871-7041f2a55e12?q=80&w=800&auto=format&fit=crop",
            is_primary=True,
            display_order=1,
        )

        prod2 = Product.objects.create(
            title="Aura ANC Pro Earbuds",
            slug="aura-anc-pro-earbuds",
            description="High-resolution wireless earbuds with hybrid noise-cancellation.",
            category=cat_audio,
            brand=brand_aura,
            base_price=Decimal("199.00"),
            compare_at_price=Decimal("249.00"),
            rating=Decimal("4.8"),
            review_count=64,
            badge_text="-20% Off",
            is_trending=True,
            is_featured=True,
            is_active=True,
        )
        ProductImage.objects.create(
            product=prod2,
            image_url="https://images.unsplash.com/photo-1590658268037-6bf12165a8df?q=80&w=800&auto=format&fit=crop",
            is_primary=True,
            display_order=1,
        )

        prod3 = Product.objects.create(
            title="Atelier Merino Overcoat",
            slug="atelier-merino-overcoat",
            description="Tailored luxury outer layer woven from 100% fine Merino wool.",
            category=cat_apparel,
            brand=brand_cartivo,
            base_price=Decimal("495.00"),
            rating=Decimal("5.0"),
            review_count=38,
            badge_text="New In",
            is_trending=True,
            is_featured=False,
            is_active=True,
        )
        ProductImage.objects.create(
            product=prod3,
            image_url="https://images.unsplash.com/photo-1591047139829-d91aecb6caea?q=80&w=800&auto=format&fit=crop",
            is_primary=True,
            display_order=1,
        )

        prod4 = Product.objects.create(
            title="Saddle Leather Daypack",
            slug="saddle-leather-daypack",
            description="Full-grain vegetable tanned leather backpack for modern commutes.",
            category=cat_accessories,
            brand=brand_cartivo,
            base_price=Decimal("280.00"),
            rating=Decimal("4.9"),
            review_count=112,
            is_trending=True,
            is_featured=True,
            is_active=True,
        )
        ProductImage.objects.create(
            product=prod4,
            image_url="https://images.unsplash.com/photo-1553062407-98eeb64c6a62?q=80&w=800&auto=format&fit=crop",
            is_primary=True,
            display_order=1,
        )
        self.stdout.write(self.style.SUCCESS("[OK] Seeded Catalog Products"))

        # 8. Seed Homepage Section Orchestrator
        HomepageSection.objects.all().delete()
        sec_catbar = HomepageSection.objects.create(
            name="Category Sub-Menu Bar",
            section_type="category_bar",
            display_order=1,
            is_active=True,
        )
        sec_promo = HomepageSection.objects.create(
            name="Flipkart-Style Marquee Carousel",
            section_type="hero_banners",
            display_order=2,
            is_active=True,
        )
        sec_trust = HomepageSection.objects.create(
            name="Value Propositions & Trust Bar",
            section_type="trust_bar",
            display_order=3,
            is_active=True,
        )
        sec_categories = HomepageSection.objects.create(
            name="Curated Categories Grid",
            section_type="curated_categories",
            title="Curated Categories",
            subtitle="Collections",
            view_all_url="/products/",
            view_all_text="Explore All Categories",
            display_order=4,
            is_active=True,
        )
        sec_trending = HomepageSection.objects.create(
            name="Trending Products Grid",
            section_type="product_grid",
            title="Trending This Week",
            subtitle="Handpicked Pieces",
            view_all_url="/products/",
            view_all_text="View All Trending",
            product_filter_type="trending",
            max_items=4,
            display_order=5,
            is_active=True,
        )
        sec_newsletter = HomepageSection.objects.create(
            name="VIP Newsletter Subscription",
            section_type="newsletter",
            display_order=6,
            is_active=True,
        )

        self.stdout.write(self.style.SUCCESS("[OK] All CMS sections successfully seeded!"))
