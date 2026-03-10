import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Year, Course, CourseInstructorAssignment, LabBatchAssignment

print("\n=== DIAGNOSING 3RD YEAR LAB INSTRUCTOR ASSIGNMENTS ===\n")

year_3 = Year.objects.get(year_name__icontains='3')
lab_courses = Course.objects.filter(year=year_3, course_type='LAB')

print(f"Found {lab_courses.count()} lab courses:\n")

for course in lab_courses:
    print(f"\n{course.course_name} ({course.course_number})")
    print(f"  split_into_batches: {course.split_into_batches}")
    print(f"  hours_per_week: {course.hours_per_week}")
    print(f"  max_continuous_hours: {course.max_continuous_hours}")
    
    # Check direct course instructors (fallback)
    direct_instructors = course.instructors.all()
    print(f"  Direct instructors: {direct_instructors.count()} - {[i.name for i in direct_instructors]}")
    
    # For each section, check assignments
    for section in [1, 2, 3]:
        print(f"\n  Section {section}:")
        
        if course.split_into_batches:
            # Should have LabBatchAssignment
            batch_assignments = LabBatchAssignment.objects.filter(
                year=year_3,
                section_number=section,
                course=course
            )
            if batch_assignments.exists():
                print(f"    ✓ Lab Batch Assignments: {batch_assignments.count()}")
                for ba in batch_assignments:
                    instructors = ba.instructors.all()
                    print(f"      {ba.batch} Session{ba.session_number}: {[i.name for i in instructors]} @ {ba.lab_room}")
            else:
                print(f"    ✗ NO Lab Batch Assignments!")
                if direct_instructors.count() == 0:
                    print(f"      ⚠️ CRITICAL: No fallback instructors either!")
        else:
            # Should have CourseInstructorAssignment
            instructor_assignment = CourseInstructorAssignment.objects.filter(
                year=year_3,
                section_number=section,
                course=course
            )
            if instructor_assignment.exists():
                instructors = instructor_assignment.first().instructors.all()
                print(f"    ✓ CourseInstructorAssignment: {[i.name for i in instructors]}")
            else:
                print(f"    ✗ NO CourseInstructorAssignment!")
                if direct_instructors.count() > 0:
                    print(f"      → Will use fallback: {[i.name for i in direct_instructors]}")
                else:
                    print(f"      ⚠️ CRITICAL: No fallback instructors either!")

print("\n\n=== SUMMARY ===")
print("Courses with missing assignments will cause scheduling to fail!")
