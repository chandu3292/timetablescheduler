"""
Diagnostic script for View Timetable feature
Run this to check if everything is configured correctly
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from django.urls import reverse
from SchedulerApp.models import Year, Instructor, LabRoom, TimetableEntry

print("=" * 70)
print("VIEW TIMETABLE DIAGNOSTIC TEST")
print("=" * 70)

# Test 1: Check URL exists
print("\n1. Checking URL configuration...")
try:
    url = reverse('view_timetable')
    print(f"   ✓ URL exists: {url}")
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    exit(1)

# Test 2: Check data exists
print("\n2. Checking database data...")
years_count = Year.objects.count()
instructors_count = Instructor.objects.count()
labs_count = LabRoom.objects.count()
entries_count = TimetableEntry.objects.count()

print(f"   ✓ Years: {years_count}")
print(f"   ✓ Instructors: {instructors_count}")
print(f"   ✓ Labs: {labs_count}")
print(f"   ✓ Timetable Entries: {entries_count}")

if entries_count == 0:
    print("   ⚠ WARNING: No timetable entries found!")
    print("   → Generate a timetable first before viewing")

# Test 3: Check users
print("\n3. Checking user accounts...")
users = User.objects.all()
if users.count() == 0:
    print("   ✗ ERROR: No users found!")
    print("   → Create a user with: python manage.py createsuperuser")
    exit(1)
else:
    print(f"   ✓ Found {users.count()} user(s):")
    for user in users:
        print(f"      - {user.username}")

# Test 4: Test view function
print("\n4. Testing view function...")
client = Client()
user = User.objects.first()
client.force_login(user)

response = client.get('/timetable/view/')
print(f"   Status Code: {response.status_code}")

if response.status_code == 200:
    content = response.content.decode('utf-8')
    
    # Check for key elements
    checks = [
        'View Timetable',
        'Section-wise',
        'Year-wise',
        'Faculty-wise',
        'Lab-wise',
        'Period-wise',
    ]
    
    all_found = True
    for check in checks:
        if check in content:
            print(f"   ✓ Found: {check}")
        else:
            print(f"   ✗ Missing: {check}")
            all_found = False
    
    if all_found:
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)
        print("\nThe View Timetable feature is working correctly.")
        print("\nTo access it:")
        print("1. Start server: python manage.py runserver")
        print("2. Open browser: http://localhost:8000/")
        print("3. Login with your credentials")
        print("4. Click 'View Timetable' in the menu or homepage")
    else:
        print("\n" + "=" * 70)
        print("⚠ SOME TESTS FAILED")
        print("=" * 70)
        print("\nSome template elements are missing.")
        print("The template might be corrupted or incomplete.")
else:
    print(f"\n   ✗ ERROR: Unexpected status code {response.status_code}")

print("\n" + "=" * 70)
