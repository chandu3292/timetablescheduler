#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Year, TimetableEntry, Course, SpecialPeriod
from django.db.models import Count, Q

print("="*80)
print("COMPREHENSIVE 3RD YEAR TIMETABLE ANALYSIS")
print("="*80)

year = Year.objects.filter(year_name='3rd Year').first()
if not year:
    print("✗ 3rd Year not found")
    exit(1)

# Get all courses and special periods
all_courses = year.courses.all().order_by('course_number')
special_periods = SpecialPeriod.objects.filter(year=year)

print("\n📋 COURSES ASSIGNED TO 3RD YEAR:")
print("-" * 80)
print(f"Total courses: {all_courses.count()}\n")
print(f"{'Course':<15} {'Name':<30} {'Type':<10} {'Hours/Wk':<10}")
print("-" * 65)
for course in all_courses:
    print(f"{course.course_number:<15} {course.course_name:<30} {course.course_type:<10} {course.hours_per_week:<10}")

print("\n" + "="*80)
print("📊 SCHEDULE STATISTICS")
print("="*80)

# Count entries per section and course type
for section in [1, 2, 3]:
    print(f"\n--- SECTION {section} ---")
    section_entries = TimetableEntry.objects.filter(year=year, section_number=section).select_related('course', 'meeting_time')
    
    theory_count = section_entries.filter(course__course_type='THEORY').count()
    lab_count = section_entries.filter(course__course_type='LAB').count()
    elective_count = section_entries.filter(course__course_type='ELECTIVE').count()
    
    print(f"Total entries: {section_entries.count()}")
    print(f"  • THEORY:   {theory_count}")
    print(f"  • LAB:      {lab_count}")
    print(f"  • ELECTIVE: {elective_count}")
    
    # Entries per day
    entries_by_day = section_entries.values('meeting_time__day').annotate(count=Count('id')).order_by('meeting_time__day')
    print(f"\nEntries per day:")
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    for entry_by_day in entries_by_day:
        day = entry_by_day['meeting_time__day']
        count = entry_by_day['count']
        index = days_order.index(day) if day in days_order else 999
        print(f"  {day:<12} {count}")

print("\n" + "="*80)
print("🔍 OE COURSE (23IT6121) DETAILED INFORMATION")
print("="*80)

oe_course = Course.objects.filter(course_number='23IT6121').first()
if oe_course:
    print(f"Course: {oe_course.course_number} - {oe_course.course_name}")
    print(f"Type: {oe_course.course_type}")
    print(f"Hours per week: {oe_course.hours_per_week}")
    print(f"Max continuous hours: {oe_course.max_continuous_hours}")
    print(f"Priority: {oe_course.priority}")
    print(f"\nSchedule across all sections:")
    
    oe_entries = TimetableEntry.objects.filter(year=year, course=oe_course).select_related('meeting_time', 'instructor')
    for section in [1, 2, 3]:
        section_oe = oe_entries.filter(section_number=section)
        if section_oe.exists():
            entry = section_oe.first()
            print(f"  Section {section}: {entry.meeting_time.day} @ {entry.meeting_time.time} | Instructor: {entry.instructor}")
        else:
            print(f"  Section {section}: NOT SCHEDULED ⚠️")

print("\n" + "="*80)
print("❓ CHECKING FOR GAPS AND ISSUES")
print("="*80)

all_course_numbers = set(all_courses.values_list('course_number', flat=True))

for section in [1, 2, 3]:
    print(f"\n--- SECTION {section} ---")
    section_entries = TimetableEntry.objects.filter(year=year, section_number=section)
    scheduled_courses = set(section_entries.values_list('course__course_number', flat=True).distinct())
    
    missing = all_course_numbers - scheduled_courses
    if missing:
        print(f"❌ MISSING COURSES: {', '.join(sorted(missing))}")
    else:
        print(f"✓ All {len(scheduled_courses)} courses scheduled")
    
    # Check for duplicate slots (same course on same day-time)
    duplicate_slots = TimetableEntry.objects.filter(
        year=year, 
        section_number=section
    ).values('course', 'meeting_time').annotate(
        slot_count=Count('id')
    ).filter(slot_count__gt=1)
    
    if duplicate_slots.exists():
        print(f"\n⚠️ Duplicate time slots for same course:")
        for dup in duplicate_slots:
            course_obj = Course.objects.get(course_number=dup['course'])
            count = dup['slot_count']
            print(f"  {course_obj.course_number}: {count} entries in same slot")
    else:
        print(f"✓ No duplicate course-slot assignments")

print("\n" + "="*80)
