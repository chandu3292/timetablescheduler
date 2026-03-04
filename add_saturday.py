#!/usr/bin/env python
"""Add Saturday meeting times for 2nd Year"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Year, MeetingTime, TIME_SLOTS

year = Year.objects.get(id=12)
print(f"Adding Saturday meeting times for {year.year_name}...")

time_slots = [slot[0] for slot in TIME_SLOTS]
count = 0

for time_slot in time_slots:
    pid = f'SAT{count+1}'
    mt, created = MeetingTime.objects.get_or_create(
        pid=pid,
        defaults={
            'year': year,
            'day': 'Saturday',
            'time': time_slot
        }
    )
    if created:
        print(f'  ✓ Created {pid}: Saturday {time_slot}')
        count += 1
    else:
        print(f'  - Already exists: {pid}')

total = MeetingTime.objects.filter(year=year).count()
print(f'\n✓ Total meeting times now: {total}')
print(f'  Days: {sorted(set(mt.day for mt in MeetingTime.objects.filter(year=year)))}')
print(f'\nCapacity check:')
print(f'  Available slots: {total}')
print(f'  Required: 38 hours (13 LAB + 25 THEORY)')
print(f'  Extra capacity: {total - 38} hours ✓')
