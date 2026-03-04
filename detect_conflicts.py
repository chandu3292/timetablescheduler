#!/usr/bin/env python
"""Detect actual conflicts in the generated timetable"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, GeneratedTimetable
from collections import defaultdict

# Get most recent timetable
gt = GeneratedTimetable.objects.select_related('year').order_by('-generated_at').first()

if not gt:
    print("No timetables found")
    exit()

print(f"Analyzing: {gt.year.year_name}")
print(f"Fitness: {gt.fitness_score:.2f}%")
print(f"Generated: {gt.generated_at}")
print("=" * 80)

# Get ALL entries (including duplicates for multi-instructor labs)
all_entries = TimetableEntry.objects.filter(timetable=gt).select_related(
    'course', 'instructor', 'meeting_time', 'lab_room'
).order_by('meeting_time__day', 'meeting_time__time')

# Detect conflicts
print("\n🔍 CONFLICT DETECTION:\n")

# 1. INSTRUCTOR CONFLICTS - Same instructor, different sections, same time
instructor_conflicts = defaultdict(list)
for entry in all_entries:
    key = (entry.instructor.name, entry.meeting_time.day, entry.meeting_time.time)
    instructor_conflicts[key].append(entry)

print("1️⃣  INSTRUCTOR CONFLICTS (same instructor, multiple sections, same time):")
conflict_count = 0
for (instructor, day, time), entries in instructor_conflicts.items():
    # Get unique sections
    sections = set((e.section_number, e.course.course_name) for e in entries)
    if len(sections) > 1:
        conflict_count += 1
        print(f"   ❌ {instructor} - {day} {time}")
        for section, course in sections:
            print(f"      • Section {section}: {course}")

if conflict_count == 0:
    print("   ✅ No instructor conflicts found")

# 2. SECTION CONFLICTS - Same section, different courses, same time
section_conflicts = defaultdict(list)
for entry in all_entries:
    key = (entry.section_number, entry.meeting_time.day, entry.meeting_time.time)
    section_conflicts[key].append(entry)

print("\n2️⃣  SECTION CONFLICTS (same section, multiple courses, same time):")
conflict_count = 0
for (section, day, time), entries in section_conflicts.items():
    # Get unique courses
    courses = set(e.course.course_name for e in entries)
    if len(courses) > 1:
        conflict_count += 1
        print(f"   ❌ Section {section} - {day} {time}")
        for course in courses:
            print(f"      • {course}")

if conflict_count == 0:
    print("   ✅ No section conflicts found")

# 3. LAB ROOM CONFLICTS - Same lab room, different sections, same time
lab_conflicts = defaultdict(list)
for entry in all_entries:
    if entry.lab_room:
        key = (entry.lab_room.room_number, entry.meeting_time.day, entry.meeting_time.time)
        lab_conflicts[key].append(entry)

print("\n3️⃣  LAB ROOM CONFLICTS (same room, multiple sections, same time):")
conflict_count = 0
for (room, day, time), entries in lab_conflicts.items():
    # Get unique section-course combinations
    sections = set((e.section_number, e.course.course_name, e.year.year_name) for e in entries)
    if len(sections) > 1:
        conflict_count += 1
        print(f"   ❌ {room} - {day} {time}")
        for section, course, year in sections:
            print(f"      • {year} Section {section}: {course}")

if conflict_count == 0:
    print("   ✅ No lab room conflicts found")

print("\n" + "=" * 80)
print(f"Total entries in database: {all_entries.count()}")
