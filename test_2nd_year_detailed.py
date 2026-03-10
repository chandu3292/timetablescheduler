import os
import django
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Year, TimetableEntry, GeneratedTimetable
from SchedulerApp.views import ConstraintScheduler, Data
import logging

# Configure logging to show everything
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    stream=sys.stdout,
    force=True
)

# Also configure the SchedulerApp.views logger specifically
views_logger = logging.getLogger('SchedulerApp.views')
views_logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
views_logger.addHandler(handler)

print('=== DETAILED 2ND YEAR GENERATION TEST ===\n')

# Clear any existing 2nd year timetable
second_year = Year.objects.filter(year_name__icontains='2').first()
if second_year:
    TimetableEntry.objects.filter(year=second_year).delete()
    GeneratedTimetable.objects.filter(year=second_year).delete()
    
    print(f'Testing: {second_year.year_name}\n')
    print('='*80)
    
    data = Data(second_year)
    scheduler = ConstraintScheduler()
    schedule = scheduler.build_schedule(data, second_year)
    
    if schedule:
        print('\n' + '='*80)
        print(f'SUCCESS: {len(schedule._classes)} classes generated')
        print(f'Fitness: {schedule.getFitness():.2f}%')
    else:
        print('\n' + '='*80)
        print('GENERATION FAILED - check logs above for which course failed')
