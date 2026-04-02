import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, Course, GeneratedTimetable
from collections import defaultdict

print("\n" + "="*80)
print("3RD YEAR TIMETABLE ANALYSIS (ID 366)")
print("="*80)

# Get timetable 366
timetable = GeneratedTimetable.objects.get(id=366)

print(f"\nTimetable ID: {timetable.id} - {timetable.year.year_name}")
print(f"Generated at: {timetable.generated_at}")
print(f"Entry count: {TimetableEntry.objects.filter(timetable=timetable).count()}")
print("-" * 80)

# Check PE courses specifically
print("\n" + "="*80)
print("PROFESSIONAL ELECTIVE COURSES - DAY LIMIT CHECK")
print("="*80)

pe_courses = ['23IT5121', '23IT5131']

for course_num in pe_courses:
    course = Course.objects.get(course_number=course_num)
    print(f"\n{course_num} - {course.course_name}")
    print(f"  Type: {course.course_type}, Max per day: {course.max_continuous_hours}, Total weekly: {course.hours_per_week}")
    
    for section in [1, 2, 3]:
        entries = TimetableEntry.objects.filter(
            timetable=timetable,
            course=course,
            section_number=section,
            is_evaluator=False
        ).select_related('meeting_time').order_by('meeting_time__day', 'meeting_time__time')
        
        # Group by day
        by_day = defaultdict(list)
        for entry in entries:
            by_day[entry.meeting_time.day].append(entry.meeting_time.time)
        
        print(f"\n  Section {section}:")
        violations = []
        for day, times in sorted(by_day.items()):
            status = "✅" if len(times) <= course.max_continuous_hours else "❌"
            print(f"    {status} {day}: {len(times)} period(s) - {', '.join(times)}")
            if len(times) > course.max_continuous_hours:
                violations.append((day, len(times)))
        
        if violations:
            print(f"    ⚠️ VIOLATIONS: {len(violations)} days exceed max {course.max_continuous_hours} hrs/day")
            for day, count in violations:
                print(f"       - {day}: {count} hrs (exceeds by {count - course.max_continuous_hours})")
        else:
            print(f"    ✓ All days within limit")

# Check OE course
print("\n" + "="*80)
print("OPEN ELECTIVE COURSE - DAY LIMIT CHECK")
print("="*80)

oe_course = Course.objects.get(course_number='23IT6121')
print(f"\n{oe_course.course_number} - {oe_course.course_name}")
print(f"  Type: {oe_course.course_type}, Max per day: {oe_course.max_continuous_hours}, Total weekly: {oe_course.hours_per_week}")

for section in [1, 2, 3]:
    entries = TimetableEntry.objects.filter(
        timetable=timetable,
        course=oe_course,
        section_number=section,
        is_evaluator=False
    ).select_related('meeting_time').order_by('meeting_time__day', 'meeting_time__time')
    
    # Group by day
    by_day = defaultdict(list)
    for entry in entries:
        by_day[entry.meeting_time.day].append(entry.meeting_time.time)
    
    print(f"\n  Section {section}:")
    violations = []
    for day, times in sorted(by_day.items()):
        status = "✅" if len(times) <= oe_course.max_continuous_hours else "❌"
        print(f"    {status} {day}: {len(times)} period(s) - {', '.join(times)}")
        if len(times) > oe_course.max_continuous_hours:
            violations.append((day, len(times)))
    
    if violations:
        print(f"    ⚠️ VIOLATIONS: {len(violations)} days exceed max {oe_course.max_continuous_hours} hrs/day")
    else:
        print(f"    ✓ All days within limit")

# Check alignment
print("\n" + "="*80)
print("ELECTIVE ALIGNMENT CHECK")
print("="*80)

for course_num in ['23IT6121', '23IT5121', '23IT5131']:
    course = Course.objects.get(course_number=course_num)
    print(f"\n{course_num} - {course.course_name}:")
    
    # Get time slots for each section
    section_slots = {}
    for section in [1, 2, 3]:
        entries = TimetableEntry.objects.filter(
            timetable=timetable,
            course=course,
            section_number=section,
            is_evaluator=False
        ).select_related('meeting_time')
        
        slots = [(e.meeting_time.day, e.meeting_time.time) for e in entries]
        section_slots[section] = sorted(slots)
    
    # Check if all sections have same slots
    if len(section_slots) >= 2:
        sec1_slots = set(section_slots[1])
        all_same = all(set(section_slots[sec]) == sec1_slots for sec in section_slots.keys())
        
        if all_same:
            print(f"  ✅ ALIGNED - All sections at same times:")
            for day, time in sorted(sec1_slots):
                print(f"     {day} {time}")
        else:
            print(f"  ❌ NOT ALIGNED - Different times per section:")
            for sec, slots in sorted(section_slots.items()):
                print(f"     Section {sec}: {slots}")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80 + "\n")
