import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import Client
from SchedulerApp.models import Year

# Create test client
client = Client()

# Login
user = User.objects.get(username='sruji')
client.force_login(user)

# Get first year
year = Year.objects.first()
print(f"Testing with Year: {year.year_name} (ID: {year.id})")

# Test year-wise view using GET (not POST)
print("\n" + "=" * 60)
print("TESTING YEAR-WISE VIEW (All 3 Sections)")
print("=" * 60)
response = client.get(f'/timetable/view/?view_type=year&year={year.id}')
print(f"Status: {response.status_code}")

content = response.content.decode('utf-8')

# Check for multiple section headers
import re
section_matches = re.findall(r'Section (\d+) Timetable', content)
print(f"Found {len(section_matches)} section timetable headers: {section_matches}")

# Check for class counts
count_matches = re.findall(r'(\d+) Classes', content)
print(f"Class counts found: {count_matches}")

# Check if sections_data is present in HTML
if 'sections_data' in content:
    print("✓ sections_data variable found in template")
else:
    print("✗ sections_data variable NOT found")

# Test all faculties view
print("\n" + "=" * 60)
print("TESTING ALL FACULTIES VIEW")
print("=" * 60)
response = client.get('/timetable/view/?view_type=faculty&all_faculties=true')
print(f"Status: {response.status_code}")

content = response.content.decode('utf-8')
faculty_matches = re.findall(r"<h3>(.+?)'s Timetable</h3>", content)
print(f"Found {len(faculty_matches)} faculty timetable headers")
if faculty_matches:
    print(f"First 3 faculties: {faculty_matches[:3]}")

# Test all labs view
print("\n" + "=" * 60)
print("TESTING ALL LABS VIEW")
print("=" * 60)
response = client.get('/timetable/view/?view_type=lab&all_labs=true')
print(f"Status: {response.status_code}")

content = response.content.decode('utf-8')
lab_matches = re.findall(r'<h3>(.+?) Schedule</h3>', content)
print(f"Found {len(lab_matches)} lab timetable headers")
if lab_matches:
    print(f"Labs: {lab_matches}")

print("\n✅ All tests complete!")
