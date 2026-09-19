from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Category,
    Brand,
    ProductTag,
    Attribute,
    AttributeValue,
    Product,
    ProductVariant,
    VariantAttributeValue,
    ProductImage,
)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'image_url', 'alt_text', 'is_primary', 'display_order', 'preview')
    readonly_fields = ('preview',)

    def preview(self, obj):
        url = obj.effective_image_url
        if url:
            return format_html('<img src="{}" style="height: 50px; border-radius: 6px;" />', url)
        return "-"


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ('sku', 'name', 'price', 'compare_at_price', 'barcode', 'is_active', 'display_order')


class VariantAttributeValueInline(admin.TabularInline):
    model = VariantAttributeValue
    extra = 1


class AttributeValueInline(admin.TabularInline):
    model = AttributeValue
    extra = 2
    fields = ('value', 'display_order')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'icon_name', 'display_order', 'is_active', 'image_preview')
    list_filter = ('is_active', 'parent')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('display_order', 'is_active')
    ordering = ('display_order', 'name')

    def image_preview(self, obj):
        url = obj.effective_image_url
        if url:
            return format_html('<img src="{}" style="height: 36px; border-radius: 4px;" />', url)
        return "-"
    image_preview.short_description = "Image"


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(ProductTag)
class ProductTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'display_order')
    search_fields = ('name', 'code')
    prepopulated_fields = {'code': ('name',)}
    inlines = [AttributeValueInline]


@admin.register(AttributeValue)
class AttributeValueAdmin(admin.ModelAdmin):
    list_display = ('attribute', 'value', 'display_order')
    list_filter = ('attribute',)
    search_fields = ('value', 'attribute__name')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'sku',
        'category',
        'brand',
        'base_price',
        'compare_at_price',
        'status',
        'visibility',
        'is_featured',
        'is_active',
        'product_preview',
    )
    list_filter = ('status', 'visibility', 'is_featured', 'is_trending', 'category', 'brand')
    search_fields = ('title', 'slug', 'sku', 'description')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('status', 'visibility', 'is_featured')
    inlines = [ProductImageInline, ProductVariantInline]
    filter_horizontal = ('tags',)

    def product_preview(self, obj):
        url = obj.primary_image_url
        if url:
            return format_html('<img src="{}" style="height: 40px; width: 40px; object-fit: cover; border-radius: 6px;" />', url)
        return "-"
    product_preview.short_description = "Image"


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('sku', 'product', 'name', 'price', 'is_active')
    list_filter = ('is_active', 'product__category')
    search_fields = ('sku', 'name', 'product__title', 'barcode')
    inlines = [VariantAttributeValueInline]


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'is_primary', 'display_order', 'preview')
    list_filter = ('is_primary',)

    def preview(self, obj):
        url = obj.effective_image_url
        if url:
            return format_html('<img src="{}" style="height: 40px; border-radius: 4px;" />', url)
        return "-"
