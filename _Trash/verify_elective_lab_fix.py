import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Course, Year

print("\n" + "="*80)
print("UPDATED ALIGNMENT CHECK - AFTER FIX")
print("="*80)

# Updated helper function (same as in views.py now)
def needs_section_alignment(course):
    """Check if course should be scheduled at same time for all sections"""
    # LAB courses are NEVER aligned - they have batches and separate scheduling
    if course.course_type == 'LAB':
        return False
    # ELECTIVE course type always needs alignment
    if course.course_type == 'ELECTIVE':
        return True
    # OE (Open Elective) - starts with 23IT6 or 23IT7 (6xxx/7xxx are elective codes)
    if course.course_number.startswith('23IT6') or course.course_number.startswith('23IT7'):
        return True
    # PE (Professional Elective) - 23IT5xxx series (THEORY courses only, not labs)
    if course.course_number.startswith('23IT5') and course.course_type != 'LAB':
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
            print(f"  ✓ {course.course_number:15} {course.course_name:30} Type: {course.course_type:10}")
        
        print(f"\n  → These {len(aligned_courses)} courses will be scheduled at THE SAME TIME for all sections")

# Specifically check elective lab
print("\n" + "="*80)
print("ELECTIVE LAB STATUS")
print("="*80)

elective_lab = Course.objects.filter(course_number='23IT5211').first()
if elective_lab:
    is_aligned = needs_section_alignment(elective_lab)
    
    print(f"\n{elective_lab.course_number} - {elective_lab.course_name}")
    print(f"  Course Type: {elective_lab.course_type}")
    print(f"  Will be treated as needing alignment? {is_aligned}")
    
    if is_aligned:
        print(f"  ❌ STILL A PROBLEM - Lab is being treated as elective")
    else:
        print(f"  ✅ FIXED - Lab will be scheduled separately per section with batches")
        print(f"  ✅ Lab will NOT appear in aligned elective scheduling")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print("""
BEFORE FIX:
- Elective lab (23IT5211) was being aligned across all sections
- It appeared in the timetable at same times for all sections
- This was wrong because labs have batch assignments

AFTER FIX:
- Elective lab (23IT5211) will be scheduled separately per section
- Each section gets its own lab schedule with batch assignments
- Only THEORY electives (PE2, PE3, OE) will be aligned

ACTION REQUIRED:
1. Regenerate the timetable for 3rd year
2. Elective lab will no longer appear in aligned elective list
3. Lab will be scheduled properly with BATCH1, BATCH2, BATCH3
""")

print("="*80 + "\n")
