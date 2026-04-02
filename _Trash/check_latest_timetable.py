import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, Course, GeneratedTimetable
from collections import defaultdict

print("\n" + "="*80)
print("LATEST TIMETABLE ANALYSIS - ALL VIOLATIONS")
print("="*80)

# Get the LATEST timetable
latest_timetable = GeneratedTimetable.objects.all().order_by('-id').first()

print(f"\nLatest Timetable ID: {latest_timetable.id}")
print(f"Generated at: {latest_timetable.generated_at}")
print(f"Entry count: {TimetableEntry.objects.filter(timetable=latest_timetable).count()}")
print("-" * 80)

# Get all theory/elective courses (exclude labs and special courses)
theory_entries = TimetableEntry.objects.filter(
    timetable=latest_timetable,
    is_evaluator=False,
    batch='FULL'
).exclude(
    course__course_number__in=['TRAINING', 'SPORTS_LIBRARY', 'COUNS', 'SPORT', 'COUNSELING']
).select_related('course', 'year', 'meeting_time')

# Group by course-year-section
course_schedule = defaultdict(lambda: defaultdict(list))

for entry in theory_entries:
    key = (entry.course.course_number, entry.year.year_name, entry.section_number)
    course_schedule[key][entry.meeting_time.day].append(entry.meeting_time.time)

# Check for violations
violations = []
all_courses = []

for (course_num, year_name, section), days in course_schedule.items():
    course = Course.objects.get(course_number=course_num)
    max_continuous = course.max_continuous_hours
    
    course_info = {
        'course': course_num,
        'name': course.course_name,
        'year': year_name,
        'section': section,
        'type': course.course_type,
        'max_per_day': max_continuous,
        'total_weekly': sum(len(times) for times in days.values()),
        'days': {}
    }
    
    has_violation = False
    for day, times in days.items():
        hours_on_day = len(times)
        course_info['days'][day] = hours_on_day
        
        if hours_on_day > max_continuous:
            violations.append({
                'course': course_num,
                'name': course.course_name,
                'year': year_name,
                'section': section,
                'day': day,
                'hours': hours_on_day,
                'max': max_continuous,
                'excess': hours_on_day - max_continuous,
                'type': course.course_type
            })
            has_violation = True
    
    all_courses.append((course_info, has_violation))

print("\n" + "="*80)
print("VIOLATION SUMMARY")
print("="*80)

if violations:
    print(f"\n❌ Found {len(violations)} DAY LIMIT VIOLATIONS:\n")
    
    # Group by course
    by_course = defaultdict(list)
    for v in violations:
        by_course[v['course']].append(v)
    
    for course_num, course_violations in sorted(by_course.items()):
        v = course_violations[0]
        print(f"{course_num} - {v['name']} (Type: {v['type']}, Max: {v['max']} hrs/day)")
        for violation in course_violations:
            print(f"  ❌ {violation['year']} Section {violation['section']} - {violation['day']}: {violation['hours']} hours (exceeds by {violation['excess']})")
        print()
else:
    print("\n✅ NO VIOLATIONS FOUND - All courses respect max_continuous_hours per day!")

# Show elective alignment
print("\n" + "="*80)
print("ELECTIVE ALIGNMENT CHECK")
print("="*80)

# Check OE/PE courses
oe_pe_courses = ['23IT6121', '23IT5121', '23IT5131']

for course_num in oe_pe_courses:
    course = Course.objects.filter(course_number=course_num).first()
    if not course:
        continue
    
    print(f"\n{course_num} - {course.course_name}:")
    
    # Get entries for all sections
    entries = TimetableEntry.objects.filter(
        timetable=latest_timetable,
        course__course_number=course_num,
        is_evaluator=False
    ).select_related('meeting_time').order_by('section_number', 'meeting_time__day', 'meeting_time__time')
    
    # Group by section
    by_section = defaultdict(list)
    for entry in entries:
        by_section[entry.section_number].append((entry.meeting_time.day, entry.meeting_time.time))
    
    # Show schedule for each section
    for section in sorted(by_section.keys()):
        times = sorted(by_section[section])
        print(f"  Section {section}: {times}")
    
    # Check if aligned
    if len(by_section) > 1:
        section_1_times = set(by_section[1])
        all_aligned = all(set(by_section[sec]) == section_1_times for sec in by_section.keys())
        
        if all_aligned:
            print(f"  ✅ ALIGNED - All sections have same time slots")
        else:
            print(f"  ❌ NOT ALIGNED - Sections have different time slots")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80 + "\n")
