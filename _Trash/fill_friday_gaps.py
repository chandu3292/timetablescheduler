import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, MeetingTime, Course, Year, GeneratedTimetable, Instructor

print("\n" + "="*80)
print("FILLING REMAINING FRIDAY GAPS")
print("="*80)

# Define gaps and which course to use
gaps_to_fill = [
    {
        'year_id': 12,
        'section': 3,
        'section_name': '2nd Year Section 3',
        'day': 'Friday',
        'time': '1:05 - 1:55',
        'course_number': '23TP9102',
        'instructor_name': 'jithin kumar'
    },
    {
        'year_id': 13,
        'section': 3,
        'section_name': '3rd Year Section 3',
        'day': 'Friday',
        'time': '10:35 - 11:25',
        'course_number': '23TP09104',
        'instructor_name': 'yogesh bhavana'
    }
]

filled = 0

for gap in gaps_to_fill:
    print(f"\n{gap['section_name']} - {gap['day']} {gap['time']}")
    print("-" * 80)
    
    try:
        # Get objects
        year_obj = Year.objects.get(id=gap['year_id'])
        meeting_time = MeetingTime.objects.get(
            day=gap['day'], 
            time=gap['time'],
            year=gap['year_id']
        )
        course = Course.objects.get(course_number=gap['course_number'])
        instructor = Instructor.objects.get(name=gap['instructor_name'])
        timetable = GeneratedTimetable.objects.first()
        
        # Create entry
        new_entry = TimetableEntry.objects.create(
            timetable=timetable,
            year=year_obj,
            section_number=gap['section'],
            course=course,
            instructor=instructor,
            meeting_time=meeting_time,
            batch='FULL',
            is_evaluator=False
        )
        
        print(f"✅ FILLED with: {course.course_number} - {instructor.name}")
        filled += 1
        
        # Verify
        current_hours = TimetableEntry.objects.filter(
            course=course,
            year=year_obj,
            section_number=gap['section'],
            batch='FULL'
        ).count()
        
        print(f"   Course now has {current_hours} hours scheduled (was {course.hours_per_week} required)")
        
    except Exception as e:
        print(f"✗ Error: {e}")

print("\n" + "="*80)
print(f"FILLED {filled} out of {len(gaps_to_fill)} Friday gaps")
print("="*80 + "\n")
