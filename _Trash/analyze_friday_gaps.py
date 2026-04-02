import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, MeetingTime, CourseInstructorAssignment, Course, Year, GeneratedTimetable

print("\n" + "="*80)
print("ANALYZING REMAINING WEEKDAY GAPS")
print("="*80)

# Define the gaps
gaps_to_analyze = [
    {
        'year_id': 12,
        'section': 3,
        'section_name': '2nd Year Section 3',
        'day': 'Friday',
        'time': '1:05 - 1:55'
    },
    {
        'year_id': 13,
        'section': 3,
        'section_name': '3rd Year Section 3',
        'day': 'Friday',
        'time': '10:35 - 11:25'
    }
]

for gap in gaps_to_analyze:
    print(f"\n{gap['section_name']} - {gap['day']} {gap['time']}")
    print("-" * 80)
    
    # Get meeting time
    meeting_time = MeetingTime.objects.get(
        day=gap['day'], 
        time=gap['time'],
        year=gap['year_id']
    )
    
    # Check what courses are available
    assignments = CourseInstructorAssignment.objects.filter(
        year=gap['year_id'],
        section_number=gap['section'],
        main_instructor__isnull=False
    ).select_related('course', 'main_instructor')
    
    print(f"Checking {assignments.count()} course assignments...")
    
    available_courses = []
    
    for assignment in assignments:
        course = assignment.course
        instructor = assignment.main_instructor
        
        # Skip special courses
        if course.course_number in ['TRAINING', 'SPORTS_LIBRARY', 'COUNS', 'SPORT', 'COUNSELING']:
            continue
        if course.course_type == 'LAB':
            continue
        
        # Check instructor availability
        instructor_conflict = TimetableEntry.objects.filter(
            instructor=instructor,
            meeting_time=meeting_time
        ).exists()
        
        if instructor_conflict:
            conflicting = TimetableEntry.objects.get(
                instructor=instructor,
                meeting_time=meeting_time
            )
            print(f"  ✗ {course.course_number} - Instructor {instructor.name} busy with {conflicting.course.course_number} ({conflicting.year.year_name} Sec{conflicting.section_number})")
            continue
        
        # Check section availability
        section_conflict = TimetableEntry.objects.filter(
            year=gap['year_id'],
            section_number=gap['section'],
            meeting_time=meeting_time
        ).exists()
        
        if section_conflict:
            print(f"  ✗ {course.course_number} - Section already has class at this time")
            continue
        
        # Check current schedule for this course
        current_hours = TimetableEntry.objects.filter(
            course=course,
            year=gap['year_id'],
            section_number=gap['section'],
            batch='FULL'
        ).count()
        
        # Check consecutive hours on this day
        friday_entries = TimetableEntry.objects.filter(
            course=course,
            year=gap['year_id'],
            section_number=gap['section'],
            meeting_time__day=gap['day']
        ).order_by('meeting_time__time')
        
        friday_count = friday_entries.count()
        
        available_courses.append({
            'course': course,
            'instructor': instructor,
            'required_hours': course.hours_per_week,
            'current_hours': current_hours,
            'friday_hours': friday_count,
            'max_continuous': course.max_continuous_hours
        })
        
        print(f"  ✓ {course.course_number} - {instructor.name} (has {current_hours}/{course.hours_per_week} hrs, {friday_count} on Friday, max_continuous={course.max_continuous_hours})")
    
    print(f"\nFound {len(available_courses)} available courses")
    
    # Analyze why gap exists
    if len(available_courses) == 0:
        print("\n⚠️ REASON FOR GAP: All instructors are busy at this time!")
        print("   This is an instructor availability constraint - cannot fill this gap.")
    else:
        print(f"\n✅ CAN FILL GAP with {len(available_courses)} possible courses")
        # Show best candidate
        best = min(available_courses, key=lambda x: x['friday_hours'])
        print(f"   Best candidate: {best['course'].course_number} ({best['instructor'].name})")
        print(f"   - Currently has {best['friday_hours']} periods on Friday")
        print(f"   - Max continuous allowed: {best['max_continuous']}")

print("\n" + "="*80)
