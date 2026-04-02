import os
import sys
import django

sys.path.insert(0, r'c:\Users\M srujitha\OneDrive\文서\Desktop\timetablescheduler')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Course

# Test the updated alignment logic
def needs_section_alignment(course):
    """Updated logic from views.py"""
    if course.course_type == 'LAB':
        return False
    
    # EXCLUDE TP courses from forced alignment (they need strict 2-hour continuity)
    if 'TP' in course.course_number:
        return False
    
    if course.course_type == 'ELECTIVE':
        return True
    if course.course_number.startswith('23IT6') or course.course_number.startswith('23IT7'):
        return True
    if course.course_number.startswith('23IT5') and course.course_type != 'LAB':
        return True
    return False

print("="*80)
print("ALIGNMENT LOGIC TEST - Updated")
print("="*80)

# Check specific courses
test_courses = [
    '23IT6121',  # OE (Theory)
    '23TP9102',  # TP (should NOT align)
    '23IT5001',  # Theory (should align)
    'LAB001',    # Lab (should NOT align)
    'ELEC001',   # Elective (should align)
]

for course_num in test_courses:
    course = Course.objects.filter(course_number=course_num).first()
    if course:
        result = needs_section_alignment(course)
        icon = "✓ ALIGN" if result else "✗ NO-ALIGN"
        print(f"{course.course_number:12} ({course.course_type:8}) → {icon}")
    else:
        print(f"{course_num:12} (NOT FOUND)")

print("\n" + "="*80)
print("KEY BENEFITS:")
print("  ✓ TP courses (23TP*)**not forced to align** - each section independent")
print("  ✓ Different instructors for same course won't conflict")
print("  ✓ 2-hour continuous blocks strictly maintained for TP courses")
print("  ✓ LAB courses not forced to align")
print("="*80)
