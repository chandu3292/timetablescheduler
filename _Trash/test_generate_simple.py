#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from SchedulerApp.models import *
from SchedulerApp.views import ConstraintScheduler, Data, MAX_ATTEMPTS
import logging

# Suppress emoji/unicode logging
logging.disable(logging.DEBUG)
logging.disable(logging.INFO)
logging.disable(logging.WARNING)

# Clear old timetables
TimetableEntry.objects.all().delete()
GeneratedTimetable.objects.all().delete()

# Test generation for all 4 years
results = {}
for year in Year.objects.all().order_by('id'):
    print(f"\nTesting: {year.year_name}")
    
    try:
        scheduler = ConstraintScheduler()
        year_data = Data(year)
        year_data.elective_time_tracker = {}
        
        schedule = scheduler.build_schedule(year_data, year)
        
        if schedule:
            alloc_report = schedule.get_allocation_report()
            print(f"  GENERATED: {len(schedule.getClasses())} classes")
            print(f"  Allocation: {alloc_report['total_delivered']}/{alloc_report['total_needed']} hours")
            print(f"  Complete: {alloc_report['complete']} / Incomplete: {alloc_report['incomplete_count']}")
            
            if alloc_report['incomplete_list']:
                print(f"  Under-allocated:")
                for item in alloc_report['incomplete_list'][:3]:
                    print(f"    - {item['course']} Sec{item['section']}: {item['got']}/{item['need']} hours")
            
            results[year.year_name] = 'SUCCESS'
        else:
            print(f"  FAILED to generate")
            results[year.year_name] = 'FAILED'
    except Exception as e:
        print(f"  ERROR: {e}")
        results[year.year_name] = f'ERROR: {str(e)[:50]}'

print(f"\n{'='*60}")
print("FINAL SUMMARY")
print(f"{'='*60}")
for year_name, status in results.items():
    print(f"{year_name}: {status}")

# Verify what was saved
from SchedulerApp.models import GeneratedTimetable
print(f"\nDatabase saved: {GeneratedTimetable.objects.count()} timetables")
