import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Year, Course, CourseInstructorAssignment

print("\n=== ANALYZING 23IT5211 INSTRUCTOR ASSIGNMENTS ===\n")

year_3 = Year.objects.get(year_name__icontains='3')
course = Course.objects.get(course_number='23IT5211', year=year_3)

print(f"Course: {course.course_name} ({course.course_number})")
print(f"Type: {course.course_type}")
print(f"Hours: {course.hours_per_week} (continuous: {course.max_continuous_hours})")
print()

for section in [1, 2, 3]:
    assignment = CourseInstructorAssignment.objects.filter(
        year=year_3,
        section_number=section,
        course=course
    ).first()
    
    if assignment:
        instructors = list(assignment.instructors.all())
        print(f"Section {section}: {[i.name for i in instructors]}")
    else:
        print(f"Section {section}: NO ASSIGNMENT")

print("\n=== INSTRUCTOR OVERLAP ANALYSIS ===\n")

# Get all instructors
sec1_assignment = CourseInstructorAssignment.objects.filter(
    year=year_3, section_number=1, course=course
).first()
sec2_assignment = CourseInstructorAssignment.objects.filter(
    year=year_3, section_number=2, course=course
).first()
sec3_assignment = CourseInstructorAssignment.objects.filter(
    year=year_3, section_number=3, course=course
).first()

if sec1_assignment and sec2_assignment and sec3_assignment:
    sec1_instructors = set(i.name for i in sec1_assignment.instructors.all())
    sec2_instructors = set(i.name for i in sec2_assignment.instructors.all())
    sec3_instructors = set(i.name for i in sec3_assignment.instructors.all())
    
    overlap_2_3 = sec2_instructors & sec3_instructors
    overlap_1_2 = sec1_instructors & sec2_instructors
    overlap_1_3 = sec1_instructors & sec3_instructors
    
    print(f"Section 1 ∩ Section 2: {overlap_1_2}")
    print(f"Section 1 ∩ Section 3: {overlap_1_3}")
    print(f"Section 2 ∩ Section 3: {overlap_2_3}")
    
    if overlap_2_3:
        print(f"\n⚠️ PROBLEM: Sections 2 and 3 share instructors: {overlap_2_3}")
        print("   This creates a scheduling conflict!")
        print("   These instructors cannot teach both sections at different times.")
        print("\n   SOLUTION OPTIONS:")
        print("   1. Remove shared instructors from one section")
        print("   2. If all sections meet at SAME time (like electives), mark as ELECTIVE type")
        print("   3. Assign different instructors to each section")
