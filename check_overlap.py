#!/usr/bin/env python
"""Check for overlapping/duplicate lab entries in the database"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, GeneratedTimetable, Course
from collections import Counter

# Get most recent timetable
gt = GeneratedTimetable.objects.select_related('year').order_by('-generated_at').first()

if not gt:
    print("No timetables found in database")
    exit()

print(f"Checking timetable for: {gt.year.year_name}")
print(f"Generated: {gt.generated_at}")
print(f"Fitness: {gt.fitness_score:.2f}%")
print("=" * 70)

# Get all lab courses
lab_courses = Course.objects.filter(course_type='LAB', year=gt.year)

for course in lab_courses:
    print(f"\n{course.course_number} - {course.course_name} (max_continuous_hours={course.max_continuous_hours})")
    
    for section in [1, 2, 3]:
        entries = TimetableEntry.objects.filter(
            timetable=gt,
            course=course,
            section_number=section
        ).select_related('meeting_time').order_by('meeting_time__day', 'meeting_time__time')
        
        if entries:
            # Group by day
            by_day = {}
            for e in entries:
                day = e.meeting_time.day
                time = e.meeting_time.time
                if day not in by_day:
                    by_day[day] = []
                by_day[day].append(time)
            
            # Check each day
            for day, times in by_day.items():
                time_counts = Counter(times)
                duplicates = {t: c for t, c in time_counts.items() if c > 1}
                
                if duplicates:
                    print(f"  ⚠️  Section {section} - {day}: DUPLICATES FOUND!")
                    for time, count in duplicates.items():
                        print(f"       {time} appears {count} times")
                elif len(times) > course.max_continuous_hours:
                    print(f"  ⚠️  Section {section} - {day}: {len(times)} hours (expected {course.max_continuous_hours})")
                    print(f"       Times: {', '.join(times)}")
                else:
                    print(f"  ✓ Section {section} - {day}: {len(times)} hours - {', '.join(times)}")
