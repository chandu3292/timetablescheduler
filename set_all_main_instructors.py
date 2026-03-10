import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import CourseInstructorAssignment, LabBatchAssignment, Year

# Process all years
for year in Year.objects.all():
    print(f"\n{year.year_name} Lab Instructor Assignments")
    print("=" * 80)
    
    # CourseInstructorAssignment (regular labs)
    lab_assignments = CourseInstructorAssignment.objects.filter(
        year=year,
        course__course_type='LAB'
    ).order_by('course__course_number', 'section_number')
    
    if lab_assignments.exists():
        print("\nRegular Labs:")
        for assignment in lab_assignments:
            instructors = list(assignment.instructors.all())
            if instructors:
                if not assignment.main_instructor:
                    assignment.main_instructor = instructors[0]
                    assignment.save()
                    print(f"  {assignment.course.course_number} Sec{assignment.section_number}: "
                          f"Set main={assignment.main_instructor.name}")
                else:
                    print(f"  {assignment.course.course_number} Sec{assignment.section_number}: "
                          f"Already set: {assignment.main_instructor.name}")
    
    # LabBatchAssignment (split labs)
    batch_assignments = LabBatchAssignment.objects.filter(
        year=year
    ).order_by('course__course_number', 'section_number', 'batch', 'session_number')
    
    if batch_assignments.exists():
        print("\nSplit Labs:")
        for assignment in batch_assignments:
            instructors = list(assignment.instructors.all())
            if instructors:
                if not assignment.main_instructor:
                    assignment.main_instructor = instructors[0]
                    assignment.save()
                    print(f"  {assignment.course.course_number} Sec{assignment.section_number} "
                          f"{assignment.batch} Session{assignment.session_number}: "
                          f"Set main={assignment.main_instructor.name}")
                else:
                    print(f"  {assignment.course.course_number} Sec{assignment.section_number} "
                          f"{assignment.batch} Session{assignment.session_number}: "
                          f"Already set: {assignment.main_instructor.name}")

print("\nDone!")
