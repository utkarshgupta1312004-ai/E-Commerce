from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class NavbarItem(models.Model):
    """Dynamic navigation bar item supporting nested dropdown menus and badges."""
    title = models.CharField(max_length=100)
    url = models.CharField(
        max_length=255,
        default="#",
        help_text="Relative URL (e.g., '/products/') or absolute URL (e.g., 'https://...')"
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        help_text="Leave blank for top-level navbar items. Select a parent to create a dropdown child item."
    )
    badge_text = models.CharField(
        max_length=30,
        blank=True,
        help_text="Optional highlight badge text, e.g. '20%', 'Hot', 'New'"
    )
    badge_color = models.CharField(
        max_length=30,
        blank=True,
        default="amber",
        help_text="Color identifier, e.g. 'amber', 'blue', 'rose', 'emerald'"
    )
    open_in_new_tab = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Navbar Item'
        verbose_name_plural = 'Navbar Items'
        ordering = ['display_order', 'id']

    @property
    def is_dropdown(self):
        return self.children.filter(is_active=True).exists()

    def get_active_children(self):
        return self.children.filter(is_active=True).order_by('display_order', 'id')

    def __str__(self):
        if self.parent:
            return f"{self.parent.title} -> {self.title}"
        return self.title


class CategoryNavItem(models.Model):
    """Sticky sub-menu category bar item displayed directly below the navbar."""
    title = models.CharField(max_length=100)
    category = models.ForeignKey(
        'catalog.Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='category_nav_items',
        help_text="Optional linked catalog category."
    )
    custom_url = models.CharField(
        max_length=255,
        blank=True,
        help_text="Custom URL override. If blank and category is selected, uses category URL."
    )
    icon_name = models.CharField(
        max_length=60,
        default="sparkles",
        help_text="Lucide icon name (e.g., 'sparkles', 'shirt', 'smartphone', 'laptop', 'sparkle', 'lamp', 'tv', 'smile', 'utensils', 'shield', 'activity', 'armchair', 'book-open', 'bike')"
    )
    image = models.ImageField(upload_to='category_nav/', blank=True, null=True, help_text="Upload category icon/image saved to media storage")
    image_url = models.URLField(max_length=500, blank=True, help_text="External image URL (e.g. Google image, CDN)")
    is_highlighted = models.BooleanField(
        default=False,
        help_text="Apply active highlight styling (e.g. 'For You' item)"
    )
    is_active = models.BooleanField(default=True, db_index=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Category Sub-Nav Item'
        verbose_name_plural = 'Category Sub-Nav Items'
        ordering = ['display_order', 'id']

    @property
    def effective_url(self):
        if self.custom_url:
            return self.custom_url
        if self.category:
            return self.category.get_absolute_url()
        return "/"

    @property
    def effective_image_url(self):
        if self.image:
            return self.image.url
        if self.image_url:
            return self.image_url
        if self.category and hasattr(self.category, 'effective_image_url'):
            return self.category.effective_image_url
        return ''

    def __str__(self):
        return self.title


class PromoBanner(models.Model):
    """Hero & promotional banner model with scheduling and Flipkart-style aesthetics."""
    TEXT_COLOR_CHOICES = (
        ('dark', 'Dark Card / Light Text'),
        ('light', 'Light Card / Dark Text'),
    )

    title = models.CharField(max_length=200, help_text="Headline, e.g. 'VIRAT V1 5G'")
    subtitle = models.CharField(max_length=200, blank=True, help_text="e.g. 'CARTIVO | Exclusive'")
    price_tag = models.CharField(max_length=100, blank=True, help_text="e.g. 'From ₹14,499' or 'Under ₹499'")
    description = models.TextField(blank=True, help_text="e.g. 'Now with 128 GB storage'")
    badge_text = models.CharField(max_length=100, blank=True, help_text="e.g. 'BIG BACHAT DAYS'")

    image = models.ImageField(upload_to='banners/', blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True, help_text="Fallback CDN image URL")
    mobile_image = models.ImageField(upload_to='banners/mobile/', blank=True, null=True)
    mobile_image_url = models.URLField(max_length=500, blank=True)

    button_text = models.CharField(max_length=60, blank=True, default="Shop Now")
    button_url = models.CharField(max_length=255, blank=True, default="/products/")

    bg_gradient = models.CharField(
        max_length=255,
        default="from-neutral-950 via-slate-900 to-neutral-950",
        help_text="Tailwind gradient classes for background card styling"
    )
    border_color = models.CharField(
        max_length=100,
        blank=True,
        default="border-slate-800/80",
        help_text="Tailwind border class"
    )
    text_color_theme = models.CharField(max_length=20, choices=TEXT_COLOR_CHOICES, default='dark')

    start_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional scheduling start time (UTC). If set, banner will only appear on or after this time."
    )
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional scheduling end time (UTC). If set, banner will expire after this time."
    )

    is_active = models.BooleanField(default=True, db_index=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Promotional Banner'
        verbose_name_plural = 'Promotional Banners'
        ordering = ['display_order', '-created_at']

    def clean(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError({'end_date': 'End date must be after start date.'})

    def is_currently_visible(self):
        if not self.is_active:
            return False
        now = timezone.now()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True

    @property
    def effective_image_url(self):
        if self.image:
            return self.image.url
        return self.image_url or ''

    @property
    def effective_mobile_image_url(self):
        if self.mobile_image:
            return self.mobile_image.url
        return self.mobile_image_url or self.effective_image_url

    @property
    def gradient_style(self):
        val = (self.bg_gradient or '').strip()
        if val.startswith('linear-gradient') or val.startswith('radial-gradient') or val.startswith('#') or val.startswith('rgb'):
            return f"background: {val};"

        val_lower = val.lower()
        if 'emerald' in val_lower or 'teal' in val_lower:
            return 'background: linear-gradient(135deg, #064e3b 0%, #115e59 50%, #022c22 100%);'
        elif 'amber' in val_lower or 'orange' in val_lower:
            return 'background: linear-gradient(135deg, #fbbf24 0%, #fb923c 50%, #f59e0b 100%);'
        elif 'sky' in val_lower or 'cyan' in val_lower:
            return 'background: linear-gradient(135deg, #38bdf8 0%, #22d3ee 50%, #2dd4bf 100%);'
        elif 'indigo' in val_lower or 'purple' in val_lower or 'violet' in val_lower:
            return 'background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #0f172a 100%);'
        elif 'rose' in val_lower or 'red' in val_lower:
            return 'background: linear-gradient(135deg, #9f1239 0%, #e11d48 50%, #881337 100%);'
        elif 'neutral' in val_lower or 'slate' in val_lower or 'dark' in val_lower:
            return 'background: linear-gradient(135deg, #0a0a0c 0%, #1e293b 50%, #0a0a0c 100%);'

        return 'background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);'

    @property
    def card_border_style(self):
        val = (self.border_color or '').strip()
        if val.startswith('#') or val.startswith('rgb'):
            return f"border-color: {val};"
        val_lower = val.lower()
        if 'cyan' in val_lower:
            return 'border-color: #67e8f9;'
        elif 'amber' in val_lower:
            return 'border-color: #fcd34d;'
        elif 'emerald' in val_lower:
            return 'border-color: rgba(16, 185, 129, 0.5);'
        elif 'indigo' in val_lower:
            return 'border-color: rgba(99, 102, 241, 0.5);'
        return 'border-color: rgba(51, 65, 85, 0.8);'

    def __str__(self):
        return self.title


class HomepageCategoryItem(models.Model):
    """Curated category card specifically configured for homepage showcases."""
    category = models.ForeignKey(
        'catalog.Category',
        on_delete=models.CASCADE,
        related_name='homepage_curations'
    )
    custom_title = models.CharField(max_length=120, blank=True, help_text="Optional override for card title")
    custom_subtitle = models.CharField(max_length=200, blank=True, help_text="e.g. 'Headphones, speakers & drivers'")
    custom_image = models.ImageField(upload_to='homepage/categories/', blank=True, null=True)
    custom_image_url = models.URLField(max_length=500, blank=True, help_text="Fallback card image URL")
    badge_text = models.CharField(max_length=60, blank=True, help_text="e.g. '18 Products'")
    badge_color = models.CharField(max_length=30, blank=True, default="blue", help_text="e.g. 'blue', 'amber', 'emerald', 'purple'")
    link_url = models.CharField(max_length=255, blank=True, help_text="Override target URL")

    is_active = models.BooleanField(default=True, db_index=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Homepage Category Showcase'
        verbose_name_plural = 'Homepage Category Showcases'
        ordering = ['display_order', 'id']

    @property
    def display_title(self):
        return self.custom_title or self.category.name

    @property
    def effective_image_url(self):
        if self.custom_image:
            return self.custom_image.url
        if self.custom_image_url:
            return self.custom_image_url
        return self.category.effective_image_url

    @property
    def effective_url(self):
        if self.link_url:
            return self.link_url
        return self.category.get_absolute_url()

    def __str__(self):
        return f"{self.display_title} ({self.category.name})"


class TrustBadge(models.Model):
    """Value proposition / trust proposition badge item."""
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=200)
    icon_name = models.CharField(
        max_length=60,
        default="truck",
        help_text="Lucide icon name (e.g. 'truck', 'shield-check', 'rotate-ccw', 'headphones')"
    )
    color_theme = models.CharField(
        max_length=40,
        default="blue",
        help_text="Theme name ('blue', 'emerald', 'amber', 'purple')"
    )
    is_active = models.BooleanField(default=True, db_index=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Trust Badge / Value Proposition'
        verbose_name_plural = 'Trust Badges / Value Propositions'
        ordering = ['display_order', 'id']

    def __str__(self):
        return self.title


class HomepageSection(models.Model):
    """Central orchestrator model controlling the composition and order of homepage sections."""
    SECTION_TYPES = (
        ('category_bar', 'Category Sub-Menu Bar'),
        ('hero_banners', 'Promotional Marquee Carousel Banners'),
        ('trust_bar', 'Value Propositions / Trust Bar'),
        ('curated_categories', 'Curated Categories Grid'),
        ('product_grid', 'Product Grid Section (Trending / Featured / New)'),
        ('newsletter', 'VIP Newsletter Subscription Block'),
        ('custom_html', 'Custom HTML Block'),
    )

    FILTER_TYPES = (
        ('trending', 'Trending Products'),
        ('featured', 'Featured Products'),
        ('new_arrivals', 'New Arrivals (Latest Added)'),
        ('manual', 'Manual Product Selection'),
    )

    name = models.CharField(max_length=120, help_text="Internal label (e.g. 'Homepage Trending Section')")
    section_type = models.CharField(max_length=40, choices=SECTION_TYPES, db_index=True)
    title = models.CharField(max_length=150, blank=True, help_text="Section headline, e.g. 'Trending This Week'")
    subtitle = models.CharField(max_length=150, blank=True, help_text="Section tag/kicker, e.g. 'Handpicked Pieces'")
    view_all_url = models.CharField(max_length=255, blank=True, default="/products/")
    view_all_text = models.CharField(max_length=60, blank=True, default="Explore All")

    # Product grid specific settings
    product_filter_type = models.CharField(
        max_length=30,
        choices=FILTER_TYPES,
        default='trending',
        help_text="How products should be selected if section_type is product_grid"
    )
    max_items = models.PositiveIntegerField(default=4, help_text="Maximum products to display")

    # Custom HTML content if section_type is custom_html
    custom_content = models.TextField(blank=True, help_text="HTML snippet if custom_html section type is chosen")

    # Section Image / Banner (File Upload or External/Google URL)
    image = models.ImageField(upload_to='sections/', blank=True, null=True, help_text="Upload section banner/image saved to media storage")
    image_url = models.URLField(max_length=500, blank=True, help_text="External or Google image URL")

    is_active = models.BooleanField(default=True, db_index=True)
    display_order = models.PositiveIntegerField(default=0, help_text="Controls top-to-bottom rendering order on homepage")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Homepage Section'
        verbose_name_plural = 'Homepage Sections'
        ordering = ['display_order', 'id']

    @property
    def effective_image_url(self):
        if self.image:
            return self.image.url
        return self.image_url or ''

    def get_products(self):
        """Retrieve resolved product queryset for this section."""
        from apps.catalog.models import Product
        if self.section_type != 'product_grid':
            return Product.objects.none()

        if self.product_filter_type == 'manual':
            section_products = self.section_products.filter(
                is_active=True,
                product__is_active=True
            ).select_related('product', 'product__category').prefetch_related('product__images').order_by('display_order')
            return [sp.product for sp in section_products[:self.max_items]]

        qs = Product.objects.filter(is_active=True).select_related('category', 'brand').prefetch_related('images')
        if self.product_filter_type == 'trending':
            qs = qs.filter(is_trending=True)
        elif self.product_filter_type == 'featured':
            qs = qs.filter(is_featured=True)
        elif self.product_filter_type == 'new_arrivals':
            qs = qs.order_by('-created_at')

        return qs[:self.max_items]

    def __str__(self):
        return f"[{self.display_order}] {self.name} ({self.get_section_type_display()})"


class HomepageSectionProduct(models.Model):
    """Through-model for manually assigned products to a HomepageSection."""
    section = models.ForeignKey(
        HomepageSection,
        on_delete=models.CASCADE,
        related_name='section_products'
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='homepage_section_assignments'
    )
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Section Product'
        verbose_name_plural = 'Section Products'
        ordering = ['display_order', 'id']
        unique_together = ('section', 'product')

    def __str__(self):
        return f"{self.section.name} -> {self.product.title}"
