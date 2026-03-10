import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, CourseInstructorAssignment

print("=" * 80)
print("VERIFYING SHARED INSTRUCTORS NO LONGER HAVE CONFLICTS")
print("=" * 80)

# The 18 instructors who teach BOTH 2nd and 3rd year
shared_instructors = ['IT02', 'IT03', 'IT04', 'IT06', 'IT09', 'IT10', 'IT12', 
                      'IT14', 'IT17', 'IT20', 'IT21', 'IT23', 'IT25', 'IT28',
                      'TP01', 'TP04', 'TP07', 'TP08']

print(f"\nChecking {len(shared_instructors)} instructors who teach both 2nd and 3rd year...")
print("-" * 80)

conflicts_found = 0

for uid in shared_instructors:
    # Get all 2nd year assignments for this instructor
    second_assignments = CourseInstructorAssignment.objects.filter(
        year__year_name__icontains='2',
        instructors__uid=uid
    )
    
    # Get all 3rd year assignments for this instructor
    third_assignments = CourseInstructorAssignment.objects.filter(
        year__year_name__icontains='3',
        instructors__uid=uid
    )
    
    if second_assignments.exists() and third_assignments.exists():
        # Get timetable entries for 2nd year
        second_entries = []
        for assignment in second_assignments:
            entries = TimetableEntry.objects.filter(
                year=assignment.year,
                section_number=assignment.section_number,
                course=assignment.course
            )
            second_entries.extend(list(entries))
        
        # Get timetable entries for 3rd year
        third_entries = []
        for assignment in third_assignments:
            entries = TimetableEntry.objects.filter(
                year=assignment.year,
                section_number=assignment.section_number,
                course=assignment.course
            )
            third_entries.extend(list(entries))
        
        # Check for time conflicts
        instructor_conflicts = 0
        for entry2 in second_entries:
            for entry3 in third_entries:
                if entry2.meeting_time == entry3.meeting_time:
                    print(f"\n{uid} CONFLICT:")
                    print(f"  2nd Year: {entry2.course.course_name} Sec{entry2.section_number} @ {entry2.meeting_time}")
                    print(f"  3rd Year: {entry3.course.course_name} Sec{entry3.section_number} @ {entry3.meeting_time}")
                    instructor_conflicts += 1
        
        if instructor_conflicts > 0:
            conflicts_found += instructor_conflicts
        # else:
        #     print(f"{uid}: OK - no conflicts")

print("\n" + "=" * 80)
if conflicts_found == 0:
    print(f"✓✓✓ SUCCESS! ZERO conflicts among {len(shared_instructors)} shared instructors!")
    print("Sequential generation successfully avoided all instructor conflicts!")
else:
    print(f"Found {conflicts_found} instructor conflicts")
print("=" * 80)
