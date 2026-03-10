import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Year
from SchedulerApp.views import ConstraintScheduler, Data
import logging

# Enable detailed logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print('=== TESTING 2ND YEAR GENERATION ===\n')

second_year = Year.objects.filter(year_name__icontains='2').first()
if second_year:
    print(f'Generating for {second_year.year_name}...\n')
    
    data = Data(second_year)
    scheduler = ConstraintScheduler()
    
    try:
        schedule = scheduler.build_schedule(data, second_year)
        
        if schedule and hasattr(schedule, '_classes'):
            print(f'\nSUCCESS: Generated {len(schedule._classes)} classes')
            print(f'Fitness: {schedule.getFitness():.2f}%')
        else:
            print('\nFAILED: Schedule generation returned None or invalid schedule')
            
    except Exception as e:
        print(f'\nERROR during generation:')
        print(f'{type(e).__name__}: {e}')
        import traceback
        traceback.print_exc()
else:
    print('ERROR: 2nd Year not found!')
