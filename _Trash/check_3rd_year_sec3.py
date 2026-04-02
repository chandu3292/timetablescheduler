import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry
from collections import defaultdict

print("\n" + "="*80)
print("CHECKING ALL COURSES IN 3RD YEAR SECTION 3")
print("="*80)

# Get the active timetable
from SchedulerApp.models import GeneratedTimetable
timetables = GeneratedTimetable.objects.all().order_by('-id')
active_timetable = None

for tt in timetables:
    entry_count = TimetableEntry.objects.filter(timetable=tt).count()
    if entry_count > 100:
        active_timetable = tt
        break

# Get all entries for 3rd Year Section 3
entries = TimetableEntry.objects.filter(
    timetable=active_timetable,
    year__year_name='3rd Year',
    section_number=3
).select_related('course', 'instructor', 'meeting_time').order_by('meeting_time__day', 'meeting_time__time')

# Group by course and day
course_day_hours = defaultdict(lambda: defaultdict(list))

for entry in entries:
    course_key = (entry.course.course_number, entry.course.course_name)
    day = entry.meeting_time.day
    course_day_hours[course_key][day].append({
        'time': entry.meeting_time.time,
        'instructor': entry.instructor.name if entry.instructor else 'None',
        'max_continuous': entry.course.max_continuous_hours
    })

print(f"\n3rd Year Section 3 Course Distribution:")
print("-" * 80)

for (course_num, course_name), days in sorted(course_day_hours.items()):
    total_hours = sum(len(times) for times in days.values())
    print(f"\n{course_num} ({course_name}) - Total: {total_hours} hours")
    
    for day, times in sorted(days.items()):
        hours_on_day = len(times)
        max_cont = times[0]['max_continuous'] if times else 0
        violation_mark = " ⚠️ VIOLATION!" if hours_on_day > max_cont else ""
        print(f"  {day}: {hours_on_day} hours (max allowed: {max_cont}){violation_mark}")
        for t in times:
            print(f"    {t['time']}: {t['instructor']}")

print("\n" + "="*80)
