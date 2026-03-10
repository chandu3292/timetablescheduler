import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import Client

# Create test client
client = Client()

# Login
user = User.objects.get(username='sruji')
client.force_login(user)

# Test year-wise view (should show 3 separate sections)
print("=" * 60)
print("TESTING YEAR-WISE VIEW (All Sections)")
print("=" * 60)
response = client.post('/timetable/view/', {
    'view_type': 'year',
    'year': '1'  # CSE Year 1
})
print(f"Status: {response.status_code}")
content = response.content.decode('utf-8')

# Check for multiple section headers
import re
section_matches = re.findall(r'Section (\d+) Timetable', content)
print(f"Found {len(section_matches)} section timetables: {section_matches}")

# Check for results count
count_matches = re.findall(r'<span class="results-count">(\d+) Classes</span>', content)
print(f"Classes per section: {count_matches}")

print("\n" + "=" * 60)
print("TESTING FACULTY-WISE VIEW (All Faculties)")
print("=" * 60)
response = client.post('/timetable/view/', {
    'view_type': 'faculty',
    'all_faculties': 'true'
})
print(f"Status: {response.status_code}")
content = response.content.decode('utf-8')

# Check for multiple faculty headers
faculty_matches = re.findall(r"<h3>(.+?)'s Timetable</h3>", content)
print(f"Found {len(faculty_matches)} faculty timetables")
if faculty_matches:
    print(f"First 5 faculties: {faculty_matches[:5]}")

print("\n" + "=" * 60)
print("TESTING LAB-WISE VIEW (All Labs)")
print("=" * 60)
response = client.post('/timetable/view/', {
    'view_type': 'lab',
    'all_labs': 'true'
})
print(f"Status: {response.status_code}")
content = response.content.decode('utf-8')

# Check for multiple lab headers
lab_matches = re.findall(r'<h3>(.+?) Schedule</h3>', content)
print(f"Found {len(lab_matches)} lab timetables: {lab_matches}")

print("\n" + "=" * 60)
print("TESTING SINGLE SECTION VIEW")
print("=" * 60)
response = client.post('/timetable/view/', {
    'view_type': 'section',
    'year': '1',  # CSE Year 1
    'section': '1'
})
print(f"Status: {response.status_code}")
content = response.content.decode('utf-8')

# Check for single section header
section_header = re.search(r'<h3>(.+?)</h3>', content)
if section_header:
    print(f"Header: {section_header.group(1)}")

print("\nAll tests complete!")
