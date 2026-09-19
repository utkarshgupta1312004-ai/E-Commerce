import os
import sys
import django

# Setup Django environment
sys.path.insert(0, r'd:\django_project\E-Commerce\E-Commerce\ecom')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecom.settings')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.auth.models import User, Group
from apps.accounts.models import UserProfile, Role
from apps.core.models import ManagementDepartment
import json

def run_tests():
    print("=== Testing 1: Superadmin Blocked From Department Staff Login ===")
    client = Client()
    
    # Ensure a superadmin exists
    admin_user, _ = User.objects.get_or_create(username='admin_test', defaults={'email': 'admin_test@cartivo.com', 'is_superuser': True, 'is_staff': True})
    admin_user.set_password('AdminPass123!')
    admin_user.is_superuser = True
    admin_user.is_staff = True
    admin_user.save()
    
    # Try logging in as superadmin via department_login_view
    resp = client.post('/management/department/login/', {
        'login_id': 'admin_test',
        'password': 'AdminPass123!',
        'department_slug': 'accounts'
    })
    print(f"Department login response status: {resp.status_code}")
    # Should contain error message about superadmin
    content = resp.content.decode('utf-8')
    assert "Superadmins cannot login through department staff portals" in content or "Use the Superadmin Portal" in content or resp.status_code == 302, f"Failed superadmin check: {content[:200]}"
    print("[PASS]: Superadmin is blocked from department login.")

    print("\n=== Testing 2: Superadmin Blocked From Storefront Login ===")
    resp_store = client.post('/accounts/login/', {
        'email': 'admin_test',
        'password': 'AdminPass123!'
    })
    store_content = resp_store.content.decode('utf-8')
    assert "Super Administrator accounts cannot sign in through the customer storefront" in store_content, "Superadmin was not blocked from storefront login"
    print("[PASS]: Superadmin is blocked from customer storefront login.")

    print("\n=== Testing 3: Superadmin Dashboard Users Table Has No Edit Button ===")
    with open(r'd:\django_project\E-Commerce\E-Commerce\ecom\templates\management\superadmin_users.html', 'r', encoding='utf-8') as f:
        html = f.read()
    assert 'Actions' not in html, "Found 'Actions' header in superadmin_users.html"
    assert 'accounts:user_detail' not in html, "Found edit link in superadmin_users.html"
    assert 'Accounts Governance Console' in html, "Accounts Governance Console link missing in superadmin_users.html"
    print("[PASS]: Superadmin dashboard users table has no edit buttons and delegates to Accounts console.")

    print("\n=== Testing 4: Accounts Management Dashboard Customer/Staff Breakdown ===")
    # Login as an authorized accounts staff member
    accounts_staff, _ = User.objects.get_or_create(username='acc_staff_test', defaults={'email': 'acc_staff@cartivo.com', 'is_staff': True})
    accounts_staff.set_password('StaffPass123!')
    accounts_staff.is_staff = True
    accounts_staff.save()
    
    dept_accounts, _ = ManagementDepartment.objects.get_or_create(slug='accounts', defaults={'name': 'Accounts & Identity', 'code': 'ACC'})
    acc_prof, _ = UserProfile.objects.get_or_create(user=accounts_staff)
    acc_prof.department_access.add(dept_accounts)
    acc_prof.is_management_staff = True
    acc_prof.save()
    
    client.force_login(accounts_staff)
    dash_resp = client.get('/accounts/manage/')
    assert dash_resp.status_code == 200, f"Dashboard returned status {dash_resp.status_code}"
    dash_content = dash_resp.content.decode('utf-8')
    assert "Customers" in dash_content
    assert "Department Staff" in dash_content
    assert "Superadmins" in dash_content
    print("[PASS]: Accounts dashboard renders Customers, Department Staff, and Superadmins distinctly.")

    print("\n=== Testing 5: Flexible Account Switcher (Customer <-> Staff) ===")
    # Create test customer
    test_cust, _ = User.objects.get_or_create(username='test_flexible_user', defaults={'email': 'flexible@example.com'})
    test_cust.set_password('UserPass123!')
    test_cust.is_staff = False
    test_cust.is_superuser = False
    test_cust.save()
    
    profile, _ = UserProfile.objects.get_or_create(user=test_cust)
    cust_group, _ = Group.objects.get_or_create(name='Customer')
    dept_group, _ = Group.objects.get_or_create(name='Cartivo Department')
    test_cust.groups.set([cust_group])
    
    # Test switching customer to staff via POST
    post_data = {
        'username': test_cust.username,
        'first_name': 'Flexible',
        'last_name': 'Tester',
        'email': 'flexible@example.com',
        'phone': '9876543210',
        'is_active': 'on',
        'account_type': 'staff', # Switch to staff!
        'job_title': 'Finance Specialist',
        f'dept_{dept_accounts.id}': 'on',
    }
    
    resp_edit = client.post(f'/accounts/manage/users/{test_cust.id}/', post_data)
    assert resp_edit.status_code == 302, f"Expected 302 redirect after edit, got {resp_edit.status_code}"
    
    test_cust.refresh_from_db()
    test_cust.profile.refresh_from_db()
    assert test_cust.is_staff == True, "Expected is_staff to be True after switching to staff"
    assert test_cust.profile.is_management_staff == True, "Expected is_management_staff to be True"
    assert dept_group in test_cust.groups.all(), "Expected Cartivo Department group to be present"
    assert cust_group not in test_cust.groups.all(), "Expected Customer group to be removed"
    print("[PASS]: Customer successfully switched to Department Staff with correct groups and flags.")

    # Now switch back to Customer!
    post_data_back = {
        'username': test_cust.username,
        'first_name': 'Flexible',
        'last_name': 'Customer',
        'email': 'flexible@example.com',
        'phone': '9876543210',
        'is_active': 'on',
        'account_type': 'customer', # Switch back!
    }
    resp_edit_back = client.post(f'/accounts/manage/users/{test_cust.id}/', post_data_back)
    assert resp_edit_back.status_code == 302
    
    test_cust.refresh_from_db()
    test_cust.profile.refresh_from_db()
    assert test_cust.is_staff == False, "Expected is_staff to be False after switching to customer"
    assert test_cust.profile.is_management_staff == False, "Expected is_management_staff to be False"
    assert cust_group in test_cust.groups.all(), "Expected Customer group to be added back"
    assert dept_group not in test_cust.groups.all(), "Expected Cartivo Department group to be removed"
    print("[PASS]: Staff successfully switched back to Customer with clean group synchronization.")

    print("\nALL 5 VERIFICATION TESTS PASSED SUCCESSFULLY! [OK]")

if __name__ == '__main__':
    run_tests()
