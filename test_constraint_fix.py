"""
Test the constraint scheduler fix for TP courses
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import *
from SchedulerApp.views import ConstraintScheduler, Data
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("=" * 100)
print("TESTING CONSTRAINT SCHEDULER FIX")
print("=" * 100)
print()

# Test with 2nd Year (has TP courses)
year = Year.objects.get(year_name='2nd Year')
print(f"Testing with: {year.year_name}")
print()

# Create data object
data = Data(year)
data.elective_time_tracker = {}

# Build schedule
print("Building schedule...")
scheduler = ConstraintScheduler()

success_count = 0
for attempt in range(1, 11):
    print(f"\nAttempt {attempt}/10...")
    schedule = scheduler.build_schedule(data, year)
    
    if schedule:
        success_count += 1
        fitness = schedule.getFitness()
        conflicts = schedule.getNumbOfConflicts()
        classes = len(schedule.getClasses())
        
        print(f"  ✓ SUCCESS!")
        print(f"    Classes: {classes}")
        print(f"    Fitness: {fitness:.2%}")
        print(f"    Conflicts: {conflicts}")
        
        # Check TP courses
        tp_courses = ['23TP9102', '23TP9103']
        print(f"\n  Checking TP courses:")
        
        from collections import defaultdict
        for course_num in tp_courses:
            # Group by section and day
            grouped = defaultdict(list)
            for cls in schedule.getClasses():
                if cls.course.course_number == course_num:
                    key = (cls.section_number, cls.meeting_time.day)
                    grouped[key].append(cls.meeting_time.time)
            
            if grouped:
                print(f"    {course_num}:")
                for (section, day), times in list(grouped.items())[:3]:
                    if len(times) == 2:
                        print(f"      ✓ Sec{section} {day}: {times} (continuous)")
                    else:
                        print(f"      ⚠ Sec{section} {day}: {times} (NOT continuous)")
        
        break  # Stop after first success
    else:
        print(f"  ✗ Failed to create schedule")

print()
print("=" * 100)
if success_count > 0:
    print("✓ CONSTRAINT SCHEDULER IS WORKING!")
else:
    print("✗ CONSTRAINT SCHEDULER STILL FAILING")
print("=" * 100)
