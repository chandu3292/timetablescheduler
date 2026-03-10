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

# Check what year IDs exist
years = Year.objects.all()
print("Available Years:")
for year in years:
    print(f"  ID: {year.id}, Name: {year.year_name}")

# Test year-wise view with correct year ID
if years.exists():
    year_id = years.first().id
    print(f"\nTesting with Year ID: {year_id}")
    
    response = client.post('/timetable/view/', {
        'view_type': 'year',
        'year': str(year_id)
    })
    
    # Check the context variables passed to template
    if hasattr(response, 'context') and response.context:
        print("\nContext variables:")
        for key in ['view_type', 'selected_year', 'sections_data', 'schedule', 'total_classes']:
            if key in response.context:
                value = response.context[key]
                if key == 'sections_data' and value:
                    print(f"  {key}: List with {len(value)} items")
                    for i, section_data in enumerate(value[:2]):  # Show first 2
                        print(f"    Section {section_data.get('section_number', '?')}: {section_data.get('total_classes', 0)} classes")
                elif key == 'schedule' and value:
                    print(f"  {key}: List with {len(value)} classes")
                else:
                    print(f"  {key}: {value}")
            else:
                print(f"  {key}: NOT IN CONTEXT")
