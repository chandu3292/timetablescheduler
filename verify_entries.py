import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, Year

print("\n=== TIMETABLE ENTRY COUNTS ===\n")

for year in Year.objects.all().order_by('id'):
    entries = TimetableEntry.objects.filter(year=year)
    print(f"{year.year_name}: {entries.count()} entries")
    
    # Show unique courses
    unique_courses = entries.values('course__course_name').distinct().count()
    print(f"   {unique_courses} unique courses")
    
    # Show unique sections
    unique_sections = entries.values('section_number').distinct().count()
    print(f"   {unique_sections} unique sections")
    
    print()

print(f"\nTotal: {TimetableEntry.objects.count()} entries")
