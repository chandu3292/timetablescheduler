import os
import sys
import django

sys.path.insert(0, r'c:\Users\M srujitha\OneDrive\文서\Desktop\timetablescheduler')
os.chdir(r'c:\Users\M srujitha\OneDrive\文서\Desktop\timetablescheduler')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Year, GeneratedTimetable, TimetableEntry

# Get 3rd Year
third_year = Year.objects.filter(year_name='3rd Year').first()
if not third_year:
    print("3rd Year not found!")
    exit(1)

print("\n" + "="*80)
print("CLEARING CURRENT 3RD YEAR TIMETABLE")
print("="*80)

# Delete existing timetable
gen_timetable = GeneratedTimetable.objects.filter(year=third_year).first()
if gen_timetable:
    entry_count = gen_timetable.entries.count()
    print(f"\nFound existing timetable with {entry_count} entries")
    print("Deleting all entries...")
    gen_timetable.entries.all().delete()
    gen_timetable.delete()
    print("✓ Deleted")
else:
    print("\nNo existing timetable found")

print("\n" + "="*80)
print("Now regenerate the timetable from the web interface")
print("="*80)
