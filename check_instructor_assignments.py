import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import CourseInstructorAssignment, Course, Year

print("=" * 80)
print("COURSE INSTRUCTOR ASSIGNMENTS - 2ND YEAR SECTION 1")
print("=" * 80)

second_year = Year.objects.filter(year_name__icontains='2').first()
if second_year:
    # Check OS Lab
    os_lab = Course.objects.get(course_number='23IT4217')
    
    print(f"\nCourse: {os_lab.course_name} ({os_lab.course_number})")
    print(f"Split into batches: {os_lab.split_into_batches}")
    
    assignments = CourseInstructorAssignment.objects.filter(
        year=second_year,
        course=os_lab
    )
    
    print(f"\nCourseInstructorAssignment records: {assignments.count()}")
    for assign in assignments:
        instructors = list(assign.instructors.all())
        inst_names = [f"{i.uid} {i.name}" for i in instructors]
        print(f"  Section {assign.section_number}: {len(instructors)} instructors")
        for name in inst_names:
            print(f"    - {name}")

print("\n" + "=" * 80)
print("COURSE INSTRUCTOR ASSIGNMENTS - 3RD YEAR SECTION 1")
print("=" * 80)

third_year = Year.objects.filter(year_name__icontains='3').first()
if third_year:
    # Check IoT Lab
    iot_lab = Course.objects.get(course_number='23IT4222')
    
    print(f"\nCourse: {iot_lab.course_name} ({iot_lab.course_number})")
    print(f"Split into batches: {iot_lab.split_into_batches}")
    
    assignments = CourseInstructorAssignment.objects.filter(
        year=third_year,
        course=iot_lab
    )
    
    print(f"\nCourseInstructorAssignment records: {assignments.count()}")
    for assign in assignments:
        instructors = list(assign.instructors.all())
        inst_names = [f"{i.uid} {i.name}" for i in instructors]
        print(f"  Section {assign.section_number}: {len(instructors)} instructors")
        for name in inst_names:
            print(f"    - {name}")
