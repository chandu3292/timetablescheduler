"""
Regenerate timetables with TP course continuous scheduling fix
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import *
from SchedulerApp.views import ConstraintScheduler, Data, Schedule
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("=" * 100)
print("REGENERATING TIMETABLES WITH TP COURSE FIX")
print("=" * 100)
print()

# TP courses configuration check
tp_courses = ['23TP9102', '23TP9103', '23TP9104', '23TP09104', '23TP19104']
print("TP Courses Configuration:")
print("-" * 100)
for course_num in tp_courses:
    try:
        course = Course.objects.get(course_number=course_num)
        print(f"{course_num}: {course.course_name}")
        print(f"  Type: {course.course_type} | Hours/week: {course.hours_per_week} | Max continuous: {course.max_continuous_hours}")
        if course.course_type != 'THEORY':
            print(f"  ⚠ WARNING: Should be THEORY, not {course.course_type}")
        if course.max_continuous_hours != 2:
            print(f"  ⚠ WARNING: Should have max_continuous_hours=2, not {course.max_continuous_hours}")
        if course.hours_per_week != 2:
            print(f"  ⚠ WARNING: Should have hours_per_week=2, not {course.hours_per_week}")
    except Course.DoesNotExist:
        print(f"{course_num}: ⚠ DOES NOT EXIST")
print()

# Get all years
years = Year.objects.all().order_by('year_name')
print(f"Found {years.count()} years to regenerate:")
for year in years:
    print(f"  - {year.year_name}")
print()

# Regenerate for each year
for year in years:
    print("=" * 100)
    print(f"REGENERATING: {year.year_name}")
    print("=" * 100)
    
    # Delete existing timetable
    existing_tt = GeneratedTimetable.objects.filter(year=year)
    if existing_tt.exists():
        print(f"  Deleting existing timetable...")
        existing_tt.delete()
    
    # Create data object
    print(f"  Creating data object...")
    data = Data(year)
    data.elective_time_tracker = {}
    
    # Build schedule using constraint-based scheduler
    print(f"  Building schedule...")
    scheduler = ConstraintScheduler()
    best_schedule = None
    
    max_attempts = 10
    for attempt in range(1, max_attempts + 1):
        print(f"    Attempt {attempt}/{max_attempts}...")
        schedule = scheduler.build_schedule(data, year)
        
        if schedule:
            fitness = schedule.getFitness()
            conflicts = schedule.getNumbOfConflicts()
            print(f"      Fitness: {fitness:.2%}, Conflicts: {conflicts}")
            
            if fitness >= 0.95 or conflicts == 0:
                best_schedule = schedule
                print(f"    [OK] Acceptable schedule found!")
                break
            
            if best_schedule is None or fitness > best_schedule.getFitness():
                best_schedule = schedule
    
    if not best_schedule:
        print(f"  [FAIL] Failed to generate timetable after {max_attempts} attempts")
        continue
    
    best_fitness = best_schedule.getFitness()
    print(f"  Final fitness: {best_fitness:.2%}")
    print(f"  Conflicts: {best_schedule.getNumbOfConflicts()}")
    
    # Save to database
    print(f"  Saving to database...")
    gen_tt = GeneratedTimetable.objects.create(
        year=year,
        fitness_score=best_fitness,
        generation_count=0
    )
    
    # Save all classes as TimetableEntry
    for cls in best_schedule.getClasses():
        TimetableEntry.objects.create(
            timetable=gen_tt,
            year=cls.year,
            section_number=cls.section_number,
            course=cls.course,
            instructor=cls.instructor,
            lab_room=cls.room,
            meeting_time=cls.meeting_time,
            batch=cls.batch
        )
    
    print(f"  [OK] Saved {len(best_schedule.getClasses())} timetable entries")
    print()

print("=" * 100)
print("VERIFICATION: Checking TP courses in new timetables")
print("=" * 100)
print()

from collections import defaultdict

for course_num in tp_courses:
    if not Course.objects.filter(course_number=course_num).exists():
        continue
    
    entries = TimetableEntry.objects.filter(course__course_number=course_num).select_related('year', 'meeting_time', 'lab_room')
    
    if not entries.exists():
        print(f"{course_num}: Not scheduled")
        continue
    
    course = entries.first().course
    print(f"{course_num} - {course.course_name}")
    
    # Group by year, section, day
    grouped = defaultdict(list)
    for e in entries:
        key = (e.year.year_name, e.section_number, e.meeting_time.day)
        grouped[key].append(e.meeting_time.time)
    
    all_continuous = True
    for (year_name, section, day), times in grouped.items():
        if len(times) == 2:
            print(f"  ✓ {year_name} Sec{section} | {day} | {times} | 2 continuous hours | Lab: {entries.filter(year__year_name=year_name, section_number=section, meeting_time__day=day).first().lab_room or 'None'}")
        elif len(times) == 1:
            # Check if this is the only entry for this section
            section_entries = [k for k in grouped.keys() if k[0] == year_name and k[1] == section]
            if len(section_entries) > 1:
                print(f"  ✗ {year_name} Sec{section} | {day} | {times} | Only 1 hour (NOT continuous)")
                all_continuous = False
        else:
            print(f"  ⚠ {year_name} Sec{section} | {day} | {times} | Unexpected {len(times)} hours")
            all_continuous = False
    
    if all_continuous:
        print(f"  ✅ ALL SECTIONS HAVE CONTINUOUS SCHEDULING")
    else:
        print(f"  ❌ SOME SECTIONS NOT CONTINUOUS")
    print()

print("=" * 100)
print("REGENERATION COMPLETE!")
print("=" * 100)
