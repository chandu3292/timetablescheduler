import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, GeneratedTimetable, Year
from SchedulerApp.views import ConstraintScheduler, Data

print('=== REGENERATING 2ND AND 3RD YEAR WITH FIXED CODE ===\n')

# Delete old timetables with conflicts
for year_name in ['2nd Year', '3rd Year']:
    year = Year.objects.filter(year_name=year_name).first()
    if year:
        deleted = TimetableEntry.objects.filter(year=year).delete()
        print(f'Deleted {deleted[0]} old entries from {year_name}')
        GeneratedTimetable.objects.filter(year=year).delete()

print('\n' + '='*80)

# Regenerate with fixed code
for year_name in ['3rd Year', '2nd Year']:  # 3rd year first (easier to schedule)
    year = Year.objects.filter(year_name=year_name).first()
    if not year:
        continue
        
    print(f'\nGenerating {year_name}...')
    
    data = Data(year)
    scheduler = ConstraintScheduler()
    schedule = scheduler.build_schedule(data, year)
    
    if schedule and hasattr(schedule, '_classes'):
        gen_tt = GeneratedTimetable.objects.create(
            year=year,
            fitness_score=schedule.getFitness(),
            generation_count=0
        )
        
        for cls in schedule._classes:
            TimetableEntry.objects.create(
                timetable=gen_tt,
                year=cls.year,
                section_number=cls.section_number,
                course=cls.course,
                instructor=cls.instructor,
                meeting_time=cls.meeting_time,
                lab_room=cls.room,
                batch=getattr(cls, 'batch', 'FULL')
            )
        
        print(f'  SUCCESS: {len(schedule._classes)} classes saved')
        print(f'  Fitness: {schedule.getFitness():.2f}%')
    else:
        print(f'  FAILED to generate {year_name}')

print('\n' + '='*80)
print('CHECKING FOR CONFLICTS...')
print('='*80)

# Quick conflict check
from collections import defaultdict
all_entries = TimetableEntry.objects.all()

section_time = defaultdict(list)
for entry in all_entries:
    key = (entry.year.id, entry.section_number, entry.meeting_time.day, entry.meeting_time.time, entry.batch)
    section_time[key].append(entry.course.course_number)

section_conflicts = sum(1 for v in section_time.values() if len(v) > 1)
print(f'\nSection/time conflicts: {section_conflicts}')

if section_conflicts == 0:
    print('\n[SUCCESS] ZERO CONFLICTS!')
else:
    print('\n[WARNING] Still have conflicts - check details')
