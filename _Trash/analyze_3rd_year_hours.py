#!/usr/bin/env python
"""
Analyze 3rd Year course hours: scheduled vs required by section
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from SchedulerApp.models import TimetableEntry, Course, Year
from django.db.models import Count
from collections import defaultdict

# Get 3rd year
try:
    year = Year.objects.get(year_name__icontains='3')
    print(f"Found Year: {year}\n")
except Year.DoesNotExist:
    print("No 3rd year found")
    sys.exit(1)

# Get all courses for 3rd year
courses = year.courses.all().order_by('course_number')
print(f"Total courses in 3rd year: {courses.count()}")

# Build data structure: course -> section -> hours_scheduled
course_data = defaultdict(lambda: defaultdict(int))
required_hours = {}

# Query TimetableEntry for all 3rd year courses
for course in courses:
    required_hours[course.course_number] = course.hours_per_week
    
    # Count entries by section_number
    entries = TimetableEntry.objects.filter(
        course=course,
        year=year
    ).values('section_number').annotate(count=Count('id'))
    
    for entry in entries:
        section = entry['section_number']
        count = entry['count']
        course_data[course.course_number][section] = count

# Print analysis
print("\n" + "="*110)
print(f"{'Course':<20} {'Course#':<15} {'Section':<10} {'Scheduled Hrs':<18} {'Required Hrs':<15} {'Gap':<10}")
print("="*110)

for course_num in sorted(required_hours.keys()):
    course_obj = course = Course.objects.get(course_number=course_num)
    req_hrs = required_hours[course_num]
    
    # Find which sections have entries
    sections_with_entries = sorted(course_data[course_num].keys()) if course_data[course_num] else []
    
    if sections_with_entries:
        for i, section in enumerate(sections_with_entries):
            scheduled_hrs = course_data[course_num][section]
            gap = scheduled_hrs - req_hrs
            gap_str = f"{gap:+d}" if gap != 0 else "0"
            
            course_name_display = course_obj.course_name if i == 0 else ""
            course_num_display = course_num if i == 0 else ""
            
            print(f"{course_name_display:<20} {course_num_display:<15} {section:<10} {scheduled_hrs:<18} {req_hrs:<15} {gap_str:<10}")
    else:
        # No entries for this course
        print(f"{course_obj.course_name:<20} {course_num:<15} {'N/A':<10} {'0':<18} {req_hrs:<15} {'-'+str(req_hrs):<10}")

print("="*110)

# Specific analysis for OE (23IT6121)
print("\n\nDETAILED OE (23IT6121) ANALYSIS:")
print("="*70)

try:
    oe_course = Course.objects.get(course_number='23IT6121')
    print(f"Course: {oe_course.course_name} ({oe_course.course_number})")
    print(f"Required hours/week: {oe_course.hours_per_week}")
    print(f"Course type: {oe_course.course_type}")
    
    # Count entries by section_number
    oe_entries = TimetableEntry.objects.filter(
        course=oe_course,
        year=year
    ).values('section_number').annotate(count=Count('id')).order_by('section_number')
    
    print(f"\nScheduled entries by section:")
    total_entries = 0
    for entry in oe_entries:
        section = entry['section_number']
        count = entry['count']
        gap = count - oe_course.hours_per_week
        gap_str = f" (Gap: {gap:+d})" if gap != 0 else " (OK)"
        print(f"  Section {section}: {count} hours/week (Required: {oe_course.hours_per_week}){gap_str}")
        total_entries += count
    
    # Check if all sections have entries
    all_sections_in_timetable = TimetableEntry.objects.filter(
        year=year
    ).values_list('section_number', flat=True).distinct()
    all_sections_in_timetable = sorted(set(all_sections_in_timetable))
    
    print(f"\nAll sections in timetable: {all_sections_in_timetable}")
    
    oe_sections = set(oe_entries.values_list('section_number', flat=True))
    missing_sections = set(all_sections_in_timetable) - oe_sections
    if missing_sections:
        print(f"WARNING: OE not scheduled for sections: {sorted(missing_sections)}")
    
except Course.DoesNotExist:
    print("OE (23IT6121) not found in database")

# Summary statistics
print("\n\nSUMMARY BY SECTION:")
print("="*70)

section_totals = defaultdict(lambda: {'scheduled': 0, 'required': 0})

for course_num in course_data.keys():
    req_hrs = required_hours[course_num]
    for section in course_data[course_num].keys():
        scheduled = course_data[course_num][section]
        section_totals[section]['scheduled'] += scheduled
        section_totals[section]['required'] += req_hrs

for section in sorted(section_totals.keys()):
    data = section_totals[section]
    diff = data['scheduled'] - data['required']
    status = "OK" if diff == 0 else "DEFICIT" if diff < 0 else "EXCESS"
    print(f"Section {section}: Scheduled {data['scheduled']} hrs / Required {data['required']} hrs (Diff: {diff:+d}) [{status}]")
