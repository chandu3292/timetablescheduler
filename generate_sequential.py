#!/usr/bin/env python
"""
SEQUENTIAL TIMETABLE GENERATION
================================
This script generates timetables ONE YEAR AT A TIME in sequence.

Why this works:
- When instructors teach BOTH 2nd and 3rd year, we need to avoid conflicts
- By generating 2nd year FIRST, the scheduler learns which slots are taken
- When generating 3rd year SECOND, it automatically avoids those slots for shared instructors

Order: 1st Year -> 2nd Year -> 3rd Year -> 4th Year
(We do 1st year first since it has no labs, fewer constraints)
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import (
    TimetableEntry, Year, Course, GeneratedTimetable,
    CourseInstructorAssignment, LabBatchAssignment,
    MeetingTime, LabRoom, Instructor
)
from SchedulerApp.views import ConstraintScheduler, Data, Class
import logging
import random
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def print_header(text):
    print("\n" + "=" * 80)
    print(text.center(80))
    print("=" * 80)

def print_subheader(text):
    print("\n" + "-" * 80)
    print(text)
    print("-" * 80)

def generate_year_timetable(year, year_name):
    """Generate timetable for a specific year"""
    print_subheader(f"GENERATING {year_name} TIMETABLE")
    print(f"  DEBUG: Starting generation for {year_name}")
    
    # Get courses for this year
    courses = year.courses.all()
    if not courses.exists():
        print(f"  [SKIP] No courses found for {year_name}")
        return 0
    
    print(f"  DEBUG: Found {courses.count()} courses")
    print(f"  Sections: 3 (fixed)")
    print(f"  Courses: {courses.count()}")
    
    # Create Data object for this year
    data = Data(year)
    data.elective_time_tracker = {}
    
    # Get all available meeting times
    meeting_times = list(MeetingTime.objects.filter(year=year))
    print(f"  Meeting times: {len(meeting_times)}")
    
    # Get lab rooms
    lab_rooms = list(LabRoom.objects.all())
    logger.info(f"  Lab rooms: {len(lab_rooms)}")
    
    # Get instructor assignments for this year
    instructor_assignments = CourseInstructorAssignment.objects.filter(year=year)
    print(f"  Instructor assignments: {instructor_assignments.count()}")
    
    # Get lab batch assignments for this year
    lab_batches = LabBatchAssignment.objects.filter(year=year)
    print(f"  Lab batch assignments: {lab_batches.count()}")
    
    # Pre-allocate elective times (to ensure all sections use same slots)
    elective_courses = courses.filter(course_type='ELECTIVE')
    print(f"  Pre-allocating times for {elective_courses.count()} elective courses...")
    
    if meeting_times and elective_courses.exists():
        from SchedulerApp.views import TIME_SLOTS
        
        for course in elective_courses:
            total_hours = course.hours_per_week
            continuous_hours = course.max_continuous_hours if course.max_continuous_hours > 1 else 0
            single_hours = total_hours - continuous_hours
            
            # Track times used for continuous blocks to avoid overlap
            used_times = []
            
            # FIRST: Allocate continuous block(s) if needed
            if continuous_hours > 0:
                day_groups = {}
                for mt in meeting_times:
                    day_groups.setdefault(mt.day, []).append(mt)
                
                for day in day_groups:
                    day_groups[day].sort(key=lambda x: TIME_SLOTS.index((x.time, x.time)) if (x.time, x.time) in TIME_SLOTS else 999)
                
                valid_blocks = []
                for day, times in day_groups.items():
                    for i in range(len(times) - course.max_continuous_hours + 1):
                        block = times[i:i + course.max_continuous_hours]
                        if not any(t.time == "12:15 - 1:05" for t in block):
                            valid_blocks.append(block)
                
                if valid_blocks:
                    block_key = f"{course.course_number}_continuous"
                    selected_block = random.choice(valid_blocks)
                    data.elective_time_tracker[block_key] = selected_block
                    # Track these times as used
                    used_times.extend(selected_block)
            
            # SECOND: Allocate single periods from REMAINING times (exclude continuous block times)
            if single_hours > 0:
                available_times = [mt for mt in meeting_times if mt not in used_times]
                if len(available_times) >= single_hours:
                    single_key = f"{course.course_number}_single"
                    selected_times = random.sample(available_times, single_hours)
                    data.elective_time_tracker[single_key] = selected_times
                    
                    index_key = f"{course.course_number}_single_index"
                    data.elective_time_tracker[index_key] = {}
    
    # Create scheduler instance
    scheduler = ConstraintScheduler()
    
    # Attempt to generate timetable (with retries)
    max_attempts = 5
    print(f"  DEBUG: Starting generation attempts...")
    for attempt in range(1, max_attempts + 1):
        print(f"\n  Attempt {attempt}/{max_attempts}...")
        
        schedule = scheduler.build_schedule(data, year)
        print(f"  DEBUG: build_schedule returned: schedule={'None' if schedule is None else 'object with ' + str(len(schedule._classes)) + ' classes'}")
        
        if schedule and len(schedule._classes) > 0:
            # Create GeneratedTimetable entry
            gen_timetable = GeneratedTimetable.objects.create(
                year=year,
                fitness_score=1.0,
                generation_count=attempt,
                generated_at=datetime.now()
            )
            
            # Save all classes as TimetableEntry objects
            saved_count = 0
            for cls in schedule._classes:
                TimetableEntry.objects.create(
                    timetable=gen_timetable,
                    year=cls.year,
                    section_number=cls.section_number,
                    course=cls.course,
                    instructor=cls.instructor,
                    lab_room=cls.room,
                    meeting_time=cls.meeting_time,
                    batch=cls.batch
                )
                saved_count += 1
            
            print(f"  [OK] SUCCESS! Generated and saved {saved_count} classes")
            return saved_count
        else:
            print(f"  [X] Attempt {attempt} failed to build schedule")
            if schedule:
                print(f"      Schedule exists but has {len(schedule._classes)} classes")
            else:
                print(f"      Schedule returned None")
            if attempt < max_attempts:
                print(f"  Retrying...")
    
    print(f"  [X] FAILED after {max_attempts} attempts")
    return 0

def check_conflicts():
    """Check for any conflicts in the generated timetables"""
    print_subheader("CHECKING FOR CONFLICTS")
    
    all_entries = TimetableEntry.objects.all()
    
    if not all_entries.exists():
        logger.warning("  No timetable entries found!")
        return
    
    # Group by year for counting
    from collections import defaultdict
    year_counts = defaultdict(int)
    for entry in all_entries:
        year_counts[entry.year.year_name] += 1
    
    logger.info(f"\n  Total entries: {all_entries.count()}")
    for year_name, count in sorted(year_counts.items()):
        logger.info(f"    {year_name}: {count} classes")
    
    # Check for room conflicts
    room_conflicts = 0
    instructor_conflicts = 0
    section_conflicts = 0
    
    # Room conflicts: Same room, same time, but DIFFERENT course/section
    for entry1 in all_entries:
        if entry1.lab_room:  # Only check lab rooms
            conflicts_with = all_entries.filter(
                meeting_time=entry1.meeting_time,
                lab_room=entry1.lab_room
            ).exclude(id=entry1.id)
            
            # Filter out co-teaching entries (same course, section, year, time, room, different instructor)
            real_conflicts = conflicts_with.exclude(
                course=entry1.course,
                section_number=entry1.section_number,
                year=entry1.year
            )
            
            if real_conflicts.exists():
                room_conflicts += 1
    
    # Instructor conflicts: Same instructor teaching different courses at same time
    for entry1 in all_entries:
        if entry1.instructor:
            # Find other entries at same time with same instructor
            conflicts_with = all_entries.filter(
                meeting_time=entry1.meeting_time,
                instructor=entry1.instructor
            ).exclude(id=entry1.id)
            
            # Filter out co-teaching entries (same course, section, year)
            real_conflicts = conflicts_with.exclude(
                course=entry1.course,
                section_number=entry1.section_number,
                year=entry1.year
            )
            
            if real_conflicts.exists():
                for entry2 in real_conflicts:
                    instructor_conflicts += 1
                    logger.warning(
                        f"  INSTRUCTOR CONFLICT: {entry1.instructor.uid} teaching both "
                        f"{entry1.year.year_name} {entry1.course.course_name} Sec{entry1.section_number} "
                        f"AND {entry2.year.year_name} {entry2.course.course_name} Sec{entry2.section_number} "
                        f"at {entry1.meeting_time}"
                    )
                break  # Only report once per entry1
    
    # Check for section conflicts: Same section taking multiple different courses at same time
    for entry1 in all_entries:
        conflicts_with = all_entries.filter(
            meeting_time=entry1.meeting_time,
            section_number=entry1.section_number,
            year=entry1.year
        ).exclude(id=entry1.id)
        
        # Filter out co-teaching entries (same course, different instructor)
        real_conflicts = conflicts_with.exclude(course=entry1.course)
        
        if real_conflicts.exists():
            section_conflicts += 1
    
    print("\n  CONFLICT SUMMARY:")
    print(f"    Room conflicts: {room_conflicts}")
    print(f"    Instructor conflicts: {instructor_conflicts}")
    print(f"    Section conflicts: {section_conflicts}")
    
    if room_conflicts == 0 and instructor_conflicts == 0 and section_conflicts == 0:
        logger.info("\n  [OK] NO CONFLICTS FOUND!")
    else:
        logger.error("\n  [X] CONFLICTS DETECTED!")

def main():
    print_header("SEQUENTIAL TIMETABLE GENERATION")
    
    print("""
