import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, Course
from collections import defaultdict

print("\n" + "="*80)
print("IDENTIFYING THEORY COURSE VIOLATIONS (MAX HOURS PER DAY)")
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

print(f"\nAnalyzing Timetable ID: {active_timetable.id}")
print("-" * 80)

# Get theory course entries only (one instructor per slot)
all_entries = TimetableEntry.objects.filter(
    timetable=active_timetable,
    course__course_type='THEORY'
).exclude(
    course__course_number__in=['TRAINING', 'SPORTS_LIBRARY', 'COUNS', 'SPORT', 'COUNSELING']
).select_related('course', 'year', 'meeting_time')

# Group by course-year-section-day
day_hours = defaultdict(lambda: defaultdict(list))

for entry in all_entries:
    key = (entry.course.course_number, entry.year.year_name, entry.section_number)
    day = entry.meeting_time.day
    day_hours[key][day].append({
        'time': entry.meeting_time.time,
        'instructor': entry.instructor.name if entry.instructor else 'None'
    })

# Find violations
violations = []

for (course_num, year_name, section), days in day_hours.items():
    course = Course.objects.get(course_number=course_num)
    max_continuous = course.max_continuous_hours
    
    for day, times in days.items():
        hours_on_day = len(times)
        
        if hours_on_day > max_continuous:
            violations.append({
                'course': course_num,
                'course_name': course.course_name,
                'year': year_name,
                'section': section,
                'day': day,
                'hours_on_day': hours_on_day,
                'max_allowed': max_continuous,
                'violation': hours_on_day - max_continuous,
                'times': times
            })

print(f"\n{'='*80}")
print(f"FOUND {len(violations)} THEORY COURSE VIOLATIONS")
print(f"{'='*80}\n")

if violations:
    # Sort by violation severity
    violations.sort(key=lambda x: x['violation'], reverse=True)
    
    for v in violations:
        print(f"⚠️ {v['course']} ({v['course_name']}) - {v['year']} Section {v['section']}")
        print(f"   Day: {v['day']}")
        print(f"   Hours on this day: {v['hours_on_day']} (max allowed: {v['max_allowed']})")
        print(f"   Violation: {v['violation']} extra period(s)")
        for t in v['times']:
            print(f"     - {t['time']}: {t['instructor']}")
        print()
else:
    print("✅ No theory course violations found!")

print("="*80)
