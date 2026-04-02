import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, Course, CourseInstructorAssignment
from collections import defaultdict

print("\n" + "="*80)
print("IDENTIFYING GAPS IN SPECIFIC SECTIONS")
print("="*80)

sections_to_check = [
    (12, 3, "2nd Year Section 3"),
    (13, 1, "3rd Year Section 1"),
    (13, 3, "3rd Year Section 3")
]

all_gaps = []

for year_id, section_num, section_name in sections_to_check:
    print(f"\n{section_name}:")
    print("-" * 80)
    
    # Get all course assignments for this year/section
    assignments = CourseInstructorAssignment.objects.filter(
        year=year_id,
        section_number=section_num,
        main_instructor__isnull=False
    ).select_related('course', 'main_instructor')
    
    section_gaps = []
    
    for assignment in assignments:
        course = assignment.course
        
        # Skip special courses
        if course.course_number in ['TRAINING', 'SPORTS_LIBRARY', 'COUNS', 'SPORT', 'COUNSELING']:
            continue
        
        # Count scheduled hours
        entries = TimetableEntry.objects.filter(
            course=course,
            section_number=section_num
        )
        
        if course.course_type == 'LAB':
            scheduled = entries.count()
        else:
            scheduled = entries.filter(batch='FULL').count()
        
        required = course.hours_per_week
        
        if scheduled < required:
            gap = required - scheduled
            instructor = assignment.main_instructor
            section_gaps.append({
                'course': course,
                'course_number': course.course_number,
                'course_name': course.course_name,
                'scheduled': scheduled,
                'required': required,
                'gap': gap,
                'instructor': instructor,
                'year_id': year_id,
                'section': section_num
            })
            print(f"  GAP: {course.course_number} ({course.course_name})")
            print(f"      Scheduled: {scheduled}/{required} hrs (missing {gap})")
            print(f"      Instructor: {instructor.name}")
            all_gaps.append(section_gaps[-1])
    
    if not section_gaps:
        print(f"  No gaps found!")

print("\n" + "="*80)
print(f"TOTAL GAPS TO FIX: {len(all_gaps)}")
print("="*80 + "\n")

# Save gap details for fixing
if all_gaps:
    print("Gap details for manual fixing:")
    for gap in all_gaps:
        print(f"\nYear ID: {gap['year_id']}, Section: {gap['section']}")
        print(f"Course: {gap['course_number']} - {gap['course_name']}")
        print(f"Instructor: {gap['instructor'].uid} - {gap['instructor'].name}")
        print(f"Missing hours: {gap['gap']}")
