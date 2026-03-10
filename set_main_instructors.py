import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import CourseInstructorAssignment, Instructor, Course, Year

# Get 3rd year
year = Year.objects.get(year_name__icontains='3rd')

# Get course 23IT5211
course = Course.objects.get(course_number='23IT5211')

print("Setting main instructors for 23IT5211...")
print()

# Section 2: Main instructor = Mr. KSN Murthy
try:
    assignment_sec2 = CourseInstructorAssignment.objects.get(
        year=year,
        section_number=2,
        course=course
    )
    
    # Find KSN Murthy
    ksn_murthy = Instructor.objects.filter(name__icontains='KSN Murthy').first()
    
    if ksn_murthy:
        assignment_sec2.main_instructor = ksn_murthy
        assignment_sec2.save()
        print(f"✓ Section 2: Set main instructor to {ksn_murthy.name}")
        print(f"  All instructors: {', '.join([i.name for i in assignment_sec2.instructors.all()])}")
    else:
        print("✗ Section 2: Could not find KSN Murthy")
except CourseInstructorAssignment.DoesNotExist:
    print("✗ Section 2: Assignment not found")

print()

# Section 3: Main instructor = Mrs. V Krishna Sameera
try:
    assignment_sec3 = CourseInstructorAssignment.objects.get(
        year=year,
        section_number=3,
        course=course
    )
    
    # Find V Krishna Sameera
    krishna_sameera = Instructor.objects.filter(name__icontains='Krishna').first()
    
    if krishna_sameera:
        assignment_sec3.main_instructor = krishna_sameera
        assignment_sec3.save()
        print(f"✓ Section 3: Set main instructor to {krishna_sameera.name}")
        print(f"  All instructors: {', '.join([i.name for i in assignment_sec3.instructors.all()])}")
    else:
        print("✗ Section 3: Could not find Krishna Sameera")
except CourseInstructorAssignment.DoesNotExist:
    print("✗ Section 3: Assignment not found")

print()
print("Done!")
