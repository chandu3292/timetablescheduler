import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, LabRoom, MeetingTime, Year
from collections import defaultdict

print("=" * 80)
print("LAB ROOM USAGE ANALYSIS")
print("=" * 80)

# Get all lab rooms
lab_rooms = LabRoom.objects.all()
print(f"\nTotal lab rooms: {lab_rooms.count()}")
for lab in lab_rooms:
    print(f"  - {lab.lab_name}")

# Get all meeting times
meeting_times = MeetingTime.objects.all().order_by('day', 'time')
days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

print("\n" + "=" * 80)
print("LAB ROOM AVAILABILITY (FREE SLOTS)")
print("=" * 80)

# Check which labs are used when
for lab in lab_rooms:
    print(f"\n{lab.lab_name}:")
    print("-" * 80)
    
    usage_by_day = defaultdict(list)
    
    # Get all entries using this lab
    entries = TimetableEntry.objects.filter(lab_room=lab).select_related('meeting_time', 'year', 'course')
    
    for entry in entries:
        key = (entry.meeting_time.day, entry.meeting_time.time)
        usage_by_day[key].append(f"{entry.year.year_name} Sec{entry.section_number} - {entry.course.course_name}")
    
    # Show availability by day
    for day in days_order:
        day_times = meeting_times.filter(day=day)
        used_times = [mt.time for mt in day_times if (day, mt.time) in usage_by_day]
        free_times = [mt.time for mt in day_times if (day, mt.time) not in usage_by_day]
        
        if free_times or used_times:
            print(f"\n  {day}:")
            if used_times:
                print(f"    Used ({len(used_times)} slots): {', '.join(used_times[:5])}" + 
                      (" ..." if len(used_times) > 5 else ""))
            if free_times:
                print(f"    FREE ({len(free_times)} slots): {', '.join(free_times[:10])}" + 
                      (" ..." if len(free_times) > 10 else ""))

print("\n" + "=" * 80)
print("CONTINUOUS FREE BLOCKS (3+ hours)")
print("=" * 80)

# Find continuous free blocks for each lab
for lab in lab_rooms:
    print(f"\n{lab.lab_name} - 3+ hour continuous blocks:")
    
    usage_by_day = defaultdict(set)
    entries = TimetableEntry.objects.filter(lab_room=lab).select_related('meeting_time')
    
    for entry in entries:
        usage_by_day[entry.meeting_time.day].add(entry.meeting_time.pid)
    
    for day in days_order:
        day_times = list(meeting_times.filter(day=day).order_by('time'))
        if not day_times:
            continue
        
        # Find continuous free blocks
        free_blocks = []
        current_block = []
        
        for mt in day_times:
            if mt.pid not in usage_by_day[day]:
                current_block.append(mt)
            else:
                if len(current_block) >= 3:
                    free_blocks.append(current_block)
                current_block = []
        
        if len(current_block) >= 3:
            free_blocks.append(current_block)
        
        if free_blocks:
            for i, block in enumerate(free_blocks):
                print(f"  {day} Block {i+1}: {block[0].time} to {block[-1].time} ({len(block)} hours)")

print("\n" + "=" * 80)
print("2ND YEAR LAB REQUIREMENTS")
print("=" * 80)

second_year = Year.objects.filter(year_name__icontains='2').first()
if second_year:
    from SchedulerApp.models import Course
    labs = Course.objects.filter(year=second_year, course_type='LAB').order_by('-max_continuous_hours')
    
    print(f"\nLabs to schedule (3 sections each):")
    for lab in labs:
        print(f"  - {lab.course_name}: {lab.max_continuous_hours} continuous hours")
    
    total_hours = sum(lab.hours_per_week for lab in labs)
    print(f"\nTotal lab hours per section: {total_hours} hours/week")
    print(f"Total for 3 sections: {total_hours * 3} hours/week needed")
