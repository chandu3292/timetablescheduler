import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, Year

print("=" * 80)
print("ANALYZING GENERATED TIMETABLES WITH MULTIPLE INSTRUCTORS")
print("=" * 80)

# Check a specific lab to see how many entries were created
second_year = Year.objects.filter(year_name__icontains='2').first()
if second_year:
    # Get DBMS Lab entries for section 1
    dbms_entries = TimetableEntry.objects.filter(
        year=second_year,
        section_number=1,
        course__course_name__icontains='DBMS Lab'
    )
    
    if dbms_entries.exists():
        print(f"\nDBMS Lab Section 1 entries: {dbms_entries.count()}")
        print("-" * 80)
        
        # Group by time to see how many instructors per time slot
        from collections import defaultdict
        time_instructors = defaultdict(set)
        time_rooms = defaultdict(set)
        
        for entry in dbms_entries:
            key = f"{entry.meeting_time.day} {entry.meeting_time.time}"
            time_instructors[key].add(entry.instructor.uid if entry.instructor else "None")
            time_rooms[key].add(entry.lab_room.lab_name if entry.lab_room else "None")
        
        print("Time slots with instructors:")
        for time_key in sorted(time_instructors.keys()):
            instructors = time_instructors[time_key]
            rooms = time_rooms[time_key]
            print(f"  {time_key}: {len(instructors)} instructors ({', '.join(instructors)}) in {rooms}")
        
        print(f"\nTotal DBMS Lab entries: {dbms_entries.count()}")
        print(f"Unique time slots: {len(time_instructors)}")
        print(f"Average instructors per slot: {dbms_entries.count() / len(time_instructors):.1f}")

# Show totals
print("\n" + "=" * 80)
print("TOTAL COUNTS PER YEAR:")
print("=" * 80)

for year in Year.objects.all().order_by('id'):
    count = TimetableEntry.objects.filter(year=year).count()
    print(f"{year.year_name}: {count} entries")

print("\n" + "=" * 80)
print("EXPLANATION:")
print("=" * 80)
print("If labs have multiple instructors, we now create one entry per instructor.")
print("This means a 3-hour lab with 3 instructors = 9 entries total (3 hrs × 3 instructors)")
print("This is CORRECT behavior - each instructor sees the lab in their timetable.")
print("=" * 80)
