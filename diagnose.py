#!/usr/bin/env python
"""Diagnose why timetable generation is failing"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import *

year = Year.objects.get(year_name='2nd Year')
courses = year.courses.all().order_by('course_number')

print(f"\n{'='*80}")
print(f"DIAGNOSTIC REPORT: Why is fitness stuck at 0.06%?")
print(f"{'='*80}\n")

# 1. Check total hours
total_lab_hours = sum(c.hours_per_week for c in courses if c.course_type == 'LAB')
total_theory_hours = sum(c.hours_per_week for c in courses if c.course_type == 'THEORY')
total_hours = total_lab_hours + total_theory_hours

print(f"1️⃣  CAPACITY CHECK:")
print(f"   LAB hours per section: {total_lab_hours}")
print(f"   THEORY hours per section: {total_theory_hours}")
print(f"   Total hours per section: {total_hours}")
print(f"   Available slots: 47 (8 slots × 6 days - 1 lunch)")
print(f"   Status: {'✅ FITS' if total_hours <= 47 else '❌ OVERFLOW by ' + str(total_hours - 47)}")

# 2. Check instructor assignments
print(f"\n2️⃣  INSTRUCTOR ASSIGNMENTS:")
assignments = CourseInstructorAssignment.objects.filter(year=year)
missing = []
for course in courses:
    for section in [1, 2, 3]:
        assignment = assignments.filter(course=course, section_number=section).first()
        if not assignment:
            missing.append(f"   ❌ {course.course_number} Section {section}: NO ASSIGNMENT")

if missing:
    print(f"   Found {len(missing)} missing section assignments:")
    for m in missing[:10]:
        print(m)
    if len(missing) > 10:
        print(f"   ... and {len(missing) - 10} more")
else:
    print(f"   ✅ All {courses.count()} courses × 3 sections have assignments")

# 3. Check lab rooms
print(f"\n3️⃣  LAB ROOM CONFIGURATION:")
lab_courses = courses.filter(course_type='LAB')
for lab in lab_courses:
    rooms = lab.lab_rooms.all()
    print(f"   {lab.course_number}: {rooms.count()} rooms assigned - {[r.lab_name for r in rooms]}")
    if rooms.count() == 0:
        print(f"      ⚠️  WARNING: No lab rooms! Will cause scheduling failures")

# 4. Check theory max_continuous_hours bunching
print(f"\n4️⃣  THEORY COURSE BUNCHING POTENTIAL:")
theory_courses = courses.filter(course_type='THEORY')
for theory in theory_courses:
    if theory.max_continuous_hours > 1:
        print(f"   {theory.course_number}: {theory.hours_per_week} hours, max_continuous={theory.max_continuous_hours}")
        if theory.hours_per_week > theory.max_continuous_hours * 5:  # 5 days without Saturday
            print(f"      ⚠️  IMPOSSIBLE: {theory.hours_per_week} hours cannot fit in 5 days with max {theory.max_continuous_hours} per day!")

# 5. Calculate theoretical minimum conflicts
print(f"\n5️⃣  SCHEDULING DIFFICULTY:")
print(f"   Total classes to schedule: {total_hours * 3} (3 sections)")
print(f"   LAB courses need continuous blocks: {lab_courses.count()} labs × 3 sections = {lab_courses.count() * 3} blocks")
print(f"   THEORY courses to distribute: {theory_courses.count()} × 3 sections × avg 5 hours = {theory_courses.count() * 3 * 5} slots")

# 6. Check for common conflicts
print(f"\n6️⃣  COMMON CONFLICT SOURCES:")
# Check if any instructor assigned to multiple courses
from collections import defaultdict
inst_courses = defaultdict(list)
for assignment in assignments:
    for inst in assignment.instructors.all():
        inst_courses[inst.name].append(f"{assignment.course.course_number} Sec{assignment.section_number}")

overloaded = {name: courses for name, courses in inst_courses.items() if len(courses) > 10}
if overloaded:
    print(f"   ⚠️  Heavily assigned instructors (may cause conflicts):")
    for name, course_list in list(overloaded.items())[:5]:
        print(f"      {name}: {len(course_list)} assignments")
else:
    print(f"   ✅ No instructor overloading detected")

print(f"\n{'='*80}")
print(f"RECOMMENDATIONS:")
print(f"{'='*80}")

if total_hours > 40:
    print("⚠️  1. Total hours per section is very high (38-40 hours)")
    print("     Consider reducing some course hours or using Saturday more")

if missing:
    print("❌ 2. CRITICAL: Missing instructor assignments!")
    print("     All courses must have section-specific instructor assignments")
    print(f"     Missing: {len(missing)} section assignments")

lab_no_rooms = [lab for lab in lab_courses if lab.lab_rooms.count() == 0]
if lab_no_rooms:
    print("❌ 3. CRITICAL: Some labs have no rooms assigned!")
    print(f"     Affected: {[l.course_number for l in lab_no_rooms]}")

print("\n💡 Quick Fix: Reduce MAX_GENERATIONS to 50 and TARGET_FITNESS to 0.40 temporarily")
print("   This will help identify if algorithm can reach even 40% fitness")
