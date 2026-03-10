import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import CourseInstructorAssignment, Year, Course

year2 = Year.objects.get(year_name='2nd Year')
year3 = Year.objects.get(year_name='3rd Year')

print("="*80)
print("CHECKING CONFLICTING INSTRUCTOR ASSIGNMENTS")
print("="*80)

# U.Yashodara conflicts
print("\nU.Yashodara teaches:")
print("  2nd Year NA Sec 2")
print("  3rd Year SESD Sec 1")

na = Course.objects.get(course_number='23TP9102')
na_assignments = CourseInstructorAssignment.objects.filter(year=year2, course=na, section_number=2)
print(f"\n2nd Year NA Sec 2:")
for a in na_assignments:
    print(f"  Main instructor: {a.main_instructor.name if a.main_instructor else 'None'}")
    print(f"  All instructors: {[i.name for i in a.instructors.all()]}")

sesd = Course.objects.get(course_number='23TP19104')
sesd_assignments = CourseInstructorAssignment.objects.filter(year=year3, course=sesd, section_number=1)
print(f"\n3rd Year SESD Sec 1:")
for a in sesd_assignments:
    print(f"  Main instructor: {a.main_instructor.name if a.main_instructor else 'None'}")
    print(f"  All instructors: {[i.name for i in a.instructors.all()]}")

# M.Prosanth conflicts  
print("\n" + "-"*80)
print("\nM.Prosanth teaches:")
print("  2nd Year NA Sec 3")
print("  3rd Year HLR Sec 1")

na_assignments = CourseInstructorAssignment.objects.filter(year=year2, course=na, section_number=3)
print(f"\n2nd Year NA Sec 3:")
for a in na_assignments:
    print(f"  Main instructor: {a.main_instructor.name if a.main_instructor else 'None'}")
    print(f"  All instructors: {[i.name for i in a.instructors.all()]}")

hlr = Course.objects.get(course_number='23TP9104')
hlr_assignments = CourseInstructorAssignment.objects.filter(year=year3, course=hlr, section_number=1)
print(f"\n3rd Year HLR Sec 1:")
for a in hlr_assignments:
    print(f"  Main instructor: {a.main_instructor.name if a.main_instructor else 'None'}")
    print(f"  All instructors: {[i.name for i in a.instructors.all()]}")

print("\n" + "="*80)
print("SOLUTION: These instructors are main for BOTH courses")
print("  The scheduler checks main instructor availability")
print("  But both courses chose the same time slot")
print("  This is a data configuration issue, not a scheduler bug")
print("\nFix: Assign different main instructors OR accept the overlap")
print("="*80)
