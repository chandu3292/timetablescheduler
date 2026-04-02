#!/usr/bin/env python
"""
Comprehensive 3rd Year Timetable Regeneration Script
- Deletes all existing 3rd Year entries
- Creates fresh GeneratedTimetable record
- Regenerates timetable using constraint scheduler
- Reports detailed results including OE course analysis
"""

import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import (
    Year, GeneratedTimetable, TimetableEntry, Course, 
    CourseInstructorAssignment, LabBatchAssignment, MeetingTime, LabRoom
)
from SchedulerApp.views import Data, ConstraintScheduler, MAX_ATTEMPTS
from datetime import datetime
import traceback

print("=" * 100)
print("3RD YEAR TIMETABLE REGENERATION - COMPLETE CLEAN SLATE")
print("=" * 100)
print(f"Start Time: {datetime.now()}\n")

# ============================================================================
# STEP 1: Get 3rd Year Object
# ============================================================================
print("\n[STEP 1] Getting 3rd Year Object...")
try:
    year_3rd = Year.objects.get(year_name='3rd Year')
    print(f"✓ Found: {year_3rd} (ID: {year_3rd.id})")
except Year.DoesNotExist:
    print("✗ ERROR: 3rd Year not found in database")
    sys.exit(1)

# ============================================================================
# STEP 2: Delete All Existing 3rd Year Entries
# ============================================================================
print("\n[STEP 2] Deleting all existing 3rd Year timetable data...")

# Get existing GeneratedTimetable
existing_gen = GeneratedTimetable.objects.filter(year=year_3rd).first()
if existing_gen:
    entry_count_before = TimetableEntry.objects.filter(timetable=existing_gen).count()
    print(f"  - Found existing GeneratedTimetable (ID: {existing_gen.id})")
    print(f"  - Existing entries: {entry_count_before}")
    
    # Delete entries
    TimetableEntry.objects.filter(timetable=existing_gen).delete()
    print(f"  - ✓ Deleted all {entry_count_before} timetable entries")
    
    # Delete GeneratedTimetable record
    existing_gen.delete()
    print(f"  - ✓ Deleted GeneratedTimetable record")
else:
    print("  - No existing GeneratedTimetable found")

# Verify deletion
verify_entries = TimetableEntry.objects.filter(year=year_3rd).count()
verify_gen = GeneratedTimetable.objects.filter(year=year_3rd).exists()
print(f"  - Verification: {verify_entries} entries remaining, GeneratedTimetable exists: {verify_gen}")

# ============================================================================
# STEP 3: Create New GeneratedTimetable
# ============================================================================
print("\n[STEP 3] Creating new GeneratedTimetable record...")
new_gen_timetable = GeneratedTimetable.objects.create(
    year=year_3rd,
    fitness_score=0.0,
    generation_count=0
)
print(f"✓ Created GeneratedTimetable (ID: {new_gen_timetable.id})")

# ============================================================================
# STEP 4: Prepare Data and Run Scheduler
# ============================================================================
print("\n[STEP 4] Preparing scheduler data...")

# Get courses for 3rd year
courses = year_3rd.courses.all()
print(f"  - Total courses for 3rd Year: {courses.count()}")

# Create Data object
data = Data(year_3rd)
data.elective_time_tracker = {}
print(f"  - ✓ Data object created")

# ============================================================================
# STEP 5: Execute Scheduler with Retries
# ============================================================================
print("\n[STEP 5] Running ConstraintScheduler...")
print(f"  - MAX_ATTEMPTS: {MAX_ATTEMPTS}")

scheduler = ConstraintScheduler()
schedule = None
used_attempt = 0

for attempt in range(1, MAX_ATTEMPTS + 1):
    print(f"  - Attempt {attempt}...", end=" ")
    try:
        schedule = scheduler.build_schedule(data, year_3rd)
        if schedule:
            used_attempt = attempt
            print("✓ SUCCESS")
            break
        else:
            print("Failed (returned None)")
    except Exception as e:
        print(f"Failed (Exception: {str(e)[:50]})")
        traceback.print_exc()

