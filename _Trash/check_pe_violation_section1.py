import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, Course, GeneratedTimetable
from collections import defaultdict

print("\n" + "="*80)
print("PROFESSIONAL ELECTIVE VIOLATION ANALYSIS - SECTION 1")
print("="*80)

# Get active timetable
timetables = GeneratedTimetable.objects.all().order_by('-id')
active_timetable = None
for tt in timetables:
    entry_count = TimetableEntry.objects.filter(timetable=tt).count()
    if entry_count > 100:
        active_timetable = tt
        break

print(f"\nAnalyzing Timetable ID: {active_timetable.id}")
print("-" * 80)

# Get all professional elective entries (23IT5xxx)
pe_entries = TimetableEntry.objects.filter(
    timetable=active_timetable,
    course__course_number__startswith='23IT5',
    section_number=1,
    is_evaluator=False
).select_related('course', 'year', 'meeting_time', 'instructor').order_by('meeting_time__day', 'meeting_time__time')

print("\n3rd Year Section 1 - Professional Elective Entries:")
print("-" * 80)

# Group by course
pe_by_course = defaultdict(list)
for entry in pe_entries:
    pe_by_course[entry.course.course_number].append(entry)

for course_num, entries in sorted(pe_by_course.items()):
    course = entries[0].course
    print(f"\n{course_num} - {course.course_name} (Type: {course.course_type})")
    print(f"  Hours per week: {course.hours_per_week}, Max continuous: {course.max_continuous_hours}")
    print(f"  Scheduled entries: {len(entries)}")
    
    # Group by day
    by_day = defaultdict(list)
    for entry in entries:
        by_day[entry.meeting_time.day].append(entry.meeting_time.time)
    
    print(f"\n  Schedule:")
    for day, times in sorted(by_day.items()):
        print(f"    {day}: {', '.join(sorted(times))}")
        if len(times) > course.max_continuous_hours:
            print(f"      ⚠️ VIOLATION: {len(times)} periods on {day} exceeds max_continuous_hours={course.max_continuous_hours}")
    
    # Check instructor conflicts
    print(f"\n  Instructors:")
    for entry in entries:
        instructor_name = entry.instructor.name if entry.instructor else "None"
        print(f"    {entry.meeting_time.day} {entry.meeting_time.time}: {instructor_name}")

# Check for conflicts at the same time
print("\n" + "="*80)
print("CHECKING FOR CONFLICTS IN SECTION 1")
print("="*80)

all_section1_entries = TimetableEntry.objects.filter(
    timetable=active_timetable,
    section_number=1,
    is_evaluator=False
).select_related('course', 'meeting_time', 'instructor')

# Group by time slot
by_timeslot = defaultdict(list)
for entry in all_section1_entries:
    key = (entry.meeting_time.day, entry.meeting_time.time)
    by_timeslot[key].append(entry)

# Find conflicts
conflicts = []
for (day, time), entries in by_timeslot.items():
    if len(entries) > 1:
        # Check if same instructor is scheduled twice
        instructors = [e.instructor.name if e.instructor else "None" for e in entries]
        courses = [e.course.course_number for e in entries]
        
        conflicts.append({
            'day': day,
            'time': time,
            'courses': courses,
            'instructors': instructors,
            'count': len(entries)
        })

if conflicts:
    print(f"\n❌ Found {len(conflicts)} conflicts in Section 1:\n")
    for conf in conflicts:
        print(f"{conf['day']} {conf['time']}:")
        for i, (course, instructor) in enumerate(zip(conf['courses'], conf['instructors'])):
            print(f"  - {course} (Instructor: {instructor})")
        print()
else:
    print("\n✓ No scheduling conflicts found in Section 1")

# Check day limit violations for PE courses
print("\n" + "="*80)
print("DAY LIMIT VIOLATIONS FOR PE COURSES")
print("="*80)

for course_num, entries in sorted(pe_by_course.items()):
    course = entries[0].course
    
    # Count hours per day
    by_day = defaultdict(int)
    for entry in entries:
        by_day[entry.meeting_time.day] += 1
    
    violations = []
    for day, hours in by_day.items():
        if hours > course.max_continuous_hours:
            violations.append((day, hours))
    
    if violations:
        print(f"\n❌ {course_num} - {course.course_name}:")
        print(f"   Max allowed per day: {course.max_continuous_hours} hours")
        for day, hours in violations:
            print(f"   {day}: {hours} hours (EXCEEDS by {hours - course.max_continuous_hours})")
    else:
        print(f"\n✓ {course_num} - {course.course_name}: All days within limit (max {course.max_continuous_hours} hrs/day)")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80 + "\n")
