import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import CourseInstructorAssignment, Year, Course
from collections import defaultdict

print("=" * 80)
print("ANALYZING INSTRUCTOR ASSIGNMENTS (MANUAL vs AUTOMATED)")
print("=" * 80)

# Check 2nd and 3rd year instructor overlaps
second_year = Year.objects.filter(year_name__icontains='2').first()
third_year = Year.objects.filter(year_name__icontains='3').first()

if second_year and third_year:
    # Get all instructors assigned to each year
    second_year_instructors = set()
    third_year_instructors = set()
    
    second_assignments = CourseInstructorAssignment.objects.filter(year=second_year)
    third_assignments = CourseInstructorAssignment.objects.filter(year=third_year)
    
    print("\n2ND YEAR INSTRUCTOR ASSIGNMENTS:")
    print("-" * 80)
    for assignment in second_assignments:
        course_name = assignment.course.course_name
        section = assignment.section_number
        instructors = list(assignment.instructors.all())
        
        for inst in instructors:
            second_year_instructors.add(inst.uid)
            print(f"{course_name} Sec{section}: {inst.uid} {inst.name}")
    
    print(f"\nTotal unique 2nd year instructors: {len(second_year_instructors)}")
    
    print("\n" + "=" * 80)
    print("3RD YEAR INSTRUCTOR ASSIGNMENTS:")
    print("-" * 80)
    for assignment in third_assignments:
        course_name = assignment.course.course_name
        section = assignment.section_number
        instructors = list(assignment.instructors.all())
        
        for inst in instructors:
            third_year_instructors.add(inst.uid)
            print(f"{course_name} Sec{section}: {inst.uid} {inst.name}")
    
    print(f"\nTotal unique 3rd year instructors: {len(third_year_instructors)}")
    
    # Find overlapping instructors
    overlap = second_year_instructors & third_year_instructors
    
    print("\n" + "=" * 80)
    print("INSTRUCTORS TEACHING BOTH 2ND AND 3RD YEAR:")
    print("=" * 80)
    
    if overlap:
        print(f"\nFound {len(overlap)} instructors teaching BOTH years:")
        print("-" * 80)
        
        from SchedulerApp.models import Instructor
        for uid in sorted(overlap):
            inst = Instructor.objects.get(uid=uid)
            
            # Find what they teach in each year
            second_courses = []
            for assignment in second_assignments:
                if any(i.uid == uid for i in assignment.instructors.all()):
                    second_courses.append(f"{assignment.course.course_name} (Sec{assignment.section_number})")
            
            third_courses = []
            for assignment in third_assignments:
                if any(i.uid == uid for i in assignment.instructors.all()):
                    third_courses.append(f"{assignment.course.course_name} (Sec{assignment.section_number})")
            
            print(f"\n{uid} - {inst.name}:")
            print(f"  2nd Year: {', '.join(second_courses)}")
            print(f"  3rd Year: {', '.join(third_courses)}")
        
        print("\n" + "=" * 80)
        print("WHY AUTOMATED GENERATION FAILS:")
        print("=" * 80)
        print("""
The automated scheduler uses CONSTRAINT-BASED SCHEDULING:
- It checks that NO instructor can be in two places at once
- It verifies NO room is double-booked
- It ensures NO student has overlapping classes

YOUR MANUAL TIMETABLE allows instructors to teach BOTH 2nd and 3rd year,
but the automated system CANNOT guarantee they won't have conflicts
unless we schedule them carefully.

SOLUTION OPTIONS:
1. Assign DEDICATED instructors to each year (no overlap)
2. Or manually specify which time slots each instructor is available
3. Or generate years in sequence (2nd year first, then 3rd year with remaining slots)
        """)
    else:
        print("\n[OK] No instructor overlap - each year has dedicated instructors!")

print("\n" + "=" * 80)
print("CHECKING CURRENT TIMETABLE STATUS:")
print("=" * 80)

from SchedulerApp.models import TimetableEntry
for year in Year.objects.all().order_by('id'):
    count = TimetableEntry.objects.filter(year=year).count()
    print(f"{year.year_name}: {count} classes {'[GENERATED]' if count > 0 else '[EMPTY]'}")
