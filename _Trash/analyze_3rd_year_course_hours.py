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
from django.db.models import Count, Q
from collections import defaultdict

# Get 3rd year
try:
    year = Year.objects.get(year_name__icontains='3')
    print(f"Found Year: {year}")
except Year.DoesNotExist:
    print("No 3rd year found")
    sys.exit(1)

# Get all courses for 3rd year
courses = year.courses.all().order_by('course_number')
print(f"\nTotal courses in 3rd year: {courses.count()}")

# Build data structure: course -> section -> hours_scheduled
course_data = defaultdict(lambda: defaultdict(int))
required_hours = {}

# Query TimetableEntry for all 3rd year courses
for course in courses:
    required_hours[course.course_number] = course.hours_per_week
    
    # Count entries by section
    entries = TimetableEntry.objects.filter(
        course=course,
        semester=semester
    ).values('section').annotate(count=Count('id'))
    
    for entry in entries:
        section = entry['section']
        count = entry['count']
        course_data[course.course_number][section] = count

# Print analysis
print("\n" + "="*100)
print(f"{'Course':<15} {'Number':<12} {'Section':<10} {'Scheduled Hrs':<18} {'Required Hrs':<15} {'Gap':<10}")
print("="*100)

all_sections = set()
for course_num in sorted(course_data.keys()):
    all_sections.update(course_data[course_num].keys())

all_sections = sorted(all_sections)

for course_num in sorted(required_hours.keys()):
    course_obj = courses.get(course_number=course_num)
    req_hrs = required_hours[course_num]
    
    # Find which sections have entries
    sections_with_entries = list(course_data[course_num].keys())
    
    if sections_with_entries:
        for section in sorted(sections_with_entries):
            scheduled_hrs = course_data[course_num][section]
            gap = scheduled_hrs - req_hrs
            gap_str = f"+ {gap}" if gap >= 0 else f"{gap}"
            
            print(f"{course_obj.name:<15} {course_num:<12} {section:<10} {scheduled_hrs:<18} {req_hrs:<15} {gap_str:<10}")
    else:
        # No entries for this course
        print(f"{course_obj.name:<15} {course_num:<12} {'N/A':<10} {'0':<18} {req_hrs:<15} {'-' + str(req_hrs):<10}")

print("="*100)

# Specific analysis for OE (23IT6121)
print("\n\nDETAILED OE (23IT6121) ANALYSIS:")
print("="*60)

try:
    oe_course = Course.objects.get(course_number='23IT6121', semester=semester)
    print(f"Course: {oe_course.name} ({oe_course.course_number})")
    print(f"Required hours/week: {oe_course.hours_per_week}")
    print(f"Course type: {oe_course.course_type}")
    
    # Count entries by section
    oe_entries = TimetableEntry.objects.filter(
        course=oe_course,
        semester=semester
    ).values('section').annotate(count=Count('id'))
    
    print(f"\nScheduled entries by section:")
    for entry in oe_entries.order_by('section'):
        print(f"  Section {entry['section']}: {entry['count']} hours")
    
    # Total entries
    total = sum(e['count'] for e in oe_entries)
    print(f"  Total entries across all sections: {total}")
    
except Course.DoesNotExist:
    print("OE (23IT6121) not found in database")

# Summary statistics
print("\n\nSUMMARY BY SECTION:")
print("="*60)

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
    print(f"Section {section}: Scheduled {data['scheduled']} hrs / Required {data['required']} hrs (Diff: {diff:+d})")
