import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Year, GeneratedTimetable, TimetableEntry
from SchedulerApp.views import ConstraintScheduler, Data

print('=== REGENERATING ALL TIMETABLES ===\n')

# Clear existing timetables
TimetableEntry.objects.all().delete()
GeneratedTimetable.objects.all().delete()
print('Cleared existing timetables\n')

# Generate for each year
for year in Year.objects.all().order_by('id'):
    print(f'{year.year_name}...', end=' ')
    
    try:
        data = Data(year)
        scheduler = ConstraintScheduler()
        schedule = scheduler.build_schedule(data, year)
    except Exception as e:
        print(f'ERROR: {type(e).__name__}: {e}')
        import traceback
        traceback.print_exc()
        continue
    
    if schedule and hasattr(schedule, '_classes'):
        # Create timetable record
        gen_tt = GeneratedTimetable.objects.create(
            year=year,
            fitness_score=schedule.getFitness(),
            generation_count=0
        )
        
        # Save all classes
        for cls in schedule._classes:
            TimetableEntry.objects.create(
                timetable=gen_tt,
                year=cls.year,
                section_number=cls.section_number,
                course=cls.course,
                instructor=cls.instructor,
                meeting_time=cls.meeting_time,
                lab_room=cls.room,
                batch=getattr(cls, 'batch', 'FULL')  # Include batch info for split labs
            )
        
        print(f'✓ {len(schedule._classes)} classes saved')
        
        # Show distribution for one theory course as sample
        theory_classes = [c for c in schedule._classes if c.course.course_type == 'THEORY']
        if theory_classes:
            sample_course = theory_classes[0].course.course_number
            sample_section = theory_classes[0].section_number
            sample_classes = [c for c in theory_classes if c.course.course_number == sample_course and c.section_number == sample_section]
            
            day_dist = {}
            for cls in sample_classes:
                day = cls.meeting_time.day
                day_dist[day] = day_dist.get(day, 0) + 1
            
            days_used = len(day_dist)
            max_per_day = max(day_dist.values()) if day_dist else 0
            print(f'  Sample: {sample_course} Sec{sample_section} → {days_used} days, max {max_per_day}/day')
    else:
        print('FAILED')
    print()

print('=== VERIFICATION ===')
all_entries = TimetableEntry.objects.all()
print(f'Total classes saved: {all_entries.count()}')

# Check for conflicts
from collections import defaultdict
room_time = defaultdict(list)
inst_time = defaultdict(list)
section_time = defaultdict(list)

for entry in all_entries:
    if entry.lab_room:
        key = (entry.lab_room.lab_name, entry.meeting_time.day, entry.meeting_time.time, entry.batch)
        room_time[key].append(f'{entry.course.course_number} {entry.year.year_name} S{entry.section_number} {entry.batch}')
    if entry.instructor:
        key = (entry.instructor.uid, entry.meeting_time.day, entry.meeting_time.time)
        inst_time[key].append(f'{entry.course.course_number} {entry.year.year_name} S{entry.section_number} {entry.batch}')
    # Section conflict only if same batch (different batches can be parallel)
    key = (entry.year.id, entry.section_number, entry.meeting_time.day, entry.meeting_time.time, entry.batch)
    section_time[key].append(entry.course.course_number)

room_conflicts = sum(1 for v in room_time.values() if len(v) > 1)
inst_conflicts = sum(1 for v in inst_time.values() if len(v) > 1)
section_conflicts = sum(1 for v in section_time.values() if len(v) > 1)

print(f'Room conflicts: {room_conflicts}')
print(f'Instructor conflicts: {inst_conflicts}')
print(f'Section conflicts: {section_conflicts}')

if room_conflicts == 0 and inst_conflicts == 0 and section_conflicts == 0:
    print('\n✓✓✓ PERFECT! Zero conflicts with improved day spreading! ✓✓✓')
else:
    print('\n⚠️ Some conflicts found')
