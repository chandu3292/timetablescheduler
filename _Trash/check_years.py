#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Year

print("Available Years in Database:")
years = Year.objects.all()
for year in years:
    print(f"  - ID: {year.id}, Name: '{year.year_name}'")
