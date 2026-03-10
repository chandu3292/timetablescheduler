import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Year, Course, CourseInstructorAssignment, LabBatchAssignment

print("\n=== DIAGNOSING PROFESSIONAL ELECTIVE COURSES ===\n")

# List of courses mentioned by user
pe_courses = ['23TP9102', '23TP9103', '23TP9104', '23TP90104', '23TP19104']

year_3 = Year.objects.get(year_name__icontains='3')

for course_num in pe_courses:
    # Try to find the course
    courses = Course.objects.filter(course_number=course_num, year=year_3)
    
    if not courses.exists():
        print(f"{course_num}: NOT FOUND in database")
        continue
    
    course = courses.first()
    print(f"\n{course.course_number} - {course.course_name}")
    print(f"  Type: {course.course_type}")
    print(f"  Hours/week: {course.hours_per_week}")
    print(f"  Max continuous: {course.max_continuous_hours}")
    print(f"  Split into batches: {course.split_into_batches}")
    
    # Check lab rooms
    lab_rooms = course.lab_rooms.all()
    print(f"  Lab rooms assigned: {lab_rooms.count()}")
    if lab_rooms.count() > 0:
        for room in lab_rooms:
            print(f"    - {room.lab_name}")
    
    # Check direct instructors
    direct_inst = course.instructors.all()
    print(f"  Direct instructors: {direct_inst.count()}")
    
    # Check section assignments
    print(f"  Section assignments:")
    for section in [1, 2, 3]:
        # Check CourseInstructorAssignment
        assignments = CourseInstructorAssignment.objects.filter(
            year=year_3,
            section_number=section,
            course=course
        )
        if assignments.exists():
            instructors = assignments.first().instructors.all()
            print(f"    Sec {section}: {[i.name for i in instructors]}")
        else:
            print(f"    Sec {section}: ⚠️ NO ASSIGNMENT")
            
    # Check if it has batch assignments
    batch_assignments = LabBatchAssignment.objects.filter(
        year=year_3,
        course=course
    )
    if batch_assignments.exists():
        print(f"  ⚠️ Has {batch_assignments.count()} batch assignments (unexpected for classroom labs)")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print("For classroom-based lab courses (professional electives):")
print("  ✓ Should have course_type = 'LAB' (needs continuous blocks)")
print("  ✓ Should NOT have lab_rooms assigned (uses regular classrooms)")
print("  ✓ Should have CourseInstructorAssignment for each section")
print("  ✓ Should NOT have LabBatchAssignment (not split)")
