import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Course, Year

print("=" * 80)
print("2ND YEAR LAB COURSES CONFIGURATION")
print("=" * 80)

second_year = Year.objects.filter(year_name__icontains='2').first()
if second_year:
    labs = Course.objects.filter(year=second_year, course_type='LAB')
    
    for lab in labs:
        instructors = list(lab.instructors.all())
        inst_names = [i.name for i in instructors]
        
        print(f"\n{lab.course_number} - {lab.course_name}")
        print(f"  Type: {lab.course_type}")
        print(f"  Split into batches: {lab.split_into_batches}")
        print(f"  Hours per week: {lab.hours_per_week}")
        print(f"  Max continuous: {lab.max_continuous_hours}")
        print(f"  Instructors ({len(instructors)}): {', '.join(inst_names)}")

print("\n" + "=" * 80)
print("3RD YEAR BATCH-SPLIT LABS")
print("=" * 80)

third_year = Year.objects.filter(year_name__icontains='3').first()
if third_year:
    split_labs = Course.objects.filter(year=third_year, split_into_batches=True)
    
    for lab in split_labs:
        instructors = list(lab.instructors.all())
        inst_names = [i.name for i in instructors]
        
        print(f"\n{lab.course_number} - {lab.course_name}")
        print(f"  Type: {lab.course_type}")
        print(f"  Split into batches: {lab.split_into_batches}")
        print(f"  Hours per week: {lab.hours_per_week}")
        print(f"  Max continuous: {lab.max_continuous_hours}")
        print(f"  Instructors ({len(instructors)}): {', '.join(inst_names)}")
