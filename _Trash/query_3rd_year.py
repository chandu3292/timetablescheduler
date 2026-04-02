#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Year, TimetableEntry, Course

print("="*80)
print("1. CHECKING 3RD YEAR TIMETABLE ENTRIES")
print("="*80)
year = Year.objects.filter(year_name='3rd Year').first()
if year:
    print(f"✓ Found: {year}")
    
    # Total entries
    total_entries = TimetableEntry.objects.filter(year=year).count()
    print(f"\nTotal timetable entries for 3rd Year: {total_entries}")
else:
    print("✗ 3rd Year not found")
    exit(1)

print("\n" + "="*80)
print("2. OE COURSE (23IT6121) ENTRIES")
print("="*80)
oe_course = Course.objects.filter(course_number='23IT6121').first()
if oe_course:
    oe_entries = TimetableEntry.objects.filter(year=year, course=oe_course).select_related('meeting_time', 'instructor')
    print(f"Course: {oe_course}")
    print(f"Total OE entries: {oe_entries.count()}\n")
    for entry in oe_entries:
        print(f"  Section {entry.section_number}: {entry.meeting_time} | Instructor: {entry.instructor} | Batch: {entry.batch}")
else:
    print("✗ OE course (23IT6121) not found")

print("\n" + "="*80)
print("3. ENTRIES PER SECTION")
print("="*80)
entries = TimetableEntry.objects.filter(year=year).select_related('course', 'meeting_time', 'instructor')

# Count per section
for section in [1, 2, 3]:
    section_entries = entries.filter(section_number=section)
    count = section_entries.count()
    courses = section_entries.values('course__course_number').distinct().count()
    print(f"Section {section}: {count} entries, {courses} unique courses")

print("\n" + "="*80)
print("4. FULL SCHEDULE FOR EACH SECTION")
print("="*80)
for section in [1, 2, 3]:
    section_entries = entries.filter(section_number=section).order_by('meeting_time__day', 'meeting_time__time')
    if section_entries.exists():
        print(f"\n--- SECTION {section} ---")
        day_schedule = {}
        for entry in section_entries:
            day = entry.meeting_time.day
            time = entry.meeting_time.time
            course = entry.course.course_number
            if day not in day_schedule:
                day_schedule[day] = []
            day_schedule[day].append((time, course))
        
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        for day in days_order:
            if day in day_schedule:
                print(f"{day:12} →", end=" ")
                for time, course in day_schedule[day]:
                    print(f"{course} ({time})", end=" | ")
                print()
    else:
        print(f"\nSection {section}: No entries found")

print("\n" + "="*80)
print("5. CHECKING FOR GAPS IN COURSE ASSIGNMENTS")
print("="*80)
# Get all courses for 3rd year
all_courses = year.courses.all()
print(f"Total courses assigned to 3rd Year: {all_courses.count()}\n")

for section in [1, 2, 3]:
    print(f"--- SECTION {section} COURSE GAP ANALYSIS ---")
    section_entries = entries.filter(section_number=section)
    scheduled_courses = set(section_entries.values_list('course__course_number', flat=True).distinct())
    
    expected_courses = set(all_courses.values_list('course_number', flat=True))
    
    if scheduled_courses == expected_courses:
        print(f"✓ All {len(scheduled_courses)} courses scheduled for Section {section}")
    else:
        missing = expected_courses - scheduled_courses
        extra = scheduled_courses - expected_courses
        if missing:
            print(f"✗ Missing courses (not scheduled): {', '.join(sorted(missing))}")
        if extra:
            print(f"⚠ Extra courses scheduled: {', '.join(sorted(extra))}")
    print()
