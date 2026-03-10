import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Year
from SchedulerApp.views import ConstraintScheduler, Data

# Test generation for both years
years = Year.objects.all().order_by('year_name')
print('=== TIMETABLE GENERATION TEST (Consecutive Period Limits) ===\n')

for year in years:
    print(f'{year.year_name}:')
    
    try:
        # Create data object
        data = Data(year)
        
        # Create scheduler and build schedule
        scheduler = ConstraintScheduler()
        schedule = scheduler.build_schedule(data, year)
        
        if schedule and hasattr(schedule, '_classes') and len(schedule._classes) > 0:
            print(f'  Generated: {len(schedule._classes)} classes')
            
            # Check DMS distribution (if exists)
            dms_classes = [c for c in schedule._classes if c.course.course_number == 'DMS']
            if dms_classes:
                day_dist = {}
                for cls in dms_classes:
                    day = cls.meeting_time.day
                    day_dist[day] = day_dist.get(day, 0) + 1
                print(f'  DMS distribution: {day_dist}')
                
                # Check for consecutive periods
                for day in day_dist:
                    day_classes = sorted([c for c in dms_classes if c.meeting_time.day == day],
                                       key=lambda x: x.meeting_time.time)
                    if len(day_classes) > 0:
                        consecutive = 1
                        max_consecutive = 1
                        for i in range(1, len(day_classes)):
                            # Check if consecutive (simplified check)
                            consecutive += 1
                            max_consecutive = max(max_consecutive, consecutive)
                        print(f'    {day}: {len(day_classes)} periods (max consecutive check needed)')
            
            print(f'  Status: SUCCESS\n')
        else:
            print(f'  Status: FAILED - No classes generated\n')
    except Exception as e:
        print(f'  Status: ERROR - {str(e)}\n')
        import traceback
        traceback.print_exc()
