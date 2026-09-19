from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.core.models import ManagementDepartment, DepartmentAccount
from apps.cms.models import (
    PromoBanner,
    CategoryNavItem,
    HomepageSection,
    HomepageCategoryItem,
    TrustBadge,
    NavbarItem,
)

User = get_user_model()


class CMSDashboardViewTest(TestCase):
    def setUp(self):
        self.client = Client()

        # Superuser
        self.superuser = User.objects.create_superuser(
            username="admin",
            email="admin@cartivo.local",
            password="AdminPassword123!"
        )

        # Non-admin user
        self.regular_user = User.objects.create_user(
            username="regular",
            email="regular@cartivo.local",
            password="UserPassword123!"
        )

        # CMS Management Department & Credentials
        self.cms_dept = ManagementDepartment.objects.create(
            name="Content Management System",
            slug="cms",
            code="cms",
            description="Manages storefront content, hero carousel, banners, and layout blocks.",
            icon="layout-template",
            display_order=1
        )
        self.cms_account = DepartmentAccount.objects.create(
            department=self.cms_dept,
            login_id="CMS001",
            status=DepartmentAccount.STATUS_ACTIVE
        )
        self.cms_account.set_password("CmsSecretPass123!")
        self.cms_account.save()

        # Create CMS sample data
        self.banner = PromoBanner.objects.create(
            title="Big Saving Days Promo",
            subtitle="Exclusive Deals on Electronics",
            price_tag="From ₹9,999",
            badge_text="SPECIAL DEAL",
            is_active=True,
            display_order=1
        )
        self.section = HomepageSection.objects.create(
            name="Hero Promotional Banners",
            section_type="hero_banners",
            title="Featured Seasonal Offers",
            display_order=1,
            is_active=True
        )
        self.nav_item = CategoryNavItem.objects.create(
            title="Smartphones",
            icon_name="smartphone",
            is_active=True,
            display_order=1
        )
        self.trust_badge = TrustBadge.objects.create(
            title="Free Nationwide Shipping",
            subtitle="On all orders above ₹499",
            icon_name="truck",
            color_theme="blue",
            is_active=True
        )
        self.navbar_item = NavbarItem.objects.create(
            title="Electronics",
            url="/category/electronics/",
            is_active=True
        )

        self.dashboard_url = reverse('cms:dashboard')
        self.login_url = reverse('management:dept_login')

    def test_unauthorized_user_redirected(self):
        # Anonymous user
        res = self.client.get(self.dashboard_url)
        self.assertEqual(res.status_code, 302)

        # Regular logged in user without CMS session
        self.client.login(username="regular", password="UserPassword123!")
        res = self.client.get(self.dashboard_url)
        self.assertEqual(res.status_code, 302)

    def test_superuser_access_allowed(self):
        self.client.login(username="admin", password="AdminPassword123!")
        res = self.client.get(self.dashboard_url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "CMS Studio")
        self.assertContains(res, "Big Saving Days Promo")
        self.assertContains(res, "Hero Promotional Banners")

    def test_cms_department_staff_access_allowed(self):
        # Set session as CMS staff
        session = self.client.session
        session['department_account_id'] = self.cms_account.id
        session['department_id'] = self.cms_dept.id
        session['department_name'] = self.cms_dept.name
        session['department_login_id'] = self.cms_account.login_id
        session['department_slug'] = 'cms'
        session.save()

        res = self.client.get(self.dashboard_url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "CMS Studio Overview")
        self.assertContains(res, "CMS001")
        self.assertContains(res, "Smartphones")

    def test_department_login_redirects_cms_to_cms_dashboard(self):
        res = self.client.post(self.login_url, {
            'login_id': 'CMS001',
            'password': 'CmsSecretPass123!',
        })
        self.assertRedirects(res, self.dashboard_url)
        self.assertEqual(self.client.session.get('department_slug'), 'cms')
        self.assertEqual(self.client.session.get('department_login_id'), 'CMS001')

    def test_dashboard_context_data(self):
        self.client.login(username="admin", password="AdminPassword123!")
        res = self.client.get(self.dashboard_url)
        self.assertEqual(res.status_code, 200)

        # Verify context data structures
        self.assertIn('kpis', res.context)
        self.assertEqual(res.context['kpis']['total_banners'], 1)
        self.assertEqual(res.context['kpis']['total_sections'], 1)
        self.assertEqual(res.context['kpis']['total_nav_items'], 1)
        self.assertEqual(res.context['kpis']['total_trust_badges'], 1)
        self.assertEqual(res.context['kpis']['total_navbar_items'], 1)
        self.assertIn('banners', res.context)
        self.assertIn('category_nav_items', res.context)
        self.assertIn('homepage_sections', res.context)
        self.assertIn('trust_badges', res.context)
        self.assertIn('navbar_items', res.context)

    def test_dedicated_cms_pages_render_for_admin(self):
        self.client.login(username="admin", password="AdminPassword123!")

        endpoints = [
            ('cms:banners', 'Hero & Promotional Banners'),
            ('cms:sections', 'Homepage Section Blocks'),
            ('cms:category_nav', 'Category Sub-Menu Navigation'),
            ('cms:curations', 'Curated Category Showcases'),
            ('cms:trust_badges', 'Value Propositions & Trust Badges'),
            ('cms:navbar', 'Global Navigation Bar Hierarchy'),
        ]

        for url_name, expected_text in endpoints:
            url = reverse(url_name)
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200, f"Failed to render {url_name}")
            self.assertContains(res, expected_text)

    def test_banner_toggle_view(self):
        self.client.login(username="admin", password="AdminPassword123!")
        self.assertTrue(self.banner.is_active)

        toggle_url = reverse('cms:banner_toggle', args=[self.banner.id])
        res = self.client.get(toggle_url)
        self.assertRedirects(res, reverse('cms:banners'))

        self.banner.refresh_from_db()
        self.assertFalse(self.banner.is_active)

        # Toggle back
        res = self.client.get(toggle_url)
        self.banner.refresh_from_db()
        self.assertTrue(self.banner.is_active)

    def test_banner_bulk_deactivate_and_delete(self):
        self.client.login(username="admin", password="AdminPassword123!")

        bulk_url = reverse('cms:banner_bulk')

        # Bulk deactivate
        res = self.client.post(bulk_url, {
            'action': 'deactivate',
            'selected_ids': [self.banner.id]
        })
        self.assertRedirects(res, reverse('cms:banners'))
        self.banner.refresh_from_db()
        self.assertFalse(self.banner.is_active)

        # Bulk delete
        res = self.client.post(bulk_url, {
            'action': 'delete',
            'selected_ids': [self.banner.id]
        })
        self.assertRedirects(res, reverse('cms:banners'))
        self.assertFalse(PromoBanner.objects.filter(id=self.banner.id).exists())

    def test_banner_add_modal_submission(self):
        self.client.login(username="admin", password="AdminPassword123!")
        add_url = reverse('cms:banner_add')

        res = self.client.post(add_url, {
            'title': 'New Autumn Fest',
            'subtitle': 'Warm styles for cold days',
            'badge_text': 'LIMITED',
            'button_text': 'Shop Autumn',
            'button_url': '/products/?tag=autumn',
            'is_active': 'on',
            'display_order': '5',
        })
        self.assertRedirects(res, reverse('cms:banners'))
        created = PromoBanner.objects.filter(title='New Autumn Fest').first()
        self.assertIsNotNone(created)
        self.assertTrue(created.is_active)
        self.assertEqual(created.display_order, 5)

    def test_dedicated_cms_pages_accessible_and_linked_in_sidebar(self):
        self.client.login(username="admin", password="AdminPassword123!")

        endpoints = [
            ('cms:banners', 'Hero & Promotional Banners'),
            ('cms:sections', 'Homepage Section Blocks'),
            ('cms:category_nav', 'Category Sub-Menu Navigation'),
            ('cms:curations', 'Curated Category Showcases'),
            ('cms:trust_badges', 'Value Propositions & Trust Badges'),
            ('cms:navbar', 'Global Navigation Bar Hierarchy'),
        ]

        # 1. Verify all 6 dedicated pages render with 200 OK
        for url_name, title_fragment in endpoints:
            res = self.client.get(reverse(url_name))
            self.assertEqual(res.status_code, 200, f"Page {url_name} failed to load.")
            self.assertContains(res, title_fragment)

        # 2. Verify sidebar on CMS Dashboard contains real href links to dedicated pages, not hash anchors
        dash_res = self.client.get(reverse('cms:dashboard'))
        self.assertEqual(dash_res.status_code, 200)
        self.assertContains(dash_res, f'href="{reverse("cms:banners")}"')
        self.assertContains(dash_res, f'href="{reverse("cms:sections")}"')
        self.assertContains(dash_res, f'href="{reverse("cms:category_nav")}"')
        self.assertContains(dash_res, f'href="{reverse("cms:curations")}"')
        self.assertContains(dash_res, f'href="{reverse("cms:trust_badges")}"')
        self.assertContains(dash_res, f'href="{reverse("cms:navbar")}"')

        # Ensure no hash anchors are used for sidebar menu links
        self.assertNotContains(dash_res, 'href="/cms/dashboard/#banners"')
        self.assertNotContains(dash_res, 'href="/cms/dashboard/#sections"')
        self.assertNotContains(dash_res, 'href="/cms/dashboard/#categories"')
        self.assertNotContains(dash_res, 'href="/cms/dashboard/#curations"')
        self.assertNotContains(dash_res, 'href="/cms/dashboard/#trust"')
        self.assertNotContains(dash_res, 'href="/cms/dashboard/#navbar"')

    def test_dept_staff_can_edit_all_cms_entities_in_app(self):
        # Set session as CMS staff (non-superuser)
        session = self.client.session
        session['department_account_id'] = self.cms_account.id
        session['department_id'] = self.cms_dept.id
        session['department_name'] = self.cms_dept.name
        session['department_login_id'] = self.cms_account.login_id
        session['department_slug'] = 'cms'
        session.save()

        # 1. Edit Banner
        res = self.client.post(reverse('cms:banner_edit', args=[self.banner.id]), {
            'title': 'Updated Promo Title',
            'subtitle': 'Updated Subtitle',
            'badge_text': 'HOT DEAL',
            'price_tag': 'From ₹7,999',
            'button_text': 'Shop Now',
            'button_url': '/products/',
            'display_order': 2,
            'is_active': 'on',
        })
        self.assertEqual(res.status_code, 302)
        self.banner.refresh_from_db()
        self.assertEqual(self.banner.title, 'Updated Promo Title')
        self.assertEqual(self.banner.price_tag, 'From ₹7,999')

        # 2. Edit Section
        res = self.client.post(reverse('cms:section_edit', args=[self.section.id]), {
            'name': 'Updated Hero Section',
            'section_type': 'hero_banners',
            'title': 'Updated Section Title',
            'subtitle': 'New Subtitle',
            'display_order': 3,
            'is_active': 'on',
        })
        self.assertEqual(res.status_code, 302)
        self.section.refresh_from_db()
        self.assertEqual(self.section.name, 'Updated Hero Section')
        self.assertEqual(self.section.title, 'Updated Section Title')

        # 3. Edit Category Nav Item
        res = self.client.post(reverse('cms:category_nav_edit', args=[self.nav_item.id]), {
            'title': 'Tablets & iPads',
            'custom_url': '/products/?cat=tablets',
            'icon_name': 'tablet',
            'display_order': 4,
            'is_highlighted': 'on',
            'is_active': 'on',
        })
        self.assertEqual(res.status_code, 302)
        self.nav_item.refresh_from_db()
        self.assertEqual(self.nav_item.title, 'Tablets & iPads')
        self.assertTrue(self.nav_item.is_highlighted)

        # 4. Edit Trust Badge
        res = self.client.post(reverse('cms:trust_badge_edit', args=[self.trust_badge.id]), {
            'title': 'Free Global Shipping',
            'subtitle': 'On orders over $50',
            'icon_name': 'truck',
            'color_theme': 'emerald',
            'display_order': 1,
            'is_active': 'on',
        })
        self.assertEqual(res.status_code, 302)
        self.trust_badge.refresh_from_db()
        self.assertEqual(self.trust_badge.title, 'Free Global Shipping')
        self.assertEqual(self.trust_badge.color_theme, 'emerald')

        # 5. Edit Navbar Item
        res = self.client.post(reverse('cms:navbar_edit', args=[self.navbar_item.id]), {
            'title': 'Computers & Laptops',
            'url': '/category/computers/',
            'display_order': 5,
            'is_active': 'on',
        })
        self.assertEqual(res.status_code, 302)
        self.navbar_item.refresh_from_db()
        self.assertEqual(self.navbar_item.title, 'Computers & Laptops')
        self.assertEqual(self.navbar_item.url, '/category/computers/')

        # 6. Verify Dashboard HTML has ZERO links to /admin/ for department staff
        dash_res = self.client.get(reverse('cms:dashboard'))
        self.assertEqual(dash_res.status_code, 200)
        self.assertNotContains(dash_res, '/admin/')

    def test_dual_image_file_upload_and_external_url_support(self):
        """Verify that models and views accept file upload to local media storage and Google/external URLs."""
        # Authenticate via superuser
        self.client.login(username="admin", password="AdminPassword123!")

        # 1. Add PromoBanner with external URL (e.g., Google or Unsplash link)
        google_banner_url = "https://lh3.googleusercontent.com/test-banner-promo.jpg"
        res = self.client.post(reverse('cms:banner_add'), {
            'title': 'Google URL Banner',
            'subtitle': 'Tested with external URL',
            'image_url': google_banner_url,
            'is_active': 'on',
        })
        self.assertEqual(res.status_code, 302)
        banner_created = PromoBanner.objects.get(title='Google URL Banner')
        self.assertEqual(banner_created.image_url, google_banner_url)
        self.assertEqual(banner_created.effective_image_url, google_banner_url)

        # 2. Edit PromoBanner with uploaded file (saves to local media)
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x05\x04\x04'
            b'\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44'
            b'\x01\x00\x3b'
        )
        uploaded_file = SimpleUploadedFile('promo_test.gif', small_gif, content_type='image/gif')
        res = self.client.post(reverse('cms:banner_edit', args=[banner_created.id]), {
            'title': 'Local File Banner',
            'image': uploaded_file,
            'image_url': google_banner_url,
            'is_active': 'on',
        })
        self.assertEqual(res.status_code, 302)
        banner_created.refresh_from_db()
        self.assertTrue(bool(banner_created.image))
        self.assertTrue(banner_created.effective_image_url.startswith('/media/'))

        # 3. Add HomepageSection with uploaded file
        uploaded_section_img = SimpleUploadedFile('section_header.gif', small_gif, content_type='image/gif')
        res = self.client.post(reverse('cms:section_add'), {
            'name': 'New Upload Section',
            'section_type': 'product_grid',
            'title': 'Trending Picks',
            'image': uploaded_section_img,
            'is_active': 'on',
        })
        self.assertEqual(res.status_code, 302)
        sec = HomepageSection.objects.get(name='New Upload Section')
        self.assertTrue(bool(sec.image))
        self.assertTrue(sec.effective_image_url.startswith('/media/'))

        # 4. Edit HomepageSection with external URL & clear uploaded file
        res = self.client.post(reverse('cms:section_edit', args=[sec.id]), {
            'name': 'New Upload Section',
            'section_type': 'product_grid',
            'title': 'Trending Picks',
            'clear_image': 'true',
            'image_url': 'https://images.unsplash.com/photo-section.jpg',
            'is_active': 'on',
        })
        self.assertEqual(res.status_code, 302)
        sec.refresh_from_db()
        self.assertFalse(bool(sec.image))
        self.assertEqual(sec.effective_image_url, 'https://images.unsplash.com/photo-section.jpg')

        # 5. Add CategoryNavItem with external image URL
        res = self.client.post(reverse('cms:category_nav_add'), {
            'title': 'Fashion Hub',
            'icon_name': 'tag',
            'image_url': 'https://images.google.com/fashion-icon.png',
            'is_active': 'on',
        })
        self.assertEqual(res.status_code, 302)
        nav_item = CategoryNavItem.objects.get(title='Fashion Hub')
        self.assertEqual(nav_item.effective_image_url, 'https://images.google.com/fashion-icon.png')




