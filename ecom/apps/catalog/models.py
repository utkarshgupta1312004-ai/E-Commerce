from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify
from django.utils import timezone


class Category(models.Model):
    """
    Product catalog category model supporting hierarchical trees.
    Supports parent-child subcategories with cycle detection.
    """
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=150, unique=True, db_index=True)
    description = models.TextField(blank=True)
    icon_name = models.CharField(
        max_length=60,
        blank=True,
        help_text="Lucide icon identifier, e.g., 'shirt', 'laptop', 'sparkles'."
    )
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True, help_text="Direct or CDN image URL fallback")
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    is_active = models.BooleanField(default=True, db_index=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['display_order', 'name']

    def clean(self):
        if self.parent and self.pk and self.parent_id == self.pk:
            raise ValidationError({'parent': "A category cannot be its own parent."})
        # Check circular ancestor loop
        curr = self.parent
        while curr:
            if self.pk and curr.pk == self.pk:
                raise ValidationError({'parent': "Circular category hierarchy detected."})
            curr = curr.parent

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def effective_image_url(self):
        if self.image:
            return self.image.url
        return self.image_url or ''

    @property
    def product_count(self):
        return self.products.filter(status='ACTIVE', visibility='PUBLIC').count()

    @property
    def total_product_count(self):
        cat_ids = [self.id] + list(self.children.filter(is_active=True).values_list('id', flat=True))
        return Product.objects.filter(
            category_id__in=cat_ids,
            status='ACTIVE',
            visibility='PUBLIC',
            is_active=True
        ).count()

    def get_ancestors(self):
        ancestors = []
        curr = self.parent
        while curr:
            ancestors.append(curr)
            curr = curr.parent
        return list(reversed(ancestors))

    def get_children(self):
        return self.children.filter(is_active=True).order_by('display_order', 'name')

    def get_absolute_url(self):
        return f"/category/{self.slug}/"

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


class Brand(models.Model):
    """Product manufacturer brand model."""
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=150, unique=True, db_index=True)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True)
    logo_url = models.URLField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Brand'
        verbose_name_plural = 'Brands'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def effective_logo_url(self):
        if self.logo:
            return self.logo.url
        return self.logo_url or ''

    @property
    def product_count(self):
        return self.products.filter(status='ACTIVE', visibility='PUBLIC').count()

    def __str__(self):
        return self.name


class ProductTag(models.Model):
    """Flexible categorization tags (e.g. 'New', 'Bestseller', 'Trending', 'Summer')."""
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Product Tag'
        verbose_name_plural = 'Product Tags'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Attribute(models.Model):
    """
    Defines configurable variant attribute types (e.g. 'Color', 'Size', 'Storage', 'RAM').
    """
    name = models.CharField(max_length=80)
    code = models.SlugField(max_length=80, unique=True, db_index=True, help_text="Unique identifier e.g. 'color', 'storage'")
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Attribute'
        verbose_name_plural = 'Attributes'
        ordering = ['display_order', 'name']

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class AttributeValue(models.Model):
    """
    Individual values for an attribute (e.g. 'Black', 'White', '256GB', '512GB').
    """
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE, related_name='values')
    value = models.CharField(max_length=100)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Attribute Value'
        verbose_name_plural = 'Attribute Values'
        ordering = ['display_order', 'value']
        unique_together = ('attribute', 'value')

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


