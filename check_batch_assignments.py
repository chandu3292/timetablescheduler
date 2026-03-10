import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import *

print("=" * 80)
print("LAB BATCH ASSIGNMENTS")
print("=" * 80)

third_year = Year.objects.filter(year_name__icontains='3').first()
if third_year:
    print(f"\n3rd Year - Section 1:")
    print("-" * 80)
    batches = LabBatchAssignment.objects.filter(
        year=third_year, 
        section_number=1
    ).order_by('course__course_name', 'session_number', 'batch')
    
    for b in batches:
        instructors = list(b.instructors.all())
        inst_ids = ', '.join([i.uid for i in instructors])
        inst_names = ', '.join([i.name for i in instructors])
        print(f"\n{b.course.course_name} | Session {b.session_number} | {b.batch}")
        print(f"  Instructors: {inst_ids} ({inst_names})")
        print(f"  Lab Room: {b.lab_room}")

print("\n" + "=" * 80)
print("2ND YEAR - ELECTIVE LABS")
print("=" * 80)

second_year = Year.objects.filter(year_name__icontains='2').first()
if second_year:
    print(f"\n2nd Year - Section 1:")
    print("-" * 80)
    
    # Check for elective labs
    elective_labs = Course.objects.filter(
        year=second_year,
        course_type='LAB'
    )
    
    for course in elective_labs:
        print(f"\n{course.course_name} ({course.course_number}):")
        
        # Check if there are batch assignments
        batches = LabBatchAssignment.objects.filter(
            year=second_year,
            course=course,
            section_number=1
        )
        
        if batches.exists():
            for b in batches:
                instructors = list(b.instructors.all())
                inst_ids = ', '.join([i.uid for i in instructors])
                print(f"  Session {b.session_number}, {b.batch}: {inst_ids}")
        else:
            # Check regular assignments (instructor field might still exist)
            entries = TimetableEntry.objects.filter(
                year=second_year,
                course=course,
                section_number=1
            ).select_related('instructor')
            
            # Group by instructor
            instructors_seen = set()
            if entries.exists():
                print(f"  Timetable entries for this lab:")
                for e in entries[:10]:
                    if e.instructor and e.instructor.uid not in instructors_seen:
                        instructors_seen.add(e.instructor.uid)
                        print(f"    - {e.instructor.uid} {e.instructor.name}")
