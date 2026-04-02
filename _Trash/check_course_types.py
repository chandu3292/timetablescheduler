import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Course, Year

print("\n" + "="*80)
print("COURSE TYPE ANALYSIS")
print("="*80)

years = Year.objects.all()

for year in years:
    courses = Course.objects.filter(year=year)
    print(f"\n{year.year_name}:")
    print("-" * 80)
    
    for course in courses:
        print(f"  {course.course_number:15} {course.course_name:30} Type: {course.course_type:10} ({course.hours_per_week}hrs/week, max_continuous={course.max_continuous_hours})")
    
    # Count by type
    theory_count = courses.filter(course_type='THEORY').count()
    lab_count = courses.filter(course_type='LAB').count()
    elective_count = courses.filter(course_type='ELECTIVE').count()
    
    print(f"\n  Summary: {theory_count} THEORY, {lab_count} LAB, {elective_count} ELECTIVE")

print("\n" + "="*80)
print("LOOKING FOR PE/OE COURSES")
print("="*80)

pe_courses = Course.objects.filter(course_number='23IT5211')
oe_courses = Course.objects.filter(course_number='23IT6121')

print(f"\nPE Course (23IT5211):")
for course in pe_courses:
    print(f"  Year: {course.year.year_name}, Type: '{course.course_type}', Name: {course.course_name}")

print(f"\nOE Course (23IT6121):")
for course in oe_courses:
    print(f"  Year: {course.year.year_name}, Type: '{course.course_type}', Name: {course.course_name}")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80 + "\n")
