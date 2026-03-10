import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import CourseInstructorAssignment, LabBatchAssignment, Year

print("="*80)
print("CROSS-YEAR INSTRUCTOR ANALYSIS")
print("="*80)

# Get 3rd year batch instructors
year3 = Year.objects.get(year_name='3rd Year')
year2 = Year.objects.get(year_name='2nd Year')

year3_batch_instructors = set()
for a in LabBatchAssignment.objects.filter(year=year3):
    if a.main_instructor:
        year3_batch_instructors.add(a.main_instructor)

print(f"\n3rd Year batch-split lab main instructors: {len(year3_batch_instructors)}")
for instructor in sorted(year3_batch_instructors, key=lambda x: x.name):
    print(f"  - {instructor.name}")

# Check which ones also teach 2nd year
print("\n" + "="*80)
print("SHARED INSTRUCTORS (Teach both 2nd and 3rd year)")
print("="*80)

shared_count = 0
for instructor in sorted(year3_batch_instructors, key=lambda x: x.name):
    # Check if they're assigned to ANY 2nd year course
    year2_assignments = CourseInstructorAssignment.objects.filter(
        year=year2,
        instructors=instructor
    )
    
    # Also check if they're main instructor for 2nd year labs
    year2_main = CourseInstructorAssignment.objects.filter(
        year=year2,
        main_instructor=instructor
    )
    
    if year2_assignments.exists() or year2_main.exists():
        shared_count += 1
        print(f"\n{instructor.name}:")
        print(f"  3rd Year batch assignments: {LabBatchAssignment.objects.filter(year=year3, main_instructor=instructor).count()}")
        
        if year2_main.exists():
            print(f"  2nd Year main instructor for:")
            for assign in year2_main:
                print(f"    - {assign.course.course_name} (Sec {assign.section_number})")
        
        if year2_assignments.exists():
            print(f"  2nd Year also teaches:")
            for assign in year2_assignments:
                is_main = " [MAIN]" if assign.main_instructor == instructor else ""
                print(f"    - {assign.course.course_name} (Sec {assign.section_number}){is_main}")

print(f"\n{'='*80}")
print(f"SUMMARY: {shared_count}/{len(year3_batch_instructors)} batch instructors also teach 2nd year")
print(f"Sharing percentage: {shared_count/len(year3_batch_instructors)*100:.1f}%")
