"""
Quick test to verify timetable view loads correctly
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from django.test import RequestFactory
from SchedulerApp.views import timetable
from SchedulerApp.models import Year

print("="*80)
print("TESTING TIMETABLE VIEW")
print("="*80)

factory = RequestFactory()

# Test for each year
for year in Year.objects.all().order_by('id'):
    print(f"\nTesting {year.year_name} (ID: {year.id})...")
    
    # Create request without regenerate parameter
    request = factory.get(f'/timetableGeneration/?year={year.id}')
    
    try:
        response = timetable(request)
        
        if response.status_code == 200:
            # Check if it loaded from database
            if 'from_database' in response.context_data:
                if response.context_data['from_database']:
                    print(f"  ✅ SUCCESS - Loaded from database")
                    print(f"     Classes: {len(response.context_data.get('schedule', []))}")
                    print(f"     Fitness: {response.context_data.get('fitness_score', 'N/A')}")
                    print(f"     Generated: {response.context_data.get('generated_at', 'N/A')}")
                else:
                    print(f"  ⚠️  Generated new (should load from DB)")
            else:
                print(f"  ✅ Response OK but no context data")
        else:
            print(f"  ❌ Error - Status code: {response.status_code}")
            
    except Exception as e:
        print(f"  ❌ Exception: {e}")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print("\nAll years should load existing timetables from database.")
print("If you see 'Generated new', the view is regenerating instead of loading.")
print("\nTo view in browser:")
print("  1. Navigate to http://localhost:8005")
print("  2. Click 'View Timetable'")
print("  3. Select a year")
print("  4. Should show existing timetable (not regenerate)")
