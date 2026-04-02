#!/usr/bin/env python
"""
Final comprehensive analysis of 3rd Year course hours
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from SchedulerApp.models import TimetableEntry, Course, Year
from django.db.models import Count

year = Year.objects.get(year_name__icontains='3')

print("="*120)
print("3RD YEAR COURSE HOURS ANALYSIS - FINAL REPORT")
print("="*120)

courses_to_check = {
    '23IT4121': 'DAA',
    '23IT4122': 'Cryptography',
    '23IT4221': 'Cryptography Lab',
    '23IT4222': 'IOT Lab',
    '23IT5121': 'PE2',
    '23IT5131': 'PE3',
    '23IT5211': 'Elective Lab',
    '23IT6121': 'OE',
    '23IT9304': 'PySpark',
    '23TP09104': 'AGIS',
    '23TP19104': 'SESD',
    '23TP9104': 'HLR',
}

# Build comprehensive table
data = []
for course_num, course_name in sorted(courses_to_check.items()):
    try:
        course = Course.objects.get(course_number=course_num)
        required = course.hours_per_week
        
        for section in [1, 2, 3]:
            entries = TimetableEntry.objects.filter(
                course=course,
                year=year,
                section_number=section
            ).count()
            
            gap = entries - required
            status = "✓" if gap == 0 else "✗" if gap < 0 else "⚠"
            
            data.append({
                'course_name': course_name,
                'course_num': course_num,
                'section': section,
                'scheduled': entries,
                'required': required,
                'gap': gap,
                'status': status
            })
    except Course.DoesNotExist:
        pass

# Print table
print(f"\n{'Course':<25} {'#':<12} {'Sec':<5} {'Scheduled':<12} {'Required':<12} {'Gap':<8} {'Status':<8}")
print("-" * 120)

current_course = None
for row in data:
    if row['course_name'] != current_course:
        current_course = row['course_name']
        course_display = row['course_name']
    else:
        course_display = ""
    
    course_num_display = row['course_num'] if row['course_name'] != current_course or row['section'] == 1 else ""
    
    print(f"{course_display:<25} {course_num_display:<12} {row['section']:<5} {row['scheduled']:<12} {row['required']:<12} {row['gap']:+3d} {row['status']:<8}")

print("-" * 120)

# Summary by type
print("\n\nSUMMARY BY COURSE TYPE:")
print("="*120)

theory = []
lab = []
other = []

for row in data:
    course_num = row['course_num']
    total_scheduled = sum(r['scheduled'] for r in data if r['course_num'] == course_num)
    total_required = sum(r['required'] for r in data if r['course_num'] == course_num)
    
    if total_scheduled not in [item[0] for item in theory + lab + other]:  # Only add once per course
        try:
            course = Course.objects.get(course_number=course_num)
            if course.course_type == 'THEORY':
                if 'Lab' not in course.course_name:
                    theory.append((course_num, course.course_name, total_scheduled, total_required, total_scheduled - total_required))
                else:
                    lab.append((course_num, course.course_name, total_scheduled, total_required, total_scheduled - total_required))
            else:
                lab.append((course_num, course.course_name, total_scheduled, total_required, total_scheduled - total_required))
        except:
            pass

print("\nTHEORY COURSES (excluding labs):")
print(f"{'Course':<25} {'#':<12} {'Total Hrs/Section':<20} {'Required/Section':<20} {'Gap/Section':<15}")
print("-" * 92)

for course_num, course_name, total_sch, total_req, gap in sorted(theory):
    hrs_per_section_sch = total_sch // 3
    hrs_per_section_req = total_req // 3
    gap_per_section = gap // 3
    
    status = "✓ OK" if gap_per_section == 0 else "✗ CRITICAL" if gap_per_section < 0 else "⚠ EXCESS"
    print(f"{course_name:<25} {course_num:<12} {total_sch:3d} ({hrs_per_section_sch:1d}/sec)       {total_req:3d} ({hrs_per_section_req:1d}/sec)         {gap:+3d} ({gap_per_section:+2d}/sec)  {status}")

print("\n\nLAB COURSES:")
print(f"{'Course':<25} {'#':<12} {'Total Hrs/Section':<20} {'Required/Section':<20} {'Gap/Section':<15}")
print("-" * 92)

for course_num, course_name, total_sch, total_req, gap in sorted(lab):
    hrs_per_section_sch = total_sch // 3 if total_sch > 0 else 0
    hrs_per_section_req = total_req // 3
    gap_per_section = gap // 3
    
    status = "✓ OK" if gap_per_section == 0 else "✗ CRITICAL" if gap_per_section < 0 else "⚠ EXCESS"
    print(f"{course_name:<25} {course_num:<12} {total_sch:3d} ({hrs_per_section_sch:1d}/sec)       {total_req:3d} ({hrs_per_section_req:1d}/sec)         {gap:+3d} ({gap_per_section:+2d}/sec)  {status}")

# Critical findings
print("\n\nCRITICAL FINDINGS:")
print("="*120)

oe = Course.objects.get(course_number='23IT6121')
oe_entries_s1 = TimetableEntry.objects.filter(course=oe, year=year, section_number=1).count()
oe_entries_s2 = TimetableEntry.objects.filter(course=oe, year=year, section_number=2).count()
oe_entries_s3 = TimetableEntry.objects.filter(course=oe, year=year, section_number=3).count()

print(f"\n⚠️ OE (23IT6121) CRITICAL ISSUE:")
print(f"   Section 1: {oe_entries_s1} hour/week (Required: 4) - MISSING {4-oe_entries_s1} hours")
print(f"   Section 2: {oe_entries_s2} hour/week (Required: 4) - MISSING {4-oe_entries_s2} hours")
print(f"   Section 3: {oe_entries_s3} hour/week (Required: 4) - MISSING {4-oe_entries_s3} hours")

print(f"\n⚠️ THEORY COURSES WITH GAPS:")
gaps_found = []
for row in data:
    if row['gap'] < 0:
        course = Course.objects.get(course_number=row['course_num'])
        if course.course_type == 'THEORY' and 'Lab' not in course.course_name:
            gaps_found.append(row)

if gaps_found:
    for row in gaps_found[:5]:
        print(f"   {row['course_name']:<25} Sec {row['section']}: {row['scheduled']} hrs scheduled / {row['required']} hrs required (Gap: {row['gap']:+d})")

print("\n" + "="*120)
print("STATUS: 3RD YEAR TIMETABLE IS SEVERELY UNDER-SCHEDULED")
print("="*120)
