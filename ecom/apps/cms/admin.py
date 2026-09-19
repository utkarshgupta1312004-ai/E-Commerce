from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    NavbarItem,
    CategoryNavItem,
    PromoBanner,
    HomepageCategoryItem,
    TrustBadge,
    HomepageSection,
    HomepageSectionProduct,
)


class NavbarDropdownInline(admin.TabularInline):
    model = NavbarItem
    fk_name = 'parent'
    extra = 1
    fields = ('title', 'url', 'badge_text', 'badge_color', 'display_order', 'open_in_new_tab', 'is_active')
    verbose_name = 'Dropdown Menu Item'
    verbose_name_plural = 'Dropdown Menu Items'


@admin.register(NavbarItem)
class NavbarItemAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'url',
        'parent',
        'badge_display',
        'display_order',
        'open_in_new_tab',
        'is_active',
    )
    list_filter = ('is_active', ('parent', admin.EmptyFieldListFilter))
    search_fields = ('title', 'url', 'badge_text')
    list_editable = ('display_order', 'is_active')
    ordering = ('display_order', 'id')
    inlines = [NavbarDropdownInline]

    fieldsets = (
        ('Navigation Details', {
            'fields': ('title', 'url', 'parent', 'open_in_new_tab')
        }),
        ('Highlight Badge', {
            'fields': ('badge_text', 'badge_color'),
            'classes': ('collapse',),
        }),
        ('Visibility & Ordering', {
            'fields': ('display_order', 'is_active')
        }),
    )

    def badge_display(self, obj):
        if obj.badge_text:
            return format_html(
                '<span style="background: #fef3c7; color: #b45309; padding: 2px 8px; border-radius: 9999px; font-weight: bold; font-size: 11px;">{}</span>',
                obj.badge_text
            )
        return "-"
    badge_display.short_description = "Badge"


@admin.register(CategoryNavItem)
class CategoryNavItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'effective_url_display', 'icon_name', 'is_highlighted', 'display_order', 'is_active')
    list_filter = ('is_active', 'is_highlighted')
    search_fields = ('title', 'custom_url')
    list_editable = ('display_order', 'is_highlighted', 'is_active')
    ordering = ('display_order', 'id')

    def effective_url_display(self, obj):
        return obj.effective_url
    effective_url_display.short_description = "Target URL"


@admin.register(PromoBanner)
class PromoBannerAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'subtitle',
        'price_tag',
        'badge_text',
        'display_order',
        'is_active',
        'scheduling_status',
        'banner_preview',
    )
    list_filter = ('is_active', 'text_color_theme', 'start_date', 'end_date')
    search_fields = ('title', 'subtitle', 'description', 'badge_text')
    list_editable = ('display_order', 'is_active')
    ordering = ('display_order', '-created_at')

    fieldsets = (
        ('Header & Promotional Copy', {
            'fields': ('title', 'subtitle', 'price_tag', 'description', 'badge_text')
        }),
        ('Images & Media', {
            'fields': ('image', 'image_url', 'mobile_image', 'mobile_image_url')
        }),
        ('Action Button & Link', {
            'fields': ('button_text', 'button_url')
        }),
        ('Theme & Card Styling', {
            'fields': ('bg_gradient', 'border_color', 'text_color_theme'),
            'classes': ('collapse',),
        }),
        ('Scheduling & Publishing', {
            'fields': ('start_date', 'end_date', 'display_order', 'is_active')
        }),
    )

    def scheduling_status(self, obj):
        now = timezone.now()
        if not obj.is_active:
            return format_html('<span style="color: #ef4444; font-weight: 600;">Inactive</span>')
        if obj.start_date and now < obj.start_date:
            return format_html('<span style="color: #f59e0b; font-weight: 600;">Scheduled</span>')
        if obj.end_date and now > obj.end_date:
            return format_html('<span style="color: #94a3b8; font-weight: 600;">Expired</span>')
        return format_html('<span style="color: #10b981; font-weight: 600;">Live</span>')
    scheduling_status.short_description = "Status"

    def banner_preview(self, obj):
        url = obj.effective_image_url
        if url:
            return format_html('<img src="{}" style="height: 40px; width: 60px; object-fit: cover; border-radius: 6px;" />', url)
        return "-"
    banner_preview.short_description = "Image Preview"


@admin.register(HomepageCategoryItem)
class HomepageCategoryItemAdmin(admin.ModelAdmin):
    list_display = ('display_title', 'category', 'badge_text', 'display_order', 'is_active', 'category_preview')
    list_filter = ('is_active',)
    search_fields = ('custom_title', 'category__name')
    list_editable = ('display_order', 'is_active')
    ordering = ('display_order', 'id')

    def category_preview(self, obj):
        url = obj.effective_image_url
        if url:
            return format_html('<img src="{}" style="height: 40px; width: 60px; object-fit: cover; border-radius: 6px;" />', url)
        return "-"
    category_preview.short_description = "Card Preview"


@admin.register(TrustBadge)
class TrustBadgeAdmin(admin.ModelAdmin):
    list_display = ('title', 'subtitle', 'icon_name', 'color_theme', 'display_order', 'is_active')
    list_editable = ('display_order', 'is_active')
    list_filter = ('is_active', 'color_theme')
    search_fields = ('title', 'subtitle')
    ordering = ('display_order', 'id')


class HomepageSectionProductInline(admin.TabularInline):
    model = HomepageSectionProduct
    extra = 1
    fields = ('product', 'display_order', 'is_active')
    ordering = ('display_order', 'id')


@admin.register(HomepageSection)
class HomepageSectionAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'section_type',
        'title',
        'product_filter_type',
        'max_items',
        'display_order',
        'is_active',
    )
    list_filter = ('is_active', 'section_type', 'product_filter_type')
    search_fields = ('name', 'title', 'subtitle')
    list_editable = ('display_order', 'is_active')
    ordering = ('display_order', 'id')
    inlines = [HomepageSectionProductInline]

    fieldsets = (
        ('Section Overview', {
            'fields': ('name', 'section_type', 'title', 'subtitle', 'display_order', 'is_active')
        }),
        ('Action Link', {
            'fields': ('view_all_url', 'view_all_text')
        }),
        ('Product Filter Settings (For Product Grids)', {
            'fields': ('product_filter_type', 'max_items'),
            'description': "If section type is 'Product Grid', choose whether products are chosen dynamically or curated manually using the inline below."
        }),
        ('Custom HTML Block (Optional)', {
            'fields': ('custom_content',),
            'classes': ('collapse',),
        }),
    )
