import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, Year

# Check for 3rd year timetable entries
year_id = 13
 
print("Checking 3rd Year (ID=13) timetable entries...")
print("-" * 50)

# Check total entries for this year
total_entries = TimetableEntry.objects.filter(year_id=year_id).count()
print(f"Total TimetableEntry records for 3rd Year: {total_entries}")

if total_entries > 0:
    # Show section breakdown
    for section in [1, 2, 3]:
        count = TimetableEntry.objects.filter(year_id=year_id, section_number=section).count()
        print(f"  Section {section}: {count} entries")
    
    # Show first 5 entries
    print("\nFirst 5 entries:")
    entries = TimetableEntry.objects.filter(year_id=year_id).select_related('course', 'instructor', 'meeting_time')[:5]
    for entry in entries:
        print(f"  Section {entry.section_number}: {entry.meeting_time.day} {entry.meeting_time.time} - {entry.course.course_name} ({entry.instructor.name if entry.instructor else 'No instructor'})")
else:
    print("\n⚠️ NO TIMETABLE ENTRIES FOUND!")
    print("The timetable has not been generated yet.")
    print("\nYou need to:")
    print("1. Go to 'Timetable' page")
    print("2. Select the year and generate the timetable")
