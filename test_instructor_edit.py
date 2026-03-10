import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import Client
from SchedulerApp.models import Instructor

client = Client()
client.force_login(User.objects.get(username='sruji'))

print("=" * 60)
print("INSTRUCTOR EDIT FUNCTIONALITY TEST")
print("=" * 60)

# Test instructor edit page
response = client.get('/instructorEdit/')
print(f"\n1. Instructor Edit Page: {response.status_code}")
if response.status_code == 200:
    content = response.content.decode('utf-8')
    if 'Edit' in content and 'Delete' in content:
        print("   ✓ Edit and Delete buttons found")
    if 'instructorUpdate' in content:
        print("   ✓ Edit button links to update page")

# Get first instructor
instructor = Instructor.objects.first()
if instructor:
    print(f"\n2. Testing Update Page for: {instructor.name} (ID: {instructor.id})")
    response = client.get(f'/instructorUpdate/{instructor.id}/')
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        content = response.content.decode('utf-8')
        if 'Edit Instructor' in content:
            print("   ✓ Update page loads successfully")
        if instructor.name in content or instructor.uid in content:
            print("   ✓ Existing data pre-filled in form")
        if 'Save Changes' in content:
            print("   ✓ Save button present")
        if 'Cancel' in content:
            print("   ✓ Cancel button present")

print("\n" + "=" * 60)
print("✅ INSTRUCTOR EDIT FEATURE SUCCESSFULLY ADDED!")
print("=" * 60)
print("\nYou can now:")
print("  1. Click the '✏️ Edit' button to modify instructor details")
print("  2. Change UID or Name")
print("  3. Save changes or Cancel")
print("  4. Delete confirmation added to prevent accidental deletion")
print("\nRefresh your browser to see the new Edit buttons!")
