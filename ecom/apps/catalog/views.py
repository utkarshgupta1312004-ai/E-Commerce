import json
from decimal import Decimal
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, F, Case, When, Value, DecimalField, IntegerField
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.text import slugify
from django.utils import timezone

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


def _check_catalog_access(request):
    """
    Validates that user is either a Django Super Administrator or has an active
    staff session account for the 'catalog' department.
    """
    try:
        if request.user.is_authenticated and request.user.is_superuser:
            return True
        dept_slug = request.session.get('department_slug')
        account_id = request.session.get('department_account_id')
        if dept_slug == 'catalog' and account_id:
            from apps.core.models import DepartmentAccount
            account = DepartmentAccount.objects.filter(
                id=account_id,
                department__slug='catalog',
                status=DepartmentAccount.STATUS_ACTIVE
            ).first()
            if account:
                return True
        return False
    except Exception:
        return False


def _get_catalog_staff_context(request, active_tab='dashboard'):
    """Shared base context for the Catalog management console."""
    is_staff = bool(request.session.get('department_slug') == 'catalog')
    dept_name = request.session.get('department_name', 'Catalog & Product Master')
    login_id = request.session.get('department_login_id', 'CAT-STAFF')
    operator_name = request.session.get('department_operator_name', '')

    try:
        sidebar_product_count = Product.objects.count()
        sidebar_category_count = Category.objects.count()
        sidebar_brand_count = Brand.objects.count()
        sidebar_attr_count = Attribute.objects.count()
    except Exception:
        sidebar_product_count = 0
        sidebar_category_count = 0
        sidebar_brand_count = 0
        sidebar_attr_count = 0

    return {
        'is_catalog_staff': is_staff,
        'department_name': dept_name,
        'department_login_id': login_id,
        'department_operator_name': operator_name,
        'is_superadmin': request.user.is_authenticated and request.user.is_superuser,
        'active_tab': active_tab,
        'sidebar_product_count': sidebar_product_count,
        'sidebar_category_count': sidebar_category_count,
        'sidebar_brand_count': sidebar_brand_count,
        'sidebar_attr_count': sidebar_attr_count,
    }


# ==============================================================================
# 1. CUSTOMER STOREFRONT VIEWS
# ==============================================================================

