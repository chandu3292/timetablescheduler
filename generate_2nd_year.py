import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Year, GeneratedTimetable, TimetableEntry
from SchedulerApp.views import ConstraintScheduler, Data

print('=== GENERATING 2ND YEAR TIMETABLE ===\n')

second_year = Year.objects.filter(year_name__icontains='2').first()
if second_year:
    # Clear existing if any
    TimetableEntry.objects.filter(year=second_year).delete()
    GeneratedTimetable.objects.filter(year=second_year).delete()
    
    data = Data(second_year)
    scheduler = ConstraintScheduler()
    schedule = scheduler.build_schedule(data, second_year)
    
    if schedule and hasattr(schedule, '_classes'):
        # Save to database
        gen_tt = GeneratedTimetable.objects.create(
            year=second_year,
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
        
        print(f'SUCCESS: {len(schedule._classes)} classes saved for 2nd Year')
        print(f'Fitness: {schedule.getFitness():.2f}%')
    else:
        print('FAILED: Could not generate 2nd Year timetable')
