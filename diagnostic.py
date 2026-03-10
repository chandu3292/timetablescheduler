import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, GeneratedTimetable, Year, Course

print("="*80)
print("DIAGNOSTIC: TIMETABLE GENERATION STATUS")
print("="*80)

# Check generated timetables
print("\n1. Generated Timetable Records:")
gen_timetables = GeneratedTimetable.objects.all().order_by('-generated_at')
if gen_timetables.exists():
    for gt in gen_timetables[:5]:
        print(f"   {gt.year.year_name}: Generated at {gt.generated_at}")
        print(f"     Fitness: {gt.fitness_score}, Generation: {gt.generation_count}")
else:
    print("   No GeneratedTimetable records found")

# Check timetable entries
print("\n2. Timetable Entries:")
for year in Year.objects.all().order_by('id'):
    count = TimetableEntry.objects.filter(year=year).count()
    print(f"   {year.year_name}: {count} classes")
print(f"   Total: {TimetableEntry.objects.count()} classes")

# Check for any issues
print("\n3. Potential Issues:")

# Check for courses without main instructors
from SchedulerApp.models import CourseInstructorAssignment
no_main = []
for year in Year.objects.all():
    for course in year.courses.filter(course_type='LAB'):
        assignments = CourseInstructorAssignment.objects.filter(year=year, course=course)
        for assign in assignments:
            if not assign.main_instructor:
                no_main.append(f"{year.year_name} {course.course_name} Sec{assign.section_number}")

if no_main:
    print("   LAB courses without main instructor:")
    for item in no_main:
        print(f"     - {item}")
else:
    print("   ✓ All LAB courses have main instructors")

# Check for batch-split courses
batch_courses = Course.objects.filter(split_into_batches=True)
if batch_courses.exists():
    print(f"   ⚠ Found {batch_courses.count()} batch-split courses (should be 0)")
    for c in batch_courses:
        print(f"     - {c.course_name}")
else:
    print("   ✓ No batch-split courses (correct)")

# Check for orphaned batch assignments
from SchedulerApp.models import LabBatchAssignment
batch_assigns = LabBatchAssignment.objects.all()
if batch_assigns.exists():
    print(f"   ⚠ Found {batch_assigns.count()} batch assignments (should be 0)")
else:
    print("   ✓ No batch assignments (correct)")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)

if TimetableEntry.objects.count() > 0:
    print("\n✅ Timetables Generated Successfully")
    print(f"   Total classes: {TimetableEntry.objects.count()}")
    print(f"   Latest generation: {gen_timetables.first().generated_at if gen_timetables.exists() else 'Unknown'}")
else:
    print("\n❌ No Timetables Found")
    print("   Run: python generate_sequential.py")

print("\n" + "="*80)