def product_list_view(request, category_slug=None):
    """
    Customer storefront product catalog with faceted filtering, search,
    multiple sorting options, and pagination. Exposes only ACTIVE and PUBLIC products.
    """
    queryset = Product.objects.filter(
        status='ACTIVE',
        visibility='PUBLIC',
        is_active=True
    ).select_related('category', 'brand').prefetch_related('images', 'variants', 'tags')

    # Category Filter (supports URL slug parameter or GET query parameter)
    if not category_slug:
        category_slug = request.GET.get('category', '').strip()
    current_category = None
    if category_slug:
        current_category = Category.objects.filter(slug=category_slug, is_active=True).first()
        if current_category:
            cat_ids = [current_category.id] + list(current_category.children.filter(is_active=True).values_list('id', flat=True))
            queryset = queryset.filter(category_id__in=cat_ids)

    # Brand Filter
    brand_slug = request.GET.get('brand', '').strip()
    current_brand = None
    if brand_slug:
        current_brand = Brand.objects.filter(slug=brand_slug, is_active=True).first()
        if current_brand:
            queryset = queryset.filter(brand=current_brand)

    # Tag Filter
    tag_slug = request.GET.get('tag', '').strip()
    current_tag = None
    if tag_slug:
        current_tag = ProductTag.objects.filter(slug=tag_slug).first()
        if current_tag:
            queryset = queryset.filter(tags=current_tag)

    # Price Filtering
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    if min_price:
        try:
            queryset = queryset.filter(base_price__gte=Decimal(min_price))
        except Exception:
            pass
    if max_price:
        try:
            queryset = queryset.filter(base_price__lte=Decimal(max_price))
        except Exception:
            pass

    # Rating Filter
    min_rating = request.GET.get('rating', '').strip()
    if min_rating:
        try:
            queryset = queryset.filter(rating__gte=Decimal(min_rating))
        except Exception:
            pass

    # Search query
    q = request.GET.get('q', '').strip()
    if q:
        queryset = queryset.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(brand__name__icontains=q) |
            Q(sku__icontains=q) |
            Q(variants__sku__icontains=q)
        ).distinct()

    # Enhanced Sorting Options
    SORT_CHOICES = [
        ('newest', 'Featured & Newest'),
        ('price_low', 'Price: Low to High'),
        ('price_high', 'Price: High to Low'),
        ('discount', 'Biggest Discounts (% Off)'),
        ('rating', 'Customer Rating: High to Low'),
        ('popular', 'Most Popular & Reviews'),
        ('name_asc', 'Alphabetical: A to Z'),
        ('name_desc', 'Alphabetical: Z to A'),
    ]
    sort = request.GET.get('sort', 'newest').strip()
    if sort == 'price_low':
        queryset = queryset.order_by('base_price', '-created_at')
    elif sort == 'price_high':
        queryset = queryset.order_by('-base_price', '-created_at')
    elif sort == 'discount':
        queryset = queryset.annotate(
            has_discount=Case(
                When(compare_at_price__gt=F('base_price'), then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            ),
            discount_amount=Case(
                When(compare_at_price__gt=F('base_price'), then=F('compare_at_price') - F('base_price')),
                default=Value(Decimal('0.00')),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ).order_by('-has_discount', '-discount_amount', '-created_at')
    elif sort == 'rating':
        queryset = queryset.order_by('-rating', '-review_count', '-created_at')
    elif sort == 'popular':
        queryset = queryset.order_by('-review_count', '-rating', '-created_at')
    elif sort == 'name_asc':
        queryset = queryset.order_by('title')
    elif sort == 'name_desc':
        queryset = queryset.order_by('-title')
    else:  # newest
        queryset = queryset.order_by('-is_featured', '-created_at')

    current_sort_label = dict(SORT_CHOICES).get(sort, 'Featured & Newest')

    total_count = queryset.count()

    # Pagination: 12 products per page
    paginator = Paginator(queryset, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Filter Sidebar Metadata
    root_categories = Category.objects.filter(is_active=True, parent__isnull=True).prefetch_related('children').order_by('display_order', 'name')
    available_brands = Brand.objects.filter(is_active=True).annotate(
        p_count=Count('products', filter=Q(products__status='ACTIVE', products__visibility='PUBLIC', products__is_active=True))
    ).filter(p_count__gt=0).order_by('name')
    popular_tags = ProductTag.objects.annotate(
        p_count=Count('products', filter=Q(products__status='ACTIVE', products__visibility='PUBLIC', products__is_active=True))
    ).filter(p_count__gt=0).order_by('-p_count')[:8]

    # Active filters detection for chips UI
    has_active_filters = bool(current_category or current_brand or current_tag or min_price or max_price or min_rating or q)
    active_filters_count = sum([
        1 if current_category else 0,
        1 if current_brand else 0,
        1 if current_tag else 0,
        1 if (min_price or max_price) else 0,
        1 if min_rating else 0,
        1 if q else 0,
    ])

    user_wishlist_product_ids = set()
    if request.user.is_authenticated:
        from apps.wishlist.services import WishlistService
        user_wishlist_product_ids = WishlistService.get_user_wishlist_product_ids(request.user)

    context = {
        'page_obj': page_obj,
        'products': page_obj.object_list,
        'total_count': total_count,
        'user_wishlist_product_ids': user_wishlist_product_ids,
        'root_categories': root_categories,
        'available_brands': available_brands,
        'popular_tags': popular_tags,
        'current_category': current_category,
        'current_brand': current_brand,
        'current_tag': current_tag,
        'selected_category_slug': category_slug,
        'selected_brand_slug': brand_slug,
        'selected_tag_slug': tag_slug,
        'min_price': min_price,
        'max_price': max_price,
        'min_rating': min_rating,
        'sort': sort,
        'sort_choices': SORT_CHOICES,
        'current_sort_label': current_sort_label,
        'has_active_filters': has_active_filters,
        'active_filters_count': active_filters_count,
        'q': q,
    }
    return render(request, 'catalog/storefront/product_list.html', context)


def product_detail_view(request, slug):
    """
    Product detail view with dynamic gallery images, interactive variant selectors,
    specifications table, discount percentage calculation, and add-to-cart hook.
    """
    is_staff = _check_catalog_access(request)
    product_qs = Product.objects.select_related('category', 'brand').prefetch_related(
        'images',
        'tags',
        'variants__attribute_values__attribute',
        'variants__attribute_values__attribute_value',
        'variants__stock_records'
    )

    if not is_staff:
        product = get_object_or_404(product_qs, slug=slug, status='ACTIVE', visibility='PUBLIC')
    else:
        product = get_object_or_404(product_qs, slug=slug)

    # Active variants
    variants = list(product.variants.filter(is_active=True).order_by('display_order', 'id'))

    # Build client-side JSON variant matrix for interactive instant price/SKU updates
    variants_json = []
    attributes_map = {}  # { 'Color': ['Black', 'White'], 'Storage': ['256GB', '512GB'] }

    for v in variants:
        attrs = {}
        for vav in v.attribute_values.all():
            attr_name = vav.attribute.name
            val = vav.attribute_value.value
            attrs[attr_name] = val
            if attr_name not in attributes_map:
                attributes_map[attr_name] = []
            if val not in attributes_map[attr_name]:
                attributes_map[attr_name].append(val)

        effective_compare_price = v.compare_at_price or product.compare_at_price
        variants_json.append({
            'id': v.id,
            'sku': v.sku,
            'name': v.name,
            'price': str(v.effective_price),
            'compare_at_price': str(effective_compare_price or '') if effective_compare_price else '',
            'discount': v.discount_percentage,
            'attributes': attrs,
            'available_stock': v.available_stock,
            'is_in_stock': v.is_in_stock,
        })

    # Related products from same category
    related_products = Product.objects.filter(
        category=product.category,
        status='ACTIVE',
        visibility='PUBLIC',
        is_active=True
    ).exclude(id=product.id).select_related('category').prefetch_related('images')[:4]

    # Integrated Reviews & Ratings
    from apps.reviews.services import ReviewService
    from apps.reviews.models import Review

    review_sort = request.GET.get('review_sort', 'recent')
    reviews_qs = product.reviews.filter(status=Review.STATUS_APPROVED).select_related(
        'user', 'variant'
    ).prefetch_related('replies__user', 'media')

    if review_sort == 'highest':
        reviews_qs = reviews_qs.order_by('-rating', '-created_at')
    elif review_sort == 'lowest':
        reviews_qs = reviews_qs.order_by('rating', '-created_at')
    elif review_sort == 'helpful':
        reviews_qs = reviews_qs.order_by('-helpful_count', '-created_at')
    else:  # recent
        reviews_qs = reviews_qs.order_by('-created_at')

    reviews_paginator = Paginator(reviews_qs, 6)
    reviews_page_number = request.GET.get('review_page', 1)
    reviews_page_obj = reviews_paginator.get_page(reviews_page_number)

    review_summary = ReviewService.get_product_review_summary(product)

    # Check if authenticated customer has already reviewed this product
    user_review = None
    is_verified_buyer = False
    can_manage_reviews = ReviewService.can_manage_reviews(request.user, request)
    is_in_wishlist = False

    if request.user.is_authenticated:
        user_review = product.reviews.filter(user=request.user).first()
        is_verified_buyer, _ = ReviewService.check_verified_purchase(request.user, product)
        from apps.wishlist.services import WishlistService
        is_in_wishlist = WishlistService.is_in_wishlist(request.user, product)

    context = {
        'product': product,
        'images': list(product.images.all()),
        'variants': variants,
        'variants_json': json.dumps(variants_json),
        'attributes_map': attributes_map,
        'related_products': related_products,
        'is_staff_view': is_staff,
        'is_in_wishlist': is_in_wishlist,
        'reviews': reviews_page_obj.object_list,
        'reviews_page_obj': reviews_page_obj,
        'review_summary': review_summary,
        'review_sort': review_sort,
        'user_review': user_review,
        'is_verified_buyer': is_verified_buyer,
        'can_manage_reviews': can_manage_reviews,
    }
    return render(request, 'catalog/storefront/product_detail.html', context)


def category_detail_view(request, slug):
    """Storefront category view filtering products by category slug."""
    return product_list_view(request, category_slug=slug)


def product_buy_now_view(request, slug):
    """
    Simulates direct customer purchase of a product or product variant.
    Decreases stock atomically using InventoryService.purchase_product.
    When stock reaches 0, the product automatically displays as 'Out of Stock'
    and purchasing is disabled on the storefront.
    """
    if request.method != 'POST':
        return redirect('catalog:product_detail', slug=slug)

    product = get_object_or_404(Product, slug=slug)

    quantity_str = request.POST.get('quantity', '1')
    try:
        quantity = max(1, int(quantity_str))
    except (ValueError, TypeError):
        quantity = 1

    variant_id = request.POST.get('variant_id')
    variant = None
    if variant_id:
        try:
            variant = product.variants.filter(id=int(variant_id), is_active=True).first()
        except (ValueError, TypeError):
            variant = None

    from apps.inventory.services import InventoryService, InsufficientStockError, StockValidationError

    try:
        stock = InventoryService.purchase_product(
            product=product,
            quantity=quantity,
            variant=variant,
            performed_by=request.user if request.user.is_authenticated else None
        )
        remaining = product.total_available_stock
        if remaining == 0:
            messages.success(
                request,
                f"🎉 Order Placed! You purchased {quantity}x '{product.title}'. "
                f"Stock has reached 0 — this item is now OUT OF STOCK."
            )
        else:
            messages.success(
                request,
                f"🎉 Order Placed! You purchased {quantity}x '{product.title}'. "
                f"Remaining available stock: {remaining} unit(s)."
            )
    except InsufficientStockError as e:
        messages.error(request, f"⚠️ Unable to complete purchase: {e}")
    except StockValidationError as e:
        messages.error(request, f"⚠️ Invalid purchase request: {e}")
    except Exception as e:
        messages.error(request, f"⚠️ An unexpected error occurred: {e}")

    return redirect('catalog:product_detail', slug=slug)



# ==============================================================================
# 2. CATALOG MANAGEMENT DASHBOARD & CONSOLE VIEWS
# ==============================================================================

def catalog_dashboard_view(request):
    """
    Catalog Executive Dashboard (/catalog/dashboard/).
    Displays real-time database KPIs, quick alerts, recent products, and taxonomy summaries.
    """
    if not _check_catalog_access(request):
        messages.error(request, "Access restricted to Catalog Staff and Super Administrators.")
        return redirect('management:portal')

    context = _get_catalog_staff_context(request, active_tab='dashboard')

    # Real Database KPI Counts
    total_products = Product.objects.count()
    active_products = Product.objects.filter(status='ACTIVE').count()
    draft_products = Product.objects.filter(status='DRAFT').count()
    archived_products = Product.objects.filter(status='ARCHIVED').count()
    total_categories = Category.objects.count()
    total_brands = Brand.objects.count()
    total_variants = ProductVariant.objects.count()
    featured_products = Product.objects.filter(is_featured=True).count()

    # Data lists
    recent_products = Product.objects.select_related('category', 'brand').prefetch_related('images', 'variants').order_by('-created_at')[:6]
    recently_updated = Product.objects.select_related('category', 'brand').order_by('-updated_at')[:5]
    drafts_list = Product.objects.filter(status='DRAFT').select_related('category', 'brand')[:5]
    missing_images = Product.objects.filter(images__isnull=True).distinct()[:5]
    missing_skus = Product.objects.filter(sku__isnull=True, variants__isnull=True).distinct()[:5]

    category_overview = Category.objects.filter(parent__isnull=True).annotate(p_count=Count('products')).order_by('-p_count')[:6]
    brand_overview = Brand.objects.annotate(p_count=Count('products')).order_by('-p_count')[:6]

    context.update({
        'total_products': total_products,
        'active_products': active_products,
        'draft_products': draft_products,
        'archived_products': archived_products,
        'total_categories': total_categories,
        'total_brands': total_brands,
        'total_variants': total_variants,
        'featured_products': featured_products,
        'recent_products': recent_products,
        'recently_updated': recently_updated,
        'drafts_list': drafts_list,
        'missing_images': missing_images,
        'missing_skus': missing_skus,
        'category_overview': category_overview,
        'brand_overview': brand_overview,
    })
    return render(request, 'catalog/manage/dashboard.html', context)


def product_admin_list_view(request):
    """
    Catalog Products Management View (/catalog/products/).
    Searchable, filterable table with full CRUD actions.
    """
    if not _check_catalog_access(request):
        messages.error(request, "Access restricted to Catalog Staff and Super Administrators.")
        return redirect('management:portal')

    context = _get_catalog_staff_context(request, active_tab='products')

    queryset = Product.objects.select_related('category', 'brand').prefetch_related('images', 'variants').order_by('-updated_at')

    # Filter parameters
    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    category_id = request.GET.get('category_id', '').strip()
    brand_id = request.GET.get('brand_id', '').strip()

    if q:
        queryset = queryset.filter(
            Q(title__icontains=q) |
            Q(sku__icontains=q) |
            Q(description__icontains=q) |
            Q(variants__sku__icontains=q)
        ).distinct()

    if status_filter in ('ACTIVE', 'DRAFT', 'ARCHIVED'):
        queryset = queryset.filter(status=status_filter)

    if category_id:
        queryset = queryset.filter(category_id=category_id)

    if brand_id:
        queryset = queryset.filter(brand_id=brand_id)

    paginator = Paginator(queryset, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context.update({
        'page_obj': page_obj,
        'products': page_obj.object_list,
        'total_count': paginator.count,
        'categories': Category.objects.all().order_by('name'),
        'brands': Brand.objects.all().order_by('name'),
        'q': q,
        'status_filter': status_filter,
        'category_id': category_id,
        'brand_id': brand_id,
    })
    return render(request, 'catalog/manage/product_list.html', context)


def product_add_view(request):
    """
    Add Product View (/catalog/products/add/).
    Supports Basic info, Category, Brand, Tags, Pricing, Images, and Variant generation.
    """
    if not _check_catalog_access(request):
        messages.error(request, "Access restricted to Catalog Staff and Super Administrators.")
        return redirect('management:portal')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        slug = request.POST.get('slug', '').strip() or slugify(title)
        short_description = request.POST.get('short_description', '').strip()
        description = request.POST.get('description', '').strip()
        category_id = request.POST.get('category')
        brand_id = request.POST.get('brand') or None
        sku = request.POST.get('sku', '').strip().upper() or None
        base_price = request.POST.get('base_price', '0').strip()
        compare_at_price = request.POST.get('compare_at_price', '').strip() or None
        cost_price = request.POST.get('cost_price', '').strip() or None
        status = request.POST.get('status', 'ACTIVE')
        visibility = request.POST.get('visibility', 'PUBLIC')
        badge_text = request.POST.get('badge_text', '').strip()
        is_featured = bool(request.POST.get('is_featured'))
        is_trending = bool(request.POST.get('is_trending'))

        if not title:
            messages.error(request, "Product title is required.")
            return redirect('catalog:product_add')

        category = get_object_or_404(Category, id=category_id)
        brand = Brand.objects.filter(id=brand_id).first() if brand_id else None

        product = Product.objects.create(
            title=title,
            slug=slug,
            short_description=short_description,
            description=description,
            category=category,
            brand=brand,
            sku=sku,
            base_price=Decimal(base_price),
            compare_at_price=Decimal(compare_at_price) if compare_at_price else None,
            cost_price=Decimal(cost_price) if cost_price else None,
            status=status,
            visibility=visibility,
            badge_text=badge_text,
            is_featured=is_featured,
            is_trending=is_trending
        )

        # Handle multiple images
        images = request.FILES.getlist('images')
        for idx, img in enumerate(images):
            ProductImage.objects.create(
                product=product,
                image=img,
                alt_text=f"{product.title} image {idx + 1}",
                is_primary=bool(idx == 0),
                display_order=idx
            )

        # Fallback image URL if provided
        image_url = request.POST.get('image_url', '').strip()
        if image_url and not images:
            ProductImage.objects.create(
                product=product,
                image_url=image_url,
                alt_text=product.title,
                is_primary=True,
                display_order=0
            )

        # Handle tags
        raw_tags = request.POST.get('tags', '').strip()
        if raw_tags:
            tag_names = [t.strip() for t in raw_tags.split(',') if t.strip()]
            for t_name in tag_names:
                t_obj, _ = ProductTag.objects.get_or_create(name=t_name, defaults={'slug': slugify(t_name)})
                product.tags.add(t_obj)

        messages.success(request, f"Product '{product.title}' created successfully.")
        return redirect('catalog:product_admin_list')

    context = _get_catalog_staff_context(request, active_tab='products')
    context.update({
        'categories': Category.objects.all().order_by('name'),
        'brands': Brand.objects.all().order_by('name'),
        'attributes': Attribute.objects.prefetch_related('values').all(),
        'action_url': '/catalog/products/add/',
        'is_edit': False,
    })
    return render(request, 'catalog/manage/product_form.html', context)


def product_edit_view(request, pk):
    """
    Edit existing Product (/catalog/products/<pk>/edit/).
    Enables modification of basic information, category, brand, pricing, images,
    and managing variants / attributes.
    """
    if not _check_catalog_access(request):
        messages.error(request, "Access restricted to Catalog Staff and Super Administrators.")
        return redirect('management:portal')

    product = get_object_or_404(
        Product.objects.prefetch_related('images', 'variants__attribute_values__attribute', 'variants__attribute_values__attribute_value', 'tags'),
        id=pk
    )

    if request.method == 'POST':
        action_type = request.POST.get('action_type', 'update_product')

        # 1. Add New Variant
        if action_type == 'add_variant':
            sku = request.POST.get('variant_sku', '').strip().upper()
            var_name = request.POST.get('variant_name', '').strip()
            price = request.POST.get('variant_price', '').strip()
            comp_price = request.POST.get('variant_compare_price', '').strip()

            if not sku:
                messages.error(request, "Variant SKU is mandatory.")
                return redirect('catalog:product_edit', pk=product.id)

            if ProductVariant.objects.filter(sku=sku).exclude(product=product).exists():
                messages.error(request, f"SKU '{sku}' already exists in another product. SKUs must be globally unique.")
                return redirect('catalog:product_edit', pk=product.id)

            variant, created = ProductVariant.objects.get_or_create(
                product=product,
                sku=sku,
                defaults={
                    'name': var_name,
                    'price': Decimal(price) if price else None,
                    'compare_at_price': Decimal(comp_price) if comp_price else None,
                }
            )
            if not created:
                variant.name = var_name
                variant.price = Decimal(price) if price else None
                variant.compare_at_price = Decimal(comp_price) if comp_price else None
                variant.save()

            # Connect attribute values (e.g. attr_1=2)
            for key, val in request.POST.items():
                if key.startswith('attr_') and val:
                    attr_id = key.replace('attr_', '')
                    attr_val = AttributeValue.objects.filter(id=val, attribute_id=attr_id).first()
                    if attr_val:
                        VariantAttributeValue.objects.update_or_create(
                            variant=variant,
                            attribute=attr_val.attribute,
                            defaults={'attribute_value': attr_val}
                        )

            product.product_type = 'variable'
            product.save(update_fields=['product_type'])
            messages.success(request, f"Variant SKU '{sku}' saved successfully.")
            return redirect('catalog:product_edit', pk=product.id)

        # 2. Upload Additional Image
        elif action_type == 'upload_image':
            new_imgs = request.FILES.getlist('images')
            for img in new_imgs:
                ProductImage.objects.create(
                    product=product,
                    image=img,
                    alt_text=product.title,
                    display_order=product.images.count()
                )
            img_url = request.POST.get('image_url', '').strip()
            if img_url:
                ProductImage.objects.create(
                    product=product,
                    image_url=img_url,
                    alt_text=product.title,
                    display_order=product.images.count()
                )
            messages.success(request, "Image(s) added successfully.")
            return redirect('catalog:product_edit', pk=product.id)

        # 3. Main Product Update
        else:
            product.title = request.POST.get('title', '').strip() or product.title
            product.slug = request.POST.get('slug', '').strip() or product.slug
            product.short_description = request.POST.get('short_description', '').strip()
            product.description = request.POST.get('description', '').strip()

            category_id = request.POST.get('category')
            if category_id:
                product.category = get_object_or_404(Category, id=category_id)

            brand_id = request.POST.get('brand')
            product.brand = Brand.objects.filter(id=brand_id).first() if brand_id else None

            new_sku = request.POST.get('sku', '').strip().upper()
            if new_sku and new_sku != product.sku:
                if Product.objects.filter(sku=new_sku).exclude(id=product.id).exists():
                    messages.error(request, f"SKU '{new_sku}' is already assigned to another product.")
                    return redirect('catalog:product_edit', pk=product.id)
                product.sku = new_sku

            base_price = request.POST.get('base_price', '').strip()
            if base_price:
                product.base_price = Decimal(base_price)

            comp_price = request.POST.get('compare_at_price', '').strip()
            product.compare_at_price = Decimal(comp_price) if comp_price else None

            cost_price = request.POST.get('cost_price', '').strip()
            product.cost_price = Decimal(cost_price) if cost_price else None

            product.status = request.POST.get('status', product.status)
            product.visibility = request.POST.get('visibility', product.visibility)
            product.badge_text = request.POST.get('badge_text', '').strip()
            product.is_featured = bool(request.POST.get('is_featured'))
            product.is_trending = bool(request.POST.get('is_trending'))

            # Upload additional images if any
            uploaded_imgs = request.FILES.getlist('images')
            for img in uploaded_imgs:
                ProductImage.objects.create(
                    product=product,
                    image=img,
                    alt_text=product.title,
                    display_order=product.images.count()
                )

            # Update tags
            raw_tags = request.POST.get('tags', '').strip()
            if raw_tags is not None:
                product.tags.clear()
                tag_names = [t.strip() for t in raw_tags.split(',') if t.strip()]
                for t_name in tag_names:
                    t_obj, _ = ProductTag.objects.get_or_create(name=t_name, defaults={'slug': slugify(t_name)})
                    product.tags.add(t_obj)

            product.save()
            messages.success(request, f"Product '{product.title}' updated successfully.")
            return redirect('catalog:product_admin_list')

    context = _get_catalog_staff_context(request, active_tab='products')
    context.update({
        'product': product,
        'categories': Category.objects.all().order_by('name'),
        'brands': Brand.objects.all().order_by('name'),
        'attributes': Attribute.objects.prefetch_related('values').all(),
        'tags_csv': ", ".join([t.name for t in product.tags.all()]),
        'variants': product.variants.prefetch_related('attribute_values__attribute', 'attribute_values__attribute_value').all(),
        'images': product.images.all(),
        'action_url': f'/catalog/products/{product.id}/edit/',
        'is_edit': True,
    })
    return render(request, 'catalog/manage/product_form.html', context)


def product_archive_view(request, pk):
    """Safe archiving: never deletes products permanently that may have order ties."""
    if not _check_catalog_access(request):
        messages.error(request, "Access restricted.")
        return redirect('management:portal')

    product = get_object_or_404(Product, id=pk)
    product.status = 'ARCHIVED'
    product.is_active = False
    product.save(update_fields=['status', 'is_active'])
    messages.success(request, f"Product '{product.title}' archived.")
    return redirect('catalog:product_admin_list')


def product_toggle_status_view(request, pk):
    """Quick toggle between ACTIVE and DRAFT."""
    if not _check_catalog_access(request):
        messages.error(request, "Access restricted.")
        return redirect('management:portal')

    product = get_object_or_404(Product, id=pk)
    if product.status == 'ACTIVE':
        product.status = 'DRAFT'
        product.is_active = False
    else:
        product.status = 'ACTIVE'
        product.is_active = True
    product.save(update_fields=['status', 'is_active'])
    messages.success(request, f"Product '{product.title}' status updated to {product.status}.")
    return redirect('catalog:product_admin_list')


# ==============================================================================
# 3. CATEGORY, BRAND & ATTRIBUTE MANAGEMENT VIEWS
# ==============================================================================

def category_list_view(request):
    """Hierarchical category view with product counts and order controls."""
    if not _check_catalog_access(request):
        messages.error(request, "Access restricted.")
        return redirect('management:portal')

    context = _get_catalog_staff_context(request, active_tab='categories')
    categories = Category.objects.select_related('parent').annotate(p_count=Count('products')).order_by('display_order', 'name')
    context.update({'categories': categories})
    return render(request, 'catalog/manage/category_list.html', context)


def category_add_view(request):
    if not _check_catalog_access(request):
        messages.error(request, "Access restricted.")
        return redirect('management:portal')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        slug = request.POST.get('slug', '').strip() or slugify(name)
        desc = request.POST.get('description', '').strip()
        icon_name = request.POST.get('icon_name', '').strip()
        parent_id = request.POST.get('parent') or None
        img_url = request.POST.get('image_url', '').strip()
        display_order = int(request.POST.get('display_order', 0) or 0)

        if not name:
            messages.error(request, "Category name is required.")
            return redirect('catalog:category_add')

        parent = Category.objects.filter(id=parent_id).first() if parent_id else None
        Category.objects.create(
            name=name,
            slug=slug,
            description=desc,
            icon_name=icon_name,
            parent=parent,
            image=request.FILES.get('image'),
            image_url=img_url,
            display_order=display_order
        )
        messages.success(request, f"Category '{name}' created successfully.")
        return redirect('catalog:category_list')

    context = _get_catalog_staff_context(request, active_tab='categories')
    context.update({
        'categories': Category.objects.all().order_by('name'),
        'is_edit': False,
    })
    return render(request, 'catalog/manage/category_form.html', context)


def category_edit_view(request, pk):
    if not _check_catalog_access(request):
        messages.error(request, "Access restricted.")
        return redirect('management:portal')

    cat = get_object_or_404(Category, id=pk)

    if request.method == 'POST':
        cat.name = request.POST.get('name', '').strip() or cat.name
        cat.slug = request.POST.get('slug', '').strip() or cat.slug
        cat.description = request.POST.get('description', '').strip()
        cat.icon_name = request.POST.get('icon_name', '').strip()
        parent_id = request.POST.get('parent') or None
        if parent_id and int(parent_id) == cat.id:
            messages.error(request, "A category cannot be its own parent.")
            return redirect('catalog:category_edit', pk=cat.id)

        cat.parent = Category.objects.filter(id=parent_id).first() if parent_id else None
        if 'image' in request.FILES:
            cat.image = request.FILES['image']
        cat.image_url = request.POST.get('image_url', '').strip()
        cat.display_order = int(request.POST.get('display_order', 0) or 0)
        cat.is_active = bool(request.POST.get('is_active'))
        try:
            cat.save()
            messages.success(request, f"Category '{cat.name}' updated successfully.")
            return redirect('catalog:category_list')
        except Exception as e:
            messages.error(request, f"Validation error: {e}")

    context = _get_catalog_staff_context(request, active_tab='categories')
    context.update({
        'category': cat,
        'categories': Category.objects.exclude(id=cat.id).order_by('name'),
        'is_edit': True,
    })
    return render(request, 'catalog/manage/category_form.html', context)


def category_toggle_status_view(request, pk):
    if not _check_catalog_access(request):
        messages.error(request, "Access restricted.")
        return redirect('management:portal')

    cat = get_object_or_404(Category, id=pk)
    cat.is_active = not cat.is_active
    cat.save(update_fields=['is_active'])
    messages.success(request, f"Category '{cat.name}' status toggled to {'Active' if cat.is_active else 'Inactive'}.")
    return redirect('catalog:category_list')


def brand_list_view(request):
    if not _check_catalog_access(request):
        messages.error(request, "Access restricted.")
        return redirect('management:portal')

    context = _get_catalog_staff_context(request, active_tab='brands')
    brands = Brand.objects.annotate(p_count=Count('products')).order_by('name')
    context.update({'brands': brands})
    return render(request, 'catalog/manage/brand_list.html', context)


def brand_add_view(request):
    if not _check_catalog_access(request):
        messages.error(request, "Access restricted.")
        return redirect('management:portal')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        slug = request.POST.get('slug', '').strip() or slugify(name)
        desc = request.POST.get('description', '').strip()
        logo_url = request.POST.get('logo_url', '').strip()

        if not name:
            messages.error(request, "Brand name is required.")
            return redirect('catalog:brand_add')

        Brand.objects.create(
            name=name,
            slug=slug,
            description=desc,
            logo=request.FILES.get('logo'),
            logo_url=logo_url
        )
        messages.success(request, f"Brand '{name}' created successfully.")
        return redirect('catalog:brand_list')

    context = _get_catalog_staff_context(request, active_tab='brands')
    context.update({'is_edit': False})
    return render(request, 'catalog/manage/brand_form.html', context)


def brand_edit_view(request, pk):
    if not _check_catalog_access(request):
        messages.error(request, "Access restricted.")
        return redirect('management:portal')

    brand = get_object_or_404(Brand, id=pk)
    if request.method == 'POST':
        brand.name = request.POST.get('name', '').strip() or brand.name
        brand.slug = request.POST.get('slug', '').strip() or brand.slug
        brand.description = request.POST.get('description', '').strip()
        brand.logo_url = request.POST.get('logo_url', '').strip()
        if 'logo' in request.FILES:
            brand.logo = request.FILES['logo']
        brand.is_active = bool(request.POST.get('is_active'))
        brand.save()
        messages.success(request, f"Brand '{brand.name}' updated successfully.")
        return redirect('catalog:brand_list')

    context = _get_catalog_staff_context(request, active_tab='brands')
    context.update({'brand': brand, 'is_edit': True})
    return render(request, 'catalog/manage/brand_form.html', context)


def brand_toggle_status_view(request, pk):
    if not _check_catalog_access(request):
        messages.error(request, "Access restricted.")
        return redirect('management:portal')

    brand = get_object_or_404(Brand, id=pk)
    brand.is_active = not brand.is_active
    brand.save(update_fields=['is_active'])
    messages.success(request, f"Brand '{brand.name}' status toggled.")
    return redirect('catalog:brand_list')


def attribute_list_view(request):
    """Lists configurable attributes and their values."""
    if not _check_catalog_access(request):
        messages.error(request, "Access restricted.")
        return redirect('management:portal')

    context = _get_catalog_staff_context(request, active_tab='attributes')
    attributes = Attribute.objects.prefetch_related('values').all().order_by('display_order', 'name')
    context.update({'attributes': attributes})
    return render(request, 'catalog/manage/attribute_list.html', context)


def attribute_add_view(request):
    if not _check_catalog_access(request):
        messages.error(request, "Access restricted.")
        return redirect('management:portal')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip() or slugify(name)
        values_raw = request.POST.get('values', '').strip()

        if not name:
            messages.error(request, "Attribute name is required.")
            return redirect('catalog:attribute_add')

        attr, created = Attribute.objects.get_or_create(name=name, defaults={'code': code})
        if values_raw:
            vals = [v.strip() for v in values_raw.split(',') if v.strip()]
            for idx, val in enumerate(vals):
                AttributeValue.objects.get_or_create(attribute=attr, value=val, defaults={'display_order': idx})

        messages.success(request, f"Attribute '{name}' created with {attr.values.count()} values.")
        return redirect('catalog:attribute_list')

    context = _get_catalog_staff_context(request, active_tab='attributes')
    context.update({'is_edit': False})
    return render(request, 'catalog/manage/attribute_form.html', context)


def attribute_edit_view(request, pk):
    if not _check_catalog_access(request):
        messages.error(request, "Access restricted.")
        return redirect('management:portal')

    attr = get_object_or_404(Attribute.objects.prefetch_related('values'), id=pk)
    if request.method == 'POST':
        # Delete specific attribute value if requested
        delete_val_id = request.POST.get('delete_val_id')
        if delete_val_id:
            val_to_del = attr.values.filter(id=delete_val_id).first()
            if val_to_del:
                val_text = val_to_del.value
                val_to_del.delete()
                messages.success(request, f"Value '{val_text}' removed from '{attr.name}'.")
            return redirect('catalog:attribute_edit', pk=attr.id)

        attr.name = request.POST.get('name', '').strip() or attr.name
        attr.code = request.POST.get('code', '').strip() or attr.code
        attr.save()

        # Add any new values submitted (supports comma-separated or single)
        new_val = request.POST.get('new_value', '').strip()
        if new_val:
            raw_vals = [v.strip() for v in new_val.split(',') if v.strip()]
            added_count = 0
            for v in raw_vals:
                _, created = AttributeValue.objects.get_or_create(attribute=attr, value=v, defaults={'display_order': attr.values.count()})
                if created:
                    added_count += 1
            if added_count > 0:
                messages.success(request, f"Added {added_count} value(s) to '{attr.name}'.")

        messages.success(request, f"Attribute '{attr.name}' updated.")
        return redirect('catalog:attribute_edit', pk=attr.id)

    context = _get_catalog_staff_context(request, active_tab='attributes')
    context.update({'attribute': attr, 'is_edit': True})
    return render(request, 'catalog/manage/attribute_form.html', context)


def attribute_delete_view(request, pk):
    if not _check_catalog_access(request):
        messages.error(request, "Access restricted.")
        return redirect('management:portal')

    attr = get_object_or_404(Attribute, id=pk)
    name = attr.name
    attr.delete()
    messages.success(request, f"Attribute '{name}' deleted.")
    return redirect('catalog:attribute_list')
