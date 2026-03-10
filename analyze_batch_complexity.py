import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import LabBatchAssignment, Course, Year

print("="*80)
print("BATCH-SPLIT LAB ANALYSIS")
print("="*80)

for year in Year.objects.all().order_by('id'):
    batch_courses = Course.objects.filter(year=year, split_into_batches=True)
    batch_count = LabBatchAssignment.objects.filter(year=year).count()
    
    print(f"\n{year.year_name}:")
    print(f"  Batch-split courses: {batch_courses.count()}")
    print(f"  Total batch assignments: {batch_count}")
    
    if batch_courses.exists():
        for course in batch_courses:
            print(f"\n  {course.course_name} ({course.course_number}):")
            print(f"    Continuous hours: {course.max_continuous_hours}")
            print(f"    Hours per week: {course.hours_per_week}")
            
            assignments = LabBatchAssignment.objects.filter(
                year=year, 
                course=course
            ).order_by('section_number', 'session_number', 'batch')
            
            current_section = None
            for a in assignments:
                if current_section != a.section_number:
                    current_section = a.section_number
                    print(f"\n    Section {a.section_number}:")
                
                main = a.main_instructor.name if a.main_instructor else "NONE"
                room = a.lab_room.lab_name if a.lab_room else "NO ROOM"
                print(f"      Session {a.session_number} {a.batch}: {room} - Main: {main}")

print("\n" + "="*80)
print("CONSTRAINT ANALYSIS")
print("="*80)

# Check for resource conflicts
year3 = Year.objects.get(year_name='3rd Year')
print("\n3rd Year Resource Constraints:")

# Count unique labs needed
labs_needed = set()
for a in LabBatchAssignment.objects.filter(year=year3):
    if a.lab_room:
        labs_needed.add(a.lab_room.lab_name)

print(f"  Unique lab rooms needed: {len(labs_needed)}")
for lab in sorted(labs_needed):
    count = LabBatchAssignment.objects.filter(year=year3, lab_room__lab_name=lab).count()
    print(f"    - {lab}: used in {count} batch assignments")

# Check instructor load
print("\n  Main instructor distribution:")
from collections import Counter
main_instructors = [a.main_instructor.name for a in LabBatchAssignment.objects.filter(year=year3) if a.main_instructor]
for instructor, count in Counter(main_instructors).most_common():
    print(f"    - {instructor}: {count} batch sessions")
