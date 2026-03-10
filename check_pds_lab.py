import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import CourseInstructorAssignment, Year, Course

# Get 2nd year
year = Year.objects.get(year_name__icontains='2nd')

# Get PDS Lab (23IT4218)
course = Course.objects.get(course_number='23IT4218')

print("PDS Lab (23IT4218) Instructor Assignments:")
print()

assignments = CourseInstructorAssignment.objects.filter(
    year=year,
    course=course
).order_by('section_number')

for assignment in assignments:
    instructors = list(assignment.instructors.all())
    print(f"Section {assignment.section_number}:")
    print(f"  Main instructor: {assignment.main_instructor.name if assignment.main_instructor else 'NOT SET'}")
    print(f"  All instructors: {', '.join([i.name for i in instructors])}")
    print()
