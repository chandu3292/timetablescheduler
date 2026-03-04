import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import *
from SchedulerApp.views import Data, Schedule

# Get year 2 (ID 12 - "2nd Year") - has IT219/IT220
year = Year.objects.get(pk=12)
sections = [1, 2, 3]  # Fixed 3 sections per year

print(f"\n{'='*60}")
print(f"CONTINUOUS BLOCK SCHEDULING TEST")
print(f"{'='*60}\n")

# Create a test schedule
import SchedulerApp.views as views_module
views_module.data = Data(year)  # Set global data
schedule = views_module.Schedule()
schedule.initialize()

print(f"\nScheduled {len(schedule.getClasses())} total classes\n")

# Group by course and section
course_hours = {}
for cls in schedule.getClasses():
    key = (cls.course.course_number, cls.section_number, cls.course.course_type)
    if key not in course_hours:
        course_hours[key] = {
            'scheduled': 0,
            'required': cls.course.hours_per_week,
            'continuous_required': cls.course.max_continuous_hours
        }
    course_hours[key]['scheduled'] += 1

# Print results
print(f"{'Course':<10} {'Type':<8} {'Section':<8} {'Scheduled':<12} {'Required':<10} {'Status'}")
print(f"{'-'*70}")

lab_courses = sorted([k for k in course_hours.keys() if k[2] == 'LAB'])
for key in lab_courses:
    course, section, ctype = key
    info = course_hours[key]
    status = "OK" if info['scheduled'] == info['required'] else "FAILED"
    print(f"{course:<10} {ctype:<8} {section:<8} {info['scheduled']:<12} {info['required']:<10} {status}")

print(f"\n{'='*60}\n")

# Calculate fitness to see conflicts
fitness = schedule.calculateFitness()
conflicts = schedule._numberOfConflicts

fitness_pct = fitness * 100
print(f"Fitness: {fitness_pct:.2f}%")
print(f"Conflicts: {conflicts}")

# Expected vs actual classes
expected = 0
for course in year.courses.all():
    if course.course_type in ['LAB', 'THEORY']:
        expected += course.hours_per_week * len(sections)
    elif course.course_type == 'ELECTIVE':
        expected += course.hours_per_week

actual = len(schedule.getClasses())
missing = expected - actual

print(f"\nExpected classes: {expected}")
print(f"Actual classes: {actual}")
print(f"Missing classes: {missing}")
print(f"Missing classes penalty: {missing * 20}")

# Detailed conflict breakdown
print(f"\n{'='*60}")
print(f"CONFLICT BREAKDOWN")
print(f"{'='*60}\n")

classes = schedule.getClasses()

# Check for section clashes
section_clashes = 0
for i in range(len(classes)):
    for j in range(i + 1, len(classes)):
        if (classes[i].section_number == classes[j].section_number and
            classes[i].meeting_time == classes[j].meeting_time):
            section_clashes += 1
            if section_clashes <= 5:  # Show first 5
                print(f"Section Clash: Section {classes[i].section_number} - {classes[i].course.course_number} & {classes[j].course.course_number} at {classes[i].meeting_time.day} {classes[i].meeting_time.time}")

# Check for instructor clashes
instructor_clashes = 0
for i in range(len(classes)):
    for j in range(i + 1, len(classes)):
        if (classes[i].section_number != classes[j].section_number and
            classes[i].meeting_time == classes[j].meeting_time and
            classes[i].instructor == classes[j].instructor):
            instructor_clashes += 1
            if instructor_clashes <= 5:  # Show first 5
                print(f"Instructor Clash: {classes[i].instructor.name} - Sec {classes[i].section_number} {classes[i].course.course_number} & Sec {classes[j].section_number} {classes[j].course.course_number} at {classes[i].meeting_time.day} {classes[i].meeting_time.time}")

print(f"\nTotal Section Clashes: {section_clashes} (penalty: {section_clashes * 100})")
print(f"Total Instructor Clashes: {instructor_clashes} (penalty: {instructor_clashes * 100})")
print(f"Other conflicts: {conflicts - (section_clashes * 100) - (instructor_clashes * 100)}")

