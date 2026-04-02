#!/usr/bin/env python
"""
Deep dive into OE (23IT6121) and other theory courses - see actual timetable entries
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from SchedulerApp.models import TimetableEntry, Course, Year, MeetingTime
from django.db.models import Count

# Get 3rd year
try:
    year = Year.objects.get(year_name__icontains='3')
except Year.DoesNotExist:
    print("No 3rd year found")
    sys.exit(1)

# Get courses
theory_courses = ['23IT4121', '23IT4122', '23IT5121', '23IT5131', '23IT6121']

print("="*120)
print("3RD YEAR THEORY COURSES - ACTUAL TIMETABLE ENTRIES")
print("="*120)

for course_num in theory_courses:
    try:
        course = Course.objects.get(course_number=course_num)
        print(f"\n{course.course_name} ({course_num}) - Required: {course.hours_per_week} hrs/week")
        print(f"Course Type: {course.course_type}")
        print("-" * 120)
        
        # Get all entries for this course
        entries = TimetableEntry.objects.filter(
            course=course,
            year=year
        ).select_related('instructor', 'meeting_time').order_by('section_number', 'meeting_time__day')
        
        if not entries.exists():
            print("  NO ENTRIES IN DATABASE")
        else:
            current_section = None
            for entry in entries:
                if entry.section_number != current_section:
                    current_section = entry.section_number
                    print(f"\n  SECTION {entry.section_number}:")
                
                instructor_name = entry.instructor.name if entry.instructor else "NO INSTRUCTOR"
                print(f"    {entry.meeting_time.day:<12} {entry.meeting_time.time:<20} Instructor: {instructor_name:<25} Batch: {entry.batch}")
        
        print()
        
    except Course.DoesNotExist:
        print(f"\nCourse {course_num} not found in database\n")

# Also show summary of what's scheduled
print("\n" + "="*120)
print("COMPARISON: SCHEDULED VS REQUIRED HOURS")
print("="*120)

for course_num in theory_courses:
    try:
        course = Course.objects.get(course_number=course_num)
        
        entries_by_section = {}
        entries = TimetableEntry.objects.filter(
            course=course,
            year=year
        ).values('section_number').annotate(count=Count('id'))
        
        for entry in entries:
            entries_by_section[entry['section_number']] = entry['count']
        
        print(f"\n{course.course_name:<25} ({course_num})")
        for section in [1, 2, 3]:
            scheduled = entries_by_section.get(section, 0)
            required = course.hours_per_week
            gap = scheduled - required
            status = "✓" if gap == 0 else "✗"
            print(f"  Section {section}: {scheduled:2d} hrs scheduled / {required:2d} hrs required {status} (Gap: {gap:+3d})")
        
    except Course.DoesNotExist:
        pass
