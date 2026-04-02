import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Course

print("\n" + "="*80)
print("FIXING ELECTIVE COURSE TYPES")
print("="*80)

# Find OE course
oe_course = Course.objects.filter(course_number='23IT6121').first()

if oe_course:
    print(f"\nFound OE Course: {oe_course.course_number} - {oe_course.course_name}")
    print(f"  Current Type: {oe_course.course_type}")
    
    if oe_course.course_type != 'ELECTIVE':
        print(f"  ❌ INCORRECT - Should be 'ELECTIVE'")
        print(f"  Updating to ELECTIVE...")
        oe_course.course_type = 'ELECTIVE'
        oe_course.save()
        print(f"  ✅ Updated successfully!")
    else:
        print(f"  ✓ Already marked as ELECTIVE")
else:
    print("\n❌ OE Course (23IT6121) not found!")

# Check PE/Elective Lab
pe_lab = Course.objects.filter(course_number='23IT5211').first()
if pe_lab:
    print(f"\nFound PE Lab: {pe_lab.course_number} - {pe_lab.course_name}")
    print(f"  Current Type: {pe_lab.course_type}")
    print(f"  Note: This is a LAB type, which is correct for lab courses")
    print(f"  LAB types already get special continuous block scheduling")

# List all ELECTIVE type courses
print("\n" + "="*80)
print("ALL ELECTIVE TYPE COURSES (After Update)")
print("="*80)

elective_courses = Course.objects.filter(course_type='ELECTIVE')
for course in elective_courses:
    print(f"  {course.course_number:15} {course.course_name:30} ({course.hours_per_week}hrs/week, max={course.max_continuous_hours})")

print("\n" + "="*80)
print("UPDATE COMPLETE")
print("="*80)
print("\n⚠️  ACTION REQUIRED:")
print("  1. Regenerate the timetable for 3rd year")
print("  2. OE (23IT6121) will now be scheduled at the same time for all sections")
print("  3. Run 'python check_elective_alignment.py' to verify")
print()
