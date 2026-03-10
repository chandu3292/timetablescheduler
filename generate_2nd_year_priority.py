import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, GeneratedTimetable, Year
from SchedulerApp.views import ConstraintScheduler, Data

print("=" * 80)
print("GENERATING 2ND YEAR FIRST (PRIORITY SCHEDULING)")
print("=" * 80)

# Clear ALL timetables to give 2nd year first pick of time slots
print("\nClearing all existing timetables...")
TimetableEntry.objects.all().delete()
GeneratedTimetable.objects.all().delete()
print("  [OK] All timetables cleared")

# Try generating 2nd year multiple times
second_year = Year.objects.filter(year_name__icontains='2').first()
if not second_year:
    print("ERROR: 2nd Year not found!")
    exit(1)

max_attempts = 10
for attempt in range(1, max_attempts + 1):
    print(f"\nAttempt {attempt}/{max_attempts}:")
    
    # Clear 2nd year entries from previous attempt
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
        
        print(f"  [SUCCESS] {len(schedule._classes)} classes saved!")
        print(f"  Fitness: {schedule.getFitness():.2f}%")
        break
    else:
        print(f"  FAILED")
        
        if attempt == max_attempts:
            print(f"\n[ERROR] Failed to generate 2nd year after {max_attempts} attempts")
            print("The constraints are too tight. Consider:")
            print("  - Adding more meeting time slots")
            print("  - Reducing lab hours")
            print("  - Enabling batch splitting for some 2nd year labs")
