"""
Test generation with co-teaching fix
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')

import django
django.setup()

from SchedulerApp.models import Year, TimetableEntry
from SchedulerApp.views import ConstraintScheduler, Data
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

print("\n=== TESTING 3RD YEAR GENERATION ===\n")

year_3 = Year.objects.get(year_name__icontains='3')
print(f"Year: {year_3.year_name}")

# Create Data object
data = Data(year_3)
data.elective_time_tracker = {}

print(f"Sections: 3")
print(f"Courses: {year_3.courses.count()}")

# Pre-allocate elective times (simplified version from generate_sequential.py)
from SchedulerApp.models import MeetingTime, Course
import random

elective_courses = year_3.courses.filter(course_type='ELECTIVE')
meeting_times = list(MeetingTime.objects.filter(year=year_3))

if elective_courses.exists() and meeting_times:
    print(f"\nPre-allocating elective times for {elective_courses.count()} courses...")
    
    for course in elective_courses:
        total_hours = course.hours_per_week
        continuous_hours = course.max_continuous_hours if course.max_continuous_hours > 1 else 0
        single_hours = total_hours - continuous_hours
        
        if single_hours > 0:
            single_key = f"{course.course_number}_single"
            selected_times = random.sample(meeting_times, min(single_hours, len(meeting_times)))
            data.elective_time_tracker[single_key] = selected_times
            
            index_key = f"{course.course_number}_single_index"
            data.elective_time_tracker[index_key] = {}

# Create scheduler and attempt to build schedule
scheduler = ConstraintScheduler()
print("\nAttempting to build schedule...")

schedule = scheduler.build_schedule(data, year_3)

if schedule:
    print(f"\n✓ SUCCESS! Generated {len(schedule._classes)} classes")
    
    # Show breakdown
    from collections import Counter
    course_counts = Counter([cls.course.course_number for cls in schedule._classes])
    print("\nClasses by course:")
    for course_num, count in sorted(course_counts.items()):
        print(f"  {course_num}: {count} entries")
else:
    print("\n✗ FAILED - build_schedule returned None")
    print("\nThis indicates one or more courses couldn't be scheduled.")
    print("Check scheduler.log for detailed error messages.")
