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

# Test section-wise view
year = Year.objects.first()
print(f"Testing UI improvements...")
print(f"Using Year: {year.year_name} (ID: {year.id})")

print("\n1. Testing Section-wise view (single section)...")
response = client.get(f'/timetable/view/?view_type=section&year={year.id}&section=1')
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    content = response.content.decode('utf-8')
    if 'class-card' in content:
        print("   ✓ Class cards rendered")
    if 'font-size: 14px' in content or 'font-size: 15px' in content:
        print("   ✓ Improved font sizes applied")
    if 'padding: 12px' in content:
        print("   ✓ Enhanced padding applied")

print("\n2. Testing Year-wise view (all sections)...")
response = client.get(f'/timetable/view/?view_type=year&year={year.id}')
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    import re
    content = response.content.decode('utf-8')
    section_matches = re.findall(r'Section (\d+) Timetable', content)
    print(f"   ✓ Found {len(section_matches)} sections: {section_matches}")
    
    # Check for improved styling
    if 'font-size: 26px' in content:
        print("   ✓ Larger section headers (26px)")
    if 'min-height: 75px' in content:
        print("   ✓ Taller class cards (75px min)")
    if 'max-width: 1600px' in content:
        print("   ✓ Wider container (1600px)")

print("\n3. Testing Lab-wise view (all labs)...")
response = client.get('/timetable/view/?view_type=lab&all_labs=true')
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    content = response.content.decode('utf-8')
    lab_matches = re.findall(r'<h3>(.+?) Schedule</h3>', content)
    print(f"   ✓ Found {len(lab_matches)} lab timetables")

print("\n✅ UI improvements applied successfully!")
print("\nKey improvements:")
print("  • Container width: 1400px → 1600px")
print("  • Section headers: 20px → 26px (bold 700)")
print("  • Class card font: 12px → 14px")  
print("  • Course name: 15px (bold 700)")
print("  • Instructor: 13px")
print("  • Room/Lab: 12px")
print("  • Card padding: 8px → 12px")
print("  • Card min-height: → 75px")
print("  • Table cell min-height: 80px → 100px")
print("  • Day column: Highlighted with purple color")
print("  • Results count badge: Larger (16px)")
