#!/usr/bin/env python
"""
Debug database query counting - why does detailed listing show 4 entries but count shows 1?
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from SchedulerApp.models import TimetableEntry, Course, Year, GeneratedTimetable
from django.db.models import Count

# Get 3rd year
year = Year.objects.get(year_name__icontains='3')

# Test with OE course
oe = Course.objects.get(course_number='23IT6121')

print("DEBUGGING DATABASE QUERY")
print("="*80)

# Method 1: Direct count
all_entries = TimetableEntry.objects.filter(course=oe, year=year)
print(f"\nMethod 1 - Direct count all entries:")
print(f"  Total TimetableEntry records: {all_entries.count()}")

# Method 2: Count by section
by_section = all_entries.values('section_number').annotate(count=Count('id'))
print(f"\nMethod 2 - Aggregated by section_number:")
for item in by_section:
    print(f"  Section {item['section_number']}: {item['count']} records")

# Method 3: Show each entry
print(f"\nMethod 3 - List all TimetableEntry records for OE:")
for entry in all_entries.select_related('meeting_time', 'instructor'):
    print(f"  Section {entry.section_number}: {entry.meeting_time.day} {entry.meeting_time.time} - {entry.instructor.name if entry.instructor else 'NO INSTRUCTOR'}")

# Method 4: Check if they're in different timetables
print(f"\nMethod 4 - Check generated timetables:")
timetables = GeneratedTimetable.objects.all()
for tt in timetables:
    entries = TimetableEntry.objects.filter(course=oe, year=year, timetable=tt)
    print(f"  Timetable {tt.year.year_name}: {entries.count()} entries for OE")
    
print(f"\nTimetables entries (all courses):")
for tt in timetables:
    entries = TimetableEntry.objects.filter(year=year, timetable=tt)
    print(f"  Timetable {tt.year.year_name}: {entries.count()} total entries")

# Method 5: Check unique TimetableEntry objects
print(f"\nMethod 5 - Detailed row information for OE:")
for entry in TimetableEntry.objects.filter(course=oe, year=year).select_related('timetable', 'meeting_time', 'instructor').order_by('timetable', 'section_number'):
    print(f"  ID={entry.id:<6} Timetable {entry.timetable.year.year_name} Section={entry.section_number} {entry.meeting_time.day} {entry.meeting_time.time}")

# Compare with DAA which apparently has 4 per section
print("\n\nCompare with DAA (which shows 4 entries visually):")
daa = Course.objects.get(course_number='23IT4121')
daa_entries = TimetableEntry.objects.filter(course=daa, year=year)
print(f"DAA total entries: {daa_entries.count()}")

by_section_daa = daa_entries.values('section_number').annotate(count=Count('id'))
for item in by_section_daa:
    print(f"  Section {item['section_number']}: {item['count']} records")

print(f"\nDAA detailed entries:")
for entry in daa_entries.select_related('timetable', 'meeting_time', 'instructor').order_by('timetable', 'section_number'):
    print(f"  ID={entry.id:<6} Timetable {entry.timetable.year.year_name} Section={entry.section_number} {entry.meeting_time.day} {entry.meeting_time.time[:13]}")