if not schedule:
    print("\n✗ ERROR: Scheduler failed to generate timetable")
    sys.exit(1)

print(f"\n✓ Schedule generated successfully on attempt {used_attempt}")

# ============================================================================
# STEP 6: Calculate Metrics and Save to Database
# ============================================================================
print("\n[STEP 6] Calculating metrics and saving to database...")

classes = list(schedule.getClasses())
conflicts = schedule.getNumbOfConflicts()
fitness = schedule.getFitness()

print(f"  - Total classes scheduled: {len(classes)}")
print(f"  - Conflicts: {conflicts}")
print(f"  - Fitness Score: {fitness:.4f} ({fitness*100:.2f}%)")

# Update GeneratedTimetable with metrics
new_gen_timetable.fitness_score = fitness
new_gen_timetable.generation_count = used_attempt
new_gen_timetable.save()
print(f"  - ✓ Updated GeneratedTimetable with metrics")

# Save all timetable entries
print(f"\n[STEP 7] Saving timetable entries to database...")

entry_count = 0
failed_entries = 0
entry_by_section = {1: 0, 2: 0, 3: 0}
oe_entries = []

for cls in classes:
    try:
        # Handle LAB courses with batch splitting
        if cls.course.split_into_batches and cls.batch != 'FULL':
            batch_assignment = LabBatchAssignment.objects.filter(
                year=year_3rd,
                section_number=cls.section_number,
                course=cls.course,
                batch=cls.batch
            ).first()
            
            if batch_assignment and batch_assignment.instructors.exists():
                for instructor in batch_assignment.instructors.all():
                    entry, created = TimetableEntry.objects.get_or_create(
                        timetable=new_gen_timetable,
                        year=year_3rd,
                        section_number=cls.section_number,
                        course=cls.course,
                        instructor=instructor,
                        lab_room=cls.room if hasattr(cls, 'room') else None,
                        meeting_time=cls.meeting_time,
                        batch=cls.batch,
                        defaults={'is_evaluator': False}
                    )
                    entry_count += 1
                    entry_by_section[cls.section_number] += 1
                    
                    # Track OE course
                    if cls.course.course_number == '23IT6121':
                        oe_entries.append({
                            'section': cls.section_number,
                            'batch': cls.batch,
                            'instructor': instructor.name,
                            'day': cls.meeting_time.day,
                            'time': cls.meeting_time.time
                        })
            else:
                entry, created = TimetableEntry.objects.get_or_create(
                    timetable=new_gen_timetable,
                    year=year_3rd,
                    section_number=cls.section_number,
                    course=cls.course,
                    instructor=cls.instructor,
                    lab_room=cls.room if hasattr(cls, 'room') else None,
                    meeting_time=cls.meeting_time,
                    batch=cls.batch,
                    defaults={'is_evaluator': False}
                )
                entry_count += 1
                entry_by_section[cls.section_number] += 1
        
        # Handle LAB courses with multiple instructors (non-split)
        elif cls.course.course_type == 'LAB':
            entry, created = TimetableEntry.objects.update_or_create(
                timetable=new_gen_timetable,
                year=year_3rd,
                section_number=cls.section_number,
                course=cls.course,
                instructor=cls.instructor,
                meeting_time=cls.meeting_time,
                batch=cls.batch,
                defaults={
                    'is_evaluator': getattr(cls, 'is_evaluator', False),
                    'lab_room': cls.room if hasattr(cls, 'room') else None
                }
            )
            entry_count += 1
            entry_by_section[cls.section_number] += 1
            
            # Track OE course
            if cls.course.course_number == '23IT6121':
                oe_entries.append({
                    'section': cls.section_number,
                    'batch': cls.batch,
                    'instructor': cls.instructor.name if cls.instructor else 'N/A',
                    'day': cls.meeting_time.day,
                    'time': cls.meeting_time.time
                })
        
        # Handle THEORY and ELECTIVE courses
        else:
            entry, created = TimetableEntry.objects.get_or_create(
                timetable=new_gen_timetable,
                year=year_3rd,
                section_number=cls.section_number,
                course=cls.course,
                instructor=cls.instructor,
                meeting_time=cls.meeting_time,
                batch=cls.batch,
                defaults={'is_evaluator': False}
            )
            entry_count += 1
            entry_by_section[cls.section_number] += 1
            
            # Track OE course
            if cls.course.course_number == '23IT6121':
                oe_entries.append({
                    'section': cls.section_number,
                    'batch': cls.batch,
                    'instructor': cls.instructor.name if cls.instructor else 'N/A',
                    'day': cls.meeting_time.day,
                    'time': cls.meeting_time.time
                })
    
    except Exception as e:
        failed_entries += 1
        print(f"  ✗ Failed to save entry for {cls.course.course_number} Section {cls.section_number}: {e}")