This script generates timetables one year at a time to avoid instructor conflicts.

Generation order:
  1. 1st Year (fewest constraints - no labs)
  2. 2nd Year (has labs, many shared instructors)
  3. 3rd Year (has labs, shares instructors with 2nd year)
  4. 4th Year (if exists)

By generating sequentially, when an instructor is already scheduled for 2nd year,
the 3rd year scheduler will automatically avoid those time slots.
    """)
    
    # Step 1: Clear all existing timetables
    print_subheader("STEP 1: CLEARING EXISTING TIMETABLES")
    entry_count = TimetableEntry.objects.all().count()
    gen_count = GeneratedTimetable.objects.all().count()
    
    # Delete in correct order (entries first, then parent)
    TimetableEntry.objects.all().delete()
    GeneratedTimetable.objects.all().delete()
    
    logger.info(f"  Deleted {entry_count} timetable entries")
    logger.info(f"  Deleted {gen_count} generated timetable records")
    
    # Step 2: Get all years and sort them
    years = Year.objects.all().order_by('id')
    
    if not years.exists():
        logger.error("  ERROR: No years found in database!")
        return
    
    logger.info(f"  Found {years.count()} years")
    
    # Map year names to generation order
    year_order = {
        '1': 1,  # 1st year first
        '2': 2,  # 2nd year second
        '3': 3,  # 3rd year third
        '4': 4   # 4th year last
    }
    
    # Sort years by custom order
    sorted_years = sorted(years, key=lambda y: year_order.get(
        y.year_name.split()[0] if ' ' in y.year_name else y.year_name[:1],
        99
    ))
    
    # Step 3: Generate each year sequentially
    print_subheader("STEP 2: SEQUENTIAL GENERATION")
    
    total_generated = 0
    for year in sorted_years:
        count = generate_year_timetable(year, year.year_name)
        total_generated += count
    
    # Step 4: Check for conflicts
    print_subheader("STEP 3: FINAL VERIFICATION")
    logger.info(f"\n  Total classes generated: {total_generated}")
    
    check_conflicts()
    
    print_header("GENERATION COMPLETE")
    print(f"\n  Total classes generated: {total_generated}")
    print("\n  You can now view the timetables in the web interface!")
    print("  The timetables should have NO instructor conflicts.")
    print()

if __name__ == '__main__':
    main()
