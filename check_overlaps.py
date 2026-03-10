import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry
from collections import defaultdict

print("="*80)
print("COMPREHENSIVE OVERLAP CHECK")
print("="*80)
print()

# Get all entries
all_entries = TimetableEntry.objects.all().select_related('instructor', 'meeting_time', 'year', 'course', 'lab_room')

print(f"Total timetable entries: {all_entries.count()}")
print()

# 1. CHECK INSTRUCTOR OVERLAPS (Faculty teaching 2 classes at same time)
print("="*80)
print("1. INSTRUCTOR OVERLAP CHECK")
print("="*80)
print()

instructor_schedule = defaultdict(list)

for entry in all_entries:
    if entry.instructor and entry.meeting_time:
        # Use day and time as key (simpler than using IDs)
        key = (entry.instructor.uid, entry.meeting_time.day, entry.meeting_time.time)
        instructor_schedule[key].append(entry)

instructor_conflicts = []
for (instructor_uid, day, time), entries in instructor_schedule.items():
    if len(entries) > 1:
        # Filter out co-teaching (same course, same section, same year)
        unique_classes = {}
        for entry in entries:
            class_key = (entry.course.course_number, entry.section_number, entry.year.id, entry.batch)
            if class_key not in unique_classes:
                unique_classes[class_key] = entry
        
        # If still more than 1 unique class, it's a conflict
        if len(unique_classes) > 1:
            instructor_conflicts.append((entries[0].instructor, day, time, list(unique_classes.values())))

if instructor_conflicts:
    print(f"❌ FOUND {len(instructor_conflicts)} INSTRUCTOR OVERLAPS:")
    print()
    for i, (instructor, day, time, entries) in enumerate(instructor_conflicts, 1):
        print(f"Conflict #{i}: {instructor.name}")
        print(f"  Time: {day} {time}")
        for entry in entries:
            print(f"    - {entry.year.year_name} {entry.course.course_name} Sec{entry.section_number} Batch:{entry.batch}")
            if entry.lab_room:
                print(f"      Room: {entry.lab_room.lab_name}")
        print()
else:
    print("✅ NO INSTRUCTOR OVERLAPS - All instructors teach only one class at a time")
    print()

# 2. CHECK LAB ROOM OVERLAPS (Same lab room used twice at same time)
print("="*80)
print("2. LAB ROOM OVERLAP CHECK")
print("="*80)
print()

lab_schedule = defaultdict(list)

for entry in all_entries:
    if entry.lab_room and entry.meeting_time:
        key = (entry.lab_room.lab_name, entry.meeting_time.day, entry.meeting_time.time)
        lab_schedule[key].append(entry)

lab_conflicts = []
for (room_name, day, time), entries in lab_schedule.items():
    if len(entries) > 1:
        # Filter out co-teaching (same course, same section, same year)
        unique_classes = {}
        for entry in entries:
            class_key = (entry.course.course_number, entry.section_number, entry.year.id, entry.batch)
            if class_key not in unique_classes:
                unique_classes[class_key] = entry
        
        # If still more than 1 unique class, it's a conflict
        if len(unique_classes) > 1:
            lab_conflicts.append((room_name, day, time, list(unique_classes.values())))

if lab_conflicts:
    print(f"❌ FOUND {len(lab_conflicts)} LAB ROOM OVERLAPS:")
    print()
    for i, (room_name, day, time, entries) in enumerate(lab_conflicts, 1):
        print(f"Conflict #{i}: {room_name}")
        print(f"  Time: {day} {time}")
        for entry in entries:
            instructors = "Multiple instructors" if entry.batch != 'FULL' else entry.instructor.name if entry.instructor else "No instructor"
            print(f"    - {entry.year.year_name} {entry.course.course_name} Sec{entry.section_number} Batch:{entry.batch}")
            print(f"      Instructor: {instructors}")
        print()
else:
    print("✅ NO LAB ROOM OVERLAPS - Each lab room used by only one class at a time")
    print()

# 3. CHECK SECTION OVERLAPS (Same section having 2 classes at same time)
print("="*80)
print("3. SECTION OVERLAP CHECK")
print("="*80)
print()

section_schedule = defaultdict(list)

for entry in all_entries:
    if entry.meeting_time:
        key = (entry.year.year_name, entry.section_number, entry.batch, entry.meeting_time.day, entry.meeting_time.time)
        section_schedule[key].append(entry)

section_conflicts = []
for (year_name, section_num, batch, day, time), entries in section_schedule.items():
    if len(entries) > 1:
        # Filter out co-teaching (same course)
        unique_courses = {}
        for entry in entries:
            course_key = entry.course.course_number
            if course_key not in unique_courses:
                unique_courses[course_key] = entry
        
        # If still more than 1 unique course, it's a conflict
        if len(unique_courses) > 1:
            section_conflicts.append((year_name, section_num, batch, day, time, list(unique_courses.values())))

if section_conflicts:
    print(f"❌ FOUND {len(section_conflicts)} SECTION OVERLAPS:")
    print()
    for i, (year_name, section_num, batch, day, time, entries) in enumerate(section_conflicts, 1):
        print(f"Conflict #{i}: {year_name} Section {section_num} Batch:{batch}")
        print(f"  Time: {day} {time}")
        for entry in entries:
            instructor = entry.instructor.name if entry.instructor else "No instructor"
            room = entry.lab_room.lab_name if entry.lab_room else "Classroom"
            print(f"    - {entry.course.course_name} ({instructor}, {room})")
        print()
else:
    print("✅ NO SECTION OVERLAPS - Each section/batch has only one class at a time")
    print()

# 4. SUMMARY
print("="*80)
print("SUMMARY")
print("="*80)
print(f"Instructor overlaps: {len(instructor_conflicts)}")
print(f"Lab room overlaps: {len(lab_conflicts)}")
print(f"Section overlaps: {len(section_conflicts)}")
print()

if instructor_conflicts == 0 and lab_conflicts == 0 and section_conflicts == 0:
    print("✅ ✅ ✅ ALL CHECKS PASSED - NO OVERLAPS FOUND!")
else:
    print("❌ OVERLAPS DETECTED - See details above")
print()
