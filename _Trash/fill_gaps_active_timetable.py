import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, MeetingTime, Course, Year, GeneratedTimetable, Instructor

print("\n" + "="*80)
print("FILLING GAPS IN ACTIVE TIMETABLE")
print("="*80)

# Get the most recent timetable with entries
timetables = GeneratedTimetable.objects.all().order_by('-id')
active_timetable = None

for tt in timetables:
    entry_count = TimetableEntry.objects.filter(timetable=tt).count()
    if entry_count > 100:  # Find a properly populated timetable
        active_timetable = tt
        print(f"\nUsing Timetable ID {tt.id} with {entry_count} entries")
        break

if not active_timetable:
    print("❌ No active timetable found!")
    exit(1)

# Define gaps to fill
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
    
    # Check if already filled
    existing = TimetableEntry.objects.filter(
        timetable=active_timetable,
        year__id=gap['year_id'],
        section_number=gap['section'],
        meeting_time__day=gap['day'],
        meeting_time__time=gap['time']
    ).exists()
    
    if existing:
        entry = TimetableEntry.objects.get(
            timetable=active_timetable,
            year__id=gap['year_id'],
            section_number=gap['section'],
            meeting_time__day=gap['day'],
            meeting_time__time=gap['time']
        )
        print(f"ℹ️ Already filled with: {entry.course.course_number} - {entry.instructor.name}")
        continue
    
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
        
        # Create entry
        new_entry = TimetableEntry.objects.create(
            timetable=active_timetable,
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
        
    except Exception as e:
        print(f"✗ Error: {e}")

print("\n" + "="*80)
print(f"FILLED {filled} gaps in Timetable ID {active_timetable.id}")
print("="*80)
print("\n🔄 Please REFRESH your browser (Ctrl+F5) to see the updates!")
print("="*80 + "\n")