print(f"  - ✓ Entries saved: {entry_count}")
print(f"  - Entries per section: Sec1={entry_by_section[1]}, Sec2={entry_by_section[2]}, Sec3={entry_by_section[3]}")
if failed_entries > 0:
    print(f"  - ✗ Failed entries: {failed_entries}")

# ============================================================================
# STEP 8: Verify Database
# ============================================================================
print("\n[STEP 8] Verifying saved data...")

total_saved = TimetableEntry.objects.filter(timetable=new_gen_timetable).count()
print(f"  - Total entries in database: {total_saved}")

# Count by course type
theory_count = TimetableEntry.objects.filter(
    timetable=new_gen_timetable,
    course__course_type='THEORY'
).count()
lab_count = TimetableEntry.objects.filter(
    timetable=new_gen_timetable,
    course__course_type='LAB'
).count()
elective_count = TimetableEntry.objects.filter(
    timetable=new_gen_timetable,
    course__course_type='ELECTIVE'
).count()

print(f"  - THEORY: {theory_count}, LAB: {lab_count}, ELECTIVE: {elective_count}")

# ============================================================================
# STEP 9: OE Course Analysis (23IT6121)
# ============================================================================
print("\n[STEP 9] OE Course Analysis (23IT6121)...")

oe_course = Course.objects.filter(course_number='23IT6121').first()
if oe_course:
    oe_entries_db = TimetableEntry.objects.filter(
        timetable=new_gen_timetable,
        course=oe_course
    )
    total_oe = oe_entries_db.count()
    print(f"  - Total OE entries scheduled: {total_oe}")
    print(f"  - OE required: 4 hours/week per section (4 entries)")
    
    # Group by section
    oe_by_section = {}
    for entry in oe_entries_db:
        if entry.section_number not in oe_by_section:
            oe_by_section[entry.section_number] = []
        oe_by_section[entry.section_number].append(entry)
    
    print(f"\n  OE Schedule Breakdown:")
    for section_num in sorted(oe_by_section.keys()):
        entries = oe_by_section[section_num]
        count = len(entries)
        status = "✓ COMPLETE" if count == 4 else f"✗ INCOMPLETE ({count}/4)"
        print(f"    Section {section_num}: {count} hours {status}")
        
        for entry in entries:
            print(f"      - {entry.meeting_time.day:9} {entry.meeting_time.time:15} | Instructor: {entry.instructor.name if entry.instructor else 'N/A'}")
    
    # Overall OE status
    print(f"\n  OE Overall Status:")
    sec1_oe = len(oe_by_section.get(1, []))
    sec2_oe = len(oe_by_section.get(2, []))
    sec3_oe = len(oe_by_section.get(3, []))
    
    all_complete = (sec1_oe == 4) and (sec2_oe == 4) and (sec3_oe == 4)
    if all_complete:
        print(f"    ✓ ALL SECTIONS COMPLETE - Each section has 4 hours/week of OE")
    else:
        print(f"    ✗ INCOMPLETE - Some sections missing OE hours")
        if sec1_oe < 4:
            print(f"      - Section 1: Missing {4 - sec1_oe} hours")
        if sec2_oe < 4:
            print(f"      - Section 2: Missing {4 - sec2_oe} hours")
        if sec3_oe < 4:
            print(f"      - Section 3: Missing {4 - sec3_oe} hours")
