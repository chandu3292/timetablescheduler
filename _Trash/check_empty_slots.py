import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, MeetingTime
from collections import defaultdict

print("\n" + "="*80)
print("CHECKING FOR EMPTY SLOTS (VISUAL GAPS) IN TIMETABLES")
print("="*80)

sections_to_check = [
    (12, 3, "2nd Year Section 3"),
    (13, 1, "3rd Year Section 1"),
    (13, 3, "3rd Year Section 3")
]

time_slots = ['8:45 - 9:45', '9:45 - 10:35', '10:35 - 11:25', '11:25 - 12:15',
              '1:05 - 1:55', '1:55 - 2:45', '2:45 - 3:35']
days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

for year_id, section_num, section_name in sections_to_check:
    print(f"\n{section_name}:")
    print("="*80)
    
    # Get all entries for this section
    entries = TimetableEntry.objects.filter(
        year=year_id,
        section_number=section_num,
        batch='FULL'
    ).select_related('course', 'meeting_time')
    
    # Create timetable grid
    timetable = defaultdict(lambda: defaultdict(str))
    for entry in entries:
        day = entry.meeting_time.day
        time = entry.meeting_time.time
        timetable[day][time] = entry.course.course_number
    
    # Count empty slots per day
    empty_slots_by_day = defaultdict(list)
    
    for day in days:
        print(f"\n{day}:")
        for time in time_slots:
            if timetable[day][time]:
                print(f"  {time}: {timetable[day][time]}")
            else:
                print(f"  {time}: --- EMPTY ---")
                empty_slots_by_day[day].append(time)
    
    # Summary of empty slots
    total_empty = sum(len(slots) for slots in empty_slots_by_day.values())
    print(f"\n{'='*80}")
    print(f"Total empty slots: {total_empty}")
    if total_empty > 0:
        print(f"Empty slots by day:")
        for day in days:
            if empty_slots_by_day[day]:
                print(f"  {day}: {len(empty_slots_by_day[day])} empty slots")

print("\n" + "="*80 + "\n")
