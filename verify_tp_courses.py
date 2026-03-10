import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, Course

tp_courses = ['23TP9102', '23TP9103', '23TP9104', '23TP09104', '23TP19104']

print('TP COURSES VERIFICATION')
print('=' * 100)
print()

for course_num in tp_courses:
    try:
        course = Course.objects.get(course_number=course_num)
        print(f'{course_num} - {course.course_name}')
        print(f'  Configuration:')
        print(f'    Type: {course.course_type}')
        print(f'    Hours/week: {course.hours_per_week}')
        print(f'    Max continuous hours: {course.max_continuous_hours}')
        print(f'    Lab rooms assigned: {list(course.lab_rooms.all())}')
        
        entries = TimetableEntry.objects.filter(course=course).select_related('year', 'meeting_time', 'lab_room')
        
        if entries.exists():
            print(f'  Scheduled entries: {entries.count()}')
            print(f'  Sample entries:')
            
            # Check continuity by grouping by year, section, day
            from collections import defaultdict
            grouped = defaultdict(list)
            
            for e in entries:
                key = (e.year.year_name, e.section_number, e.meeting_time.day)
                grouped[key].append(e.meeting_time.time)
            
            for (year, section, day), times in list(grouped.items())[:3]:
                lab_entry = entries.filter(year__year_name=year, section_number=section, meeting_time__day=day).first()
                print(f'    {year} Sec{section} | {day} {times} | Lab_room: {lab_entry.lab_room or "None"}')
                
                # Check if continuous
                if len(times) == 2:
                    print(f'      ✓ 2 continuous hours scheduled')
                else:
                    print(f'      ⚠ {len(times)} hours on this day (expected 2 continuous)')
        else:
            print(f'  ⚠ Not scheduled yet')
        
        print()
        
    except Course.DoesNotExist:
        print(f'{course_num} - ⚠ DOES NOT EXIST in database')
        print()

print('=' * 100)
print('\nSUMMARY:')
print('✓ TP courses should have:')
print('  - Type: THEORY (not LAB)')
print('  - Hours/week: 2')
print('  - Max continuous hours: 2')  
print('  - Lab rooms: [] (empty)')
print('  - Scheduled with 2 continuous hours WITHOUT lab rooms')