else:
    print("  ✗ OE Course (23IT6121) not found in database")

# ============================================================================
# STEP 10: Check for Gaps and Issues
# ============================================================================
print("\n[STEP 10] Gap Analysis...")

# Get all courses for 3rd year
all_courses = year_3rd.courses.all().order_by('course_number')
gap_status = {}
gap_count = 0

for course in all_courses:
    for section in [1, 2, 3]:
        section_entries = TimetableEntry.objects.filter(
            timetable=new_gen_timetable,
            course=course,
            section_number=section
        ).count()
        
        # Determine expected count
        if course.course_type == 'LAB':
            if course.split_into_batches:
                # Split labs: each batch should have 1 entry per section
                expected = 1  # One entry per section (batch handled separately)
            else:
                # Non-split labs: 1 entry per instructor
                expected = 1  # Simplified for now
        else:
            # Theory/Elective: should have course.hours_per_week entries
            expected = course.hours_per_week
        
        key = f"{course.course_number}_Sec{section}"
        if section_entries < expected:
            gap_status[key] = {
                'course': course.course_number,
                'section': section,
                'expected': expected,
                'actual': section_entries,
                'gap': expected - section_entries,
                'course_type': course.course_type
            }
            gap_count += 1

if gap_count > 0:
    print(f"  Found {gap_count} potential gaps:")
    for key, info in sorted(gap_status.items()):
        print(f"    - {info['course']} Section {info['section']}: {info['actual']}/{info['expected']} ({info['gap']} missing)")
else:
    print(f"  ✓ No gaps detected - all courses appear to have required hours scheduled")

# ============================================================================
# STEP 11: Summary Report
# ============================================================================
print("\n" + "=" * 100)
print("REGENERATION SUMMARY REPORT")
print("=" * 100)

print(f"\n✓ GENERATION SUCCESSFUL")
print(f"  - Attempts used: {used_attempt}/{MAX_ATTEMPTS}")
print(f"  - Total entries created: {total_saved}")
print(f"  - Fitness score: {fitness*100:.2f}%")
print(f"  - Conflicts: {conflicts}")

print(f"\n✓ COURSE DISTRIBUTION")
print(f"  - THEORY courses: {theory_count} entries")
print(f"  - LAB courses: {lab_count} entries")
print(f"  - ELECTIVE courses: {elective_count} entries")

print(f"\n✓ SECTION DISTRIBUTION")
print(f"  - Section 1: {entry_by_section[1]} entries")
print(f"  - Section 2: {entry_by_section[2]} entries")
print(f"  - Section 3: {entry_by_section[3]} entries")

if total_oe == 12:  # 4 per section
    print(f"\n✓ OE COURSE (23IT6121) - COMPLETE")
    print(f"  - Total: {total_oe} entries (4 per section)")
    print(f"  - All sections have 4 hours/week")
elif total_oe > 0:
    print(f"\n⚠ OE COURSE (23IT6121) - PARTIAL")
    print(f"  - Total: {total_oe} entries (expected 12)")
    print(f"  - Some sections missing hours")
else:
    print(f"\n✗ OE COURSE (23IT6121) - MISSING")
    print(f"  - No entries scheduled")

print(f"\n✓ GENERATION COMPLETED AT: {datetime.now()}")
print("=" * 100)
