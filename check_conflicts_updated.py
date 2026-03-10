import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, Year, MeetingTime
from django.db.models import Count

print("=" * 80)
print("TIMETABLE CONFLICT ANALYSIS")
print("=" * 80)

# Check for conflicts in each year
for year in Year.objects.all():
    print(f"\n{'='*80}")
    print(f"Year: {year.year_name}")
    print(f"{'='*80}")
    
    # Check for same time slot conflicts (multiple courses at same time)
    conflicts = TimetableEntry.objects.filter(year=year).values(
        'section_number', 'meeting_time', 'batch'
    ).annotate(count=Count('id')).filter(count__gt=1)
    
    if conflicts:
        print(f"\n[WARNING] CONFLICTS FOUND: {len(conflicts)} time slots with overlapping courses")
        for conflict in conflicts[:10]:  # Show first 10
            section = conflict['section_number']
            mt_id = conflict['meeting_time']
            batch = conflict['batch']
            count = conflict['count']
            
            mt = MeetingTime.objects.get(pid=mt_id)
            entries = TimetableEntry.objects.filter(
                year=year, 
                section_number=section, 
                meeting_time=mt,
                batch=batch
            )
            
            print(f"\n  Section {section}, Batch {batch}, {mt.day} {mt.time} - {count} courses:")
            for entry in entries:
                room = entry.lab_room if entry.lab_room else "No room"
                instructor = entry.instructor if entry.instructor else "No instructor"
                print(f"    - {entry.course.course_name} ({instructor}) in {room}")
    else:
        print(f"\n[OK] No time slot conflicts found")
    
    # Check professional electives distribution
    pe_courses = TimetableEntry.objects.filter(
        year=year, 
        course__course_name__icontains='professional elective'
    ).order_by('section_number', 'meeting_time__day', 'meeting_time__time')
    
    if pe_courses.exists():
        print(f"\n📚 PROFESSIONAL ELECTIVES DISTRIBUTION:")
        
        # Group by section and day
        for section in [1, 2, 3]:
            section_pe = pe_courses.filter(section_number=section)
            if section_pe.exists():
                print(f"\n  Section {section}:")
                day_counts = {}
                for entry in section_pe:
                    day = entry.meeting_time.day
                    if day not in day_counts:
                        day_counts[day] = []
                    day_counts[day].append(f"{entry.course.course_name} at {entry.meeting_time.time}")
                
                for day, courses in day_counts.items():
                    print(f"    {day}: {len(courses)} periods")
                    for course in courses:
                        print(f"      - {course}")
                
                # Check if all on same day
                if len(day_counts) == 1:
                    print(f"    [WARNING] All professional electives are on {list(day_counts.keys())[0]}!")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
