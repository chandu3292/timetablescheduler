#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, r'c:\Users\M srujitha\OneDrive\文서\Desktop\timetablescheduler')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Course

tp_courses = Course.objects.filter(course_number__contains='TP')
print(f"\nFound {tp_courses.count()} TP courses:\n")

for course in tp_courses:
    print(f"Course: {course.course_number} - {course.course_name}")
    print(f"  Type: {course.course_type}")
    print(f"  Hours/Week: {course.hours_per_week}")
    print(f"  Max Continuous: {course.max_continuous_hours}")
    if course.max_continuous_hours < 2:
        print(f"  ⚠️  WARNING: TP course should have max_continuous_hours >= 2")
    else:
        print(f"  ✓ OK: Correctly configured for 2-hour blocks")
    print()

if tp_courses.count() == 0:
    print("No TP courses found - they will be treated as regular theory courses")
