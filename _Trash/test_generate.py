#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from SchedulerApp.models import *
from SchedulerApp.views import ConstraintScheduler, Data, MAX_ATTEMPTS, logger
import logging

logging.basicConfig(level=logging.INFO)

# Clear old timetables
TimetableEntry.objects.all().delete()
GeneratedTimetable.objects.all().delete()

# Test generation for all 4 years
results = {}
for year in Year.objects.all().order_by('id'):
    print(f"\n{'='*60}")
    print(f"Testing: {year.year_name}")
    print(f"{'='*60}")
    
    scheduler = ConstraintScheduler()
    year_data = Data(year)
    year_data.elective_time_tracker = {}
    
    schedule = scheduler.build_schedule(year_data, year)
    
    if schedule:
        alloc_report = schedule.get_allocation_report()
        print(f"✓ {year.year_name} GENERATED")
        print(f"  Classes: {len(schedule.getClasses())}")
        print(f"  Allocation: {alloc_report['total_delivered']}/{alloc_report['total_needed']} hours")
        print(f"  Complete: {alloc_report['complete']} / Incomplete: {alloc_report['incomplete_count']}")
        
        if alloc_report['incomplete_list']:
            print(f"  Under-allocated courses:")
            for item in alloc_report['incomplete_list'][:5]:  # Show first 5
                print(f"    - {item['course']} Sec{item['section']}: {item['got']}/{item['need']} hours")
        
        results[year.year_name] = 'SUCCESS'
    else:
        print(f"✗ {year.year_name} FAILED to generate")
        results[year.year_name] = 'FAILED'

print(f"\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")
for year_name, status in results.items():
    print(f"{year_name}: {status}")
