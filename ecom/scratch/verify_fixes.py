import os
import sys
import django

sys.path.insert(0, r'd:\django_project\E-Commerce\E-Commerce\ecom')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecom.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.core.models import ManagementDepartment
from bs4 import BeautifulSoup

def verify():
    print("=== 1. Verifying Image 1 Fix: CMS editBannerModal Structure ===")
    with open(r'd:\django_project\E-Commerce\E-Commerce\ecom\templates\cms\dashboard.html', 'r', encoding='utf-8') as f:
        html = f.read()

    # Parse with BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    modal = soup.find('div', id='editBannerModal')
    assert modal is not None, "editBannerModal not found"

    # Header check
    inner_card = modal.find('div', class_=lambda c: c and 'bg-slate-900' in c and 'rounded-2xl' in c)
    assert inner_card is not None, "Modal inner card not found"

    header = inner_card.find('div', class_=lambda c: c and 'border-b' in c)
    assert header is not None, "Modal header not found"
    assert "Edit Promotional Banner" in header.text, "Header title missing"

    # Crucial: <form> must be a sibling of header, NOT inside header!
    form_inside_header = header.find('form')
    assert form_inside_header is None, "ERROR: Form is still illegally inside header!"

    # Form must be direct child of inner_card
    form = inner_card.find('form', id='editBannerForm')
    assert form is not None, "editBannerForm not found in modal inner card"
    assert form.parent == inner_card, "Form is not a direct child of inner card"

    print("[PASS] Image 1 Fix: editBannerModal header and form are cleanly separated and structurally valid.")

    print("\n=== 2. Verifying Image 2 Fix: Accounts Studio Logout Buttons & Identity ===")
    client = Client()

    # Create / get superadmin user
    admin_user, _ = User.objects.get_or_create(username='admin_test', defaults={'email': 'admin@cartivo.com', 'is_superuser': True, 'is_staff': True})
    admin_user.set_password('AdminPass123!')
    admin_user.is_superuser = True
    admin_user.is_staff = True
    admin_user.save()

    client.force_login(admin_user)
    resp = client.get('/accounts/manage/')
    assert resp.status_code == 200, f"Dashboard returned {resp.status_code}"
    resp_html = resp.content.decode('utf-8')

    soup_dash = BeautifulSoup(resp_html, 'html.parser')

    # Verify user footer in sidebar is NOT empty
    sidebar = soup_dash.find('aside', id='sidebar')
    assert sidebar is not None, "Sidebar not found"

    sidebar_text = sidebar.text
    assert "ADMIN_TEST" in sidebar_text or "admin_test" in sidebar_text, "Superadmin username missing in sidebar footer"
    assert "Super Administrator" in sidebar_text, "Super Administrator label missing in sidebar"

    # Check that avatar box is NOT empty
    avatar_div = sidebar.find('div', class_=lambda c: c and 'rounded-lg' in c and ('bg-amber-500/20' in c or 'bg-emerald-600/30' in c))
    assert avatar_div is not None, "Avatar container missing"
    assert avatar_div.text.strip() != "", "Avatar text is empty! (Empty box bug from Image 2 still present)"
    print(f"[PASS] Avatar initials correctly rendered as: '{avatar_div.text.strip()}'")

    # Check for dedicated Sign Out link in sidebar navigation
    signout_links = sidebar.find_all('a', href=lambda h: h and ('logout' in h))
    assert len(signout_links) >= 2, f"Expected at least 2 logout links in sidebar, found {len(signout_links)}"
    print(f"[PASS] Found {len(signout_links)} logout buttons in sidebar.")

    # Check for top header bar logout button
    header = soup_dash.find('header')
    header_logout = header.find('a', href=lambda h: h and ('logout' in h))
    assert header_logout is not None, "Top header bar logout button is missing"
    assert "Logout" in header_logout.text or "Sign Out" in header_logout.text, "Logout text missing in header button"
    print(f"[PASS] Found top header bar logout button: '{header_logout.text.strip()}'")

    print("\nALL FIXES VERIFIED SUCCESSFULLY! [OK]")

if __name__ == '__main__':
    verify()