class Product(models.Model):
    """
    Product Master: Represents the foundational product entity in Cartivo.
    Defines what the product is (pricing, metadata, category, brand, attributes).
    Does NOT store stock quantity (decoupled for Inventory).
    """
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('ACTIVE', 'Active'),
        ('ARCHIVED', 'Archived'),
    )
    VISIBILITY_CHOICES = (
        ('PUBLIC', 'Public'),
        ('HIDDEN', 'Hidden'),
    )
    PRODUCT_TYPE_CHOICES = (
        ('standard', 'Standard Product'),
        ('variable', 'Variable Product'),
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, db_index=True)
    short_description = models.CharField(max_length=300, blank=True, default="")
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products'
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )
    product_type = models.CharField(max_length=50, choices=PRODUCT_TYPE_CHOICES, default='standard')
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Original price for strike-through discount display"
    )
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Internal acquisition cost (staff only, never exposed to customers)"
    )
    sku = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        db_index=True,
        help_text="Primary SKU for standalone products without variants"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE', db_index=True)
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='PUBLIC', db_index=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.0)
    review_count = models.PositiveIntegerField(default=0)
    badge_text = models.CharField(
        max_length=60,
        blank=True,
        help_text="e.g. 'Best Seller', '-20% Off', 'New In'"
    )
    is_featured = models.BooleanField(default=False, db_index=True)
    is_trending = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True, help_text="Synchronized with status == ACTIVE")
    tags = models.ManyToManyField(ProductTag, blank=True, related_name='products')
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if self.sku:
            self.sku = self.sku.strip().upper()
        # Synchronize is_active flag with status
        self.is_active = bool(self.status == 'ACTIVE')
        if self.status == 'ACTIVE' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def name(self):
        """Alias for title to guarantee 100% interoperability across all apps."""
        return self.title

    @name.setter
    def name(self, val):
        self.title = val

    @property
    def price(self):
        """Alias for base_price to guarantee interoperability across all apps."""
        return self.base_price

    @property
    def effective_price(self):
        return self.base_price

    @property
    def primary_image_url(self):
        primary = self.images.filter(is_primary=True).first() or self.images.first()
        if primary:
            return primary.effective_image_url
        return ''

    @property
    def effective_sku(self):
        if self.sku:
            return self.sku
        first_variant = self.variants.filter(is_active=True).first()
        if first_variant:
            return first_variant.sku
        return '—'

    @property
    def discount_percentage(self):
        """Calculates discount percentage safely using Decimal values."""
        if self.compare_at_price and self.compare_at_price > self.base_price:
            discount = ((self.compare_at_price - self.base_price) / self.compare_at_price) * Decimal('100')
            return int(discount.quantize(Decimal('1')))
        return 0

    @property
    def is_purchasable(self):
        return self.status == 'ACTIVE' and self.visibility == 'PUBLIC' and self.is_active and self.is_in_stock

    @property
    def total_available_stock(self) -> int:
        try:
            records = self.stock_records.all()
            if records.exists():
                return sum(s.available_quantity for s in records)
            return 0
        except Exception:
            return 0

    @property
    def is_in_stock(self) -> bool:
        return self.total_available_stock > 0

    @property
    def is_low_stock(self) -> bool:
        qty = self.total_available_stock
        return 0 < qty <= 10

    @property
    def has_variants(self):
        return self.variants.filter(is_active=True).exists()

    def get_absolute_url(self):
        return f"/products/{self.slug}/"

    def __str__(self):
        return self.title


class ProductVariant(models.Model):
    """
    Represents a specific sellable variant combination of a Product (e.g. 256GB / Black).
    Holds the unique SKU that will later be referenced by Inventory and Orders.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    sku = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Unique Stock Keeping Unit (e.g. IP17-256-BLK)"
    )
    name = models.CharField(max_length=200, blank=True, help_text="e.g. '256GB / Black'")
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Override base price if different"
    )
    compare_at_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Internal variant cost"
    )
    barcode = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Product Variant'
        verbose_name_plural = 'Product Variants'
        ordering = ['display_order', 'sku']

    def save(self, *args, **kwargs):
        if self.sku:
            self.sku = self.sku.strip().upper()
        super().save(*args, **kwargs)

    @property
    def effective_price(self):
        return self.price if self.price is not None else self.product.base_price

    @property
    def discount_percentage(self):
        comp = self.compare_at_price or self.product.compare_at_price
        price = self.effective_price
        if comp and comp > price:
            disc = ((comp - price) / comp) * Decimal('100')
            return int(disc.quantize(Decimal('1')))
        return 0

    @property
    def available_stock(self) -> int:
        try:
            records = self.stock_records.all()
            if records.exists():
                return sum(s.available_quantity for s in records)
            return 0
        except Exception:
            return 0

    @property
    def is_in_stock(self) -> bool:
        return self.available_stock > 0

    def get_attribute_string(self):
        pairs = [f"{av.attribute.name}: {av.attribute_value.value}" for av in self.attribute_values.select_related('attribute', 'attribute_value')]
        return " / ".join(pairs) if pairs else self.name or "Standard"

    def __str__(self):
        return f"{self.product.title} - {self.sku} ({self.name or self.get_attribute_string()})"


class VariantAttributeValue(models.Model):
    """
    Connects a ProductVariant to its specific AttributeValues (e.g. Variant -> Color: Black).
    """
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='attribute_values')
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE)
    attribute_value = models.ForeignKey(AttributeValue, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Variant Attribute Value'
        verbose_name_plural = 'Variant Attribute Values'
        unique_together = ('variant', 'attribute')

    def __str__(self):
        return f"{self.variant.sku} - {self.attribute.name}: {self.attribute_value.value}"


class ProductImage(models.Model):
    """Product gallery image model supporting multiple ordered images."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True, help_text="Fallback CDN or image URL")
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'
        ordering = ['display_order', 'id']

    @property
    def effective_image_url(self):
        if self.image:
            return self.image.url
        return self.image_url or ''

    def __str__(self):
        return f"Image for {self.product.title}"
