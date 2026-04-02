import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Course

print("\n" + "="*80)
print("CHECKING ELECTIVE LAB COURSE")
print("="*80)

# Find elective lab
elective_lab = Course.objects.filter(course_number='23IT5211').first()

if elective_lab:
    print(f"\nFound: {elective_lab.course_number} - {elective_lab.course_name}")
    print(f"  Course Type: {elective_lab.course_type}")
    print(f"  Hours per week: {elective_lab.hours_per_week}")
    print(f"  Max continuous: {elective_lab.max_continuous_hours}")
    
    # Check if it would be caught by needs_section_alignment
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
    
    is_aligned = needs_section_alignment(elective_lab)
    
    print(f"\n  Will be treated as needing alignment? {is_aligned}")
    
    if is_aligned:
        print(f"\n  ⚠️ PROBLEM IDENTIFIED!")
        print(f"  This is a LAB course but it's being treated as an elective")
        print(f"  because its course number starts with '23IT5'")
        print(f"\n  LAB courses should be scheduled separately per section,")
        print(f"  NOT aligned across sections like elective theory courses.")
    
    print("\n" + "="*80)
    print("SOLUTION")
    print("="*80)
    print("\nThe needs_section_alignment() function should EXCLUDE LAB courses.")
    print("Only THEORY and ELECTIVE type courses should be aligned.")
    print("\nLABs have their own batch assignments and need separate scheduling.")
else:
    print("\nElective lab course not found!")

print()
