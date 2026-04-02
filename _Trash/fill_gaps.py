import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, MeetingTime, CourseInstructorAssignment, Course, Year, GeneratedTimetable

print("\n" + "="*80)
print("FILLING IDENTIFIED GAPS")
print("="*80)

# Define gaps to fill (excluding Saturday)
gaps_to_fill = [
    {
        'year_id': 12,
        'section': 3,
        'section_name': '2nd Year Section 3',
        'day': 'Friday',
        'time': '8:45 - 9:45'
    },
    {
        'year_id': 13,
        'section': 1,
        'section_name': '3rd Year Section 1',
        'day': 'Wednesday',
        'time': '2:45 - 3:35'
    },
    {
        'year_id': 13,
        'section': 1,
        'section_name': '3rd Year Section 1',
        'day': 'Friday',
        'time': '11:25 - 12:15'
    },
    {
        'year_id': 13,
        'section': 3,
        'section_name': '3rd Year Section 3',
        'day': 'Wednesday',
        'time': '11:25 - 12:15'
    }
]

filled_count = 0

for gap in gaps_to_fill:
    print(f"\n{gap['section_name']} - {gap['day']} {gap['time']}")
    print("-" * 80)
    
    # Get meeting time object
    meeting_time = MeetingTime.objects.get(
        day=gap['day'], 
        time=gap['time'],
        year=gap['year_id']
    )
    
    # Get all courses for this year/section
    assignments = CourseInstructorAssignment.objects.filter(
        year=gap['year_id'],
        section_number=gap['section'],
        main_instructor__isnull=False
    ).select_related('course', 'main_instructor')
    
    # Check each course to see if we can add this slot
    best_course = None
    best_instructor = None
    
    for assignment in assignments:
        course = assignment.course
        instructor = assignment.main_instructor
        
        # Skip special courses and LABs
        if course.course_number in ['TRAINING', 'SPORTS_LIBRARY', 'COUNS', 'SPORT', 'COUNSELING']:
            continue
        if course.course_type == 'LAB':
            continue
        
        # Check if instructor is free at this time
        conflicting = TimetableEntry.objects.filter(
            instructor=instructor,
            meeting_time=meeting_time
        ).exists()
        
        if not conflicting:
            # Check if section has this instructor free
            section_conflicting = TimetableEntry.objects.filter(
                year=gap['year_id'],
                section_number=gap['section'],
                meeting_time=meeting_time
            ).exists()
            
            if not section_conflicting:
                # This course could be scheduled here
                current_entries = TimetableEntry.objects.filter(
                    course=course,
                    section_number=gap['section'],
                    batch='FULL'
                ).count()
                
                # Prefer courses with fewer scheduled hours (more flexible)
                if best_course is None:
                    best_course = course
                    best_instructor = instructor
                
                print(f"  Could schedule: {course.course_number} with {instructor.name}")
    
    # Add the best course to fill this gap
    if best_course:
        year_obj = Year.objects.get(id=gap['year_id'])
        timetable = GeneratedTimetable.objects.first()  # Get the current timetable
        
        new_entry = TimetableEntry.objects.create(
            timetable=timetable,
            year=year_obj,
            section_number=gap['section'],
            course=best_course,
            instructor=best_instructor,
            meeting_time=meeting_time,
            batch='FULL',
            is_evaluator=False
        )
        print(f"  ✓ FILLED with: {best_course.course_number} - {best_instructor.name}")
        filled_count += 1
    else:
        print(f"  ✗ Could not find suitable course to fill this gap")

print("\n" + "="*80)
print(f"FILLED {filled_count} out of {len(gaps_to_fill)} gaps")
print("="*80 + "\n")
