import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Course, Year

print("\n" + "="*80)
print("COURSES THAT WILL BE ALIGNED ACROSS SECTIONS")
print("="*80)

# Helper function (same as in views.py)
def needs_section_alignment(course):
    """Check if course should be scheduled at same time for all sections"""
    if course.course_type == 'ELECTIVE':
        return True
    # OE (Open Elective) - 23IT6xxx or 23IT7xxx
    if course.course_number.startswith('23IT6') or course.course_number.startswith('23IT7'):
        return True
    # PE (Professional Elective) - 23IT5xxx
    if course.course_number.startswith('23IT5'):
        return True
    return False

years = Year.objects.all()

for year in years:
    courses = Course.objects.filter(year=year)
    aligned_courses = [c for c in courses if needs_section_alignment(c)]
    
    if aligned_courses:
        print(f"\n{year.year_name}:")
        print("-" * 80)
        
        for course in aligned_courses:
            reason = []
            if course.course_type == 'ELECTIVE':
                reason.append("type=ELECTIVE")
            if course.course_number.startswith('23IT6') or course.course_number.startswith('23IT7'):
                reason.append("Open Elective (6xxx/7xxx)")
            if course.course_number.startswith('23IT5'):
                reason.append("Professional Elective (5xxx)")
            
            print(f"  ✓ {course.course_number:15} {course.course_name:30} Type: {course.course_type:10} ({', '.join(reason)})")
        
        print(f"\n  → These {len(aligned_courses)} courses will be scheduled at THE SAME TIME for all sections")
        print(f"  → Students can choose between different elective options")

print("\n" + "="*80)
print("WHAT THIS MEANS")
print("="*80)
print("""
When you regenerate the timetable:

1. OE (Open Elective) - ALL sections will have OE at the same time slots
   Example: If Section 1 has OE on Monday 10:35, Sections 2 & 3 also get Monday 10:35

2. PE (Professional Electives) - ALL sections will have PE at the same time slots  
   Example: If PE2 is Monday 2:00, all sections have PE2 at Monday 2:00

3. This allows students to:
   - Choose ANY elective option regardless of their home section
   - Sit in different sections based on which elective they selected
   - Have flexibility in course selection

4. Regular theory courses (DAA, cryptography, etc.) will still be scheduled 
   separately per section as before.
""")

print("="*80)
print("ACTION REQUIRED")
print("="*80)
print("\n1. Regenerate the timetable for affected years (3rd year has OE/PE)")
print("2. Run: python check_elective_alignment.py")
print("3. Verify all sections show OE/PE at same time slots")
print()
