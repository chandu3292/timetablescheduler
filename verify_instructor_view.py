#!/usr/bin/env python
"""Verify that all instructors see their assigned labs"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, GeneratedTimetable, Course, Instructor

# Get most recent timetable
gt = GeneratedTimetable.objects.select_related('year').order_by('-generated_at').first()

if not gt:
    print("No timetables found")
    exit()

print(f"Checking: {gt.year.year_name}")
print("=" * 80)

# Check java lab (IT218) - has 3 instructors per section
java_course = Course.objects.filter(course_number='IT218').first()

if java_course:
    print(f"\n{java_course.course_number} - {java_course.course_name}")
    print(f"Total instructors: {java_course.instructors.count()}")
    
    for section in [1, 2, 3]:
        print(f"\n  Section {section}:")
        entries = TimetableEntry.objects.filter(
            timetable=gt,
            course=java_course,
            section_number=section
        ).select_related('instructor', 'meeting_time').order_by('instructor__name', 'meeting_time__time')
        
        # Group by instructor
        by_instructor = {}
        for e in entries:
            inst_name = e.instructor.name
            if inst_name not in by_instructor:
                by_instructor[inst_name] = []
            by_instructor[inst_name].append(f"{e.meeting_time.day} {e.meeting_time.time}")
        
        for inst_name, times in by_instructor.items():
            print(f"    {inst_name}: {len(times)} hours")
            for time in times:
                print(f"      - {time}")

print("\n" + "=" * 80)
print("VERIFICATION:")
print("✓ Each instructor should see all hours of the lab they teach")
print("✓ Main timetable should show lab only once per time slot")
print("✓ Instructor timetable should show lab for each assigned instructor")
