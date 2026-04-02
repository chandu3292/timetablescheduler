import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Course

print("\n" + "="*80)
print("REVERTING OE COURSE TYPE")
print("="*80)

# Revert OE course back to THEORY
oe_course = Course.objects.filter(course_number='23IT6121').first()

if oe_course:
    print(f"\nFound OE Course: {oe_course.course_number} - {oe_course.course_name}")
    print(f"  Current Type: {oe_course.course_type}")
    
    if oe_course.course_type == 'ELECTIVE':
        print(f"  Reverting to THEORY (it's a theory subject that students elect)")
        oe_course.course_type = 'THEORY'
        oe_course.save()
        print(f"  ✅ Reverted to THEORY successfully!")
    else:
        print(f"  ✓ Already marked as THEORY")
else:
    print("\n❌ OE Course (23IT6121) not found!")

print("\n" + "="*80)
print("REVERT COMPLETE")
print("="*80)
print("\n📝 NOTE:")
print("  OE is a THEORY course type (students attend theory lectures)")
print("  But it needs special scheduling: same time for all sections")
print("  Solution: Modify scheduling logic to detect OE/PE courses by number")
print()
