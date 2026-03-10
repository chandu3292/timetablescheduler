import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Year, Course, CourseInstructorAssignment

print("=" * 80)
print("2ND YEAR COURSES ANALYSIS")
print("=" * 80)

second_year = Year.objects.filter(year_name__icontains='2').first()
if second_year:
    courses = Course.objects.filter(year=second_year)
    
    print(f"\nTotal courses: {courses.count()}")
    
    for course_type in ['THEORY', 'LAB', 'ELECTIVE']:
        type_courses = courses.filter(course_type=course_type)
        print(f"\n{course_type}: {type_courses.count()} courses")
        
        for course in type_courses:
            print(f"\n  {course.course_number} - {course.course_name}")
            print(f"    Hours/week: {course.hours_per_week}, Max continuous: {course.max_continuous_hours}")
            print(f"    Split batches: {course.split_into_batches}")
            
            # Check instructor assignments for section 1
            assignment = CourseInstructorAssignment.objects.filter(
                year=second_year,
                course=course,
                section_number=1
            ).first()
            
            if assignment:
                instructors = list(assignment.instructors.all())
                print(f"    Section 1 instructors: {len(instructors)} assigned")
                if len(instructors) == 0:
                    print(f"      WARNING: No instructors assigned!")
            else:
                # Check course-level instructors
                course_instructors = list(course.instructors.all())
                if course_instructors:
                    print(f"    Course-level instructors: {len(course_instructors)} assigned")
                else:
                    print(f"    WARNING: No instructors at all!")
