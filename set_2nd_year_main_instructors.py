import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import CourseInstructorAssignment, Year, Course

# Get 2nd year
year = Year.objects.get(year_name__icontains='2nd')

# Get all lab course assignments for 2nd year
lab_assignments = CourseInstructorAssignment.objects.filter(
    year=year,
    course__course_type='LAB'
).order_by('course__course_number', 'section_number')

print("2nd Year Lab Instructor Assignments")
print("=" * 80)
print()

for assignment in lab_assignments:
    instructors = list(assignment.instructors.all())
    print(f"{assignment.course.course_number} - Section {assignment.section_number}")
    print(f"  Current main: {assignment.main_instructor.name if assignment.main_instructor else 'NOT SET'}")
    print(f"  All instructors: {', '.join([i.name for i in instructors])}")
    
    # If no main instructor set, use the first one
    if not assignment.main_instructor and instructors:
        assignment.main_instructor = instructors[0]
        assignment.save()
        print(f"  ✓ Set main instructor to: {instructors[0].name}")
    
    print()

print("Done!")
