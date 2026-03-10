import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import CourseInstructorAssignment, Instructor, Year, Course

# Get 2nd year
year = Year.objects.get(year_name__icontains='2nd')

# Get PDS Lab (23IT4218)
course = Course.objects.get(course_number='23IT4218')

# Fix Section 2: Main should be Dr.P.Laxmi Kanth (first in list)
assignment = CourseInstructorAssignment.objects.get(year=year, section_number=2, course=course)

# Get Dr.P.Laxmi Kanth
dr_laxmi = Instructor.objects.get(name__icontains='Laxmi Kanth')

assignment.main_instructor = dr_laxmi
assignment.save()

print(f"✓ Fixed Section 2: Main instructor set to {dr_laxmi.name}")
print(f"  All instructors: {', '.join([i.name for i in assignment.instructors.all()])}")

# Also fix Section 3 to match original
assignment3 = CourseInstructorAssignment.objects.get(year=year, section_number=3, course=course)
mrs_tejaswi = Instructor.objects.get(name__icontains='Tejaswi')

assignment3.main_instructor = mrs_tejaswi
assignment3.save()

print(f"✓ Fixed Section 3: Main instructor set to {mrs_tejaswi.name}")
print(f"  All instructors: {', '.join([i.name for i in assignment3.instructors.all()])}")
