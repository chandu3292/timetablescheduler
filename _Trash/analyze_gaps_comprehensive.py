import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, Course, GeneratedTimetable, Year
from collections import defaultdict

print("\n" + "="*80)
print("GAP ANALYSIS - 2ND AND 3RD YEAR TIMETABLES")
print("="*80)

# Get latest timetables for 2nd and 3rd year
for year_name in ['2nd Year', '3rd Year']:
    year = Year.objects.filter(year_name=year_name).first()
    if not year:
        continue
    
    # Get latest timetable for this year
    timetable = GeneratedTimetable.objects.filter(year=year).order_by('-id').first()
    
    if not timetable:
        print(f"\n{year_name}: No timetable found")
        continue
    
    print(f"\n{'='*80}")
    print(f"{year_name} - Timetable ID: {timetable.id}")
    print(f"Generated: {timetable.generated_at}")
    print(f"{'='*80}")
    
    # Get all courses for this year
    all_courses = Course.objects.filter(year=year).exclude(
        course_number__in=['TRAINING', 'SPORTS_LIBRARY', 'COUNS', 'SPORT', 'COUNSELING']
    )
    
    # For each course and section, check scheduled vs required hours
    gaps_found = []
    sections = [1, 2, 3]
    
    for course in all_courses:
        for section in sections:
            # Count scheduled hours (exclude evaluator entries for labs)
            if course.course_type == 'LAB':
                # For labs, count unique time slots (not instructor entries)
                entries = TimetableEntry.objects.filter(
                    timetable=timetable,
                    course=course,
                    section_number=section
                ).values('meeting_time__day', 'meeting_time__time').distinct()
                scheduled = entries.count()
            else:
                # For theory/elective, count all entries
                scheduled = TimetableEntry.objects.filter(
                    timetable=timetable,
                    course=course,
                    section_number=section,
                    is_evaluator=False
                ).count()
            
            required = course.hours_per_week
            
            if scheduled < required:
                gap = required - scheduled
                gaps_found.append({
                    'course': course.course_number,
                    'name': course.course_name,
                    'type': course.course_type,
                    'section': section,
                    'scheduled': scheduled,
                    'required': required,
                    'gap': gap,
                    'max_per_day': course.max_continuous_hours
                })
    
    if gaps_found:
        print(f"\n❌ GAPS FOUND: {len(gaps_found)} incomplete course-section combinations\n")
        
        # Group by course
        by_course = defaultdict(list)
        for gap_info in gaps_found:
            by_course[gap_info['course']].append(gap_info)
        
        for course_num, gaps in sorted(by_course.items()):
            gap_info = gaps[0]
            print(f"{course_num} - {gap_info['name']} (Type: {gap_info['type']}, Max: {gap_info['max_per_day']} hrs/day)")
            for gap in gaps:
                print(f"  Section {gap['section']}: {gap['scheduled']}/{gap['required']} hours (GAP: {gap['gap']} hours)")
        
        # Summary
        total_gap_hours = sum(g['gap'] for g in gaps_found)
        print(f"\n  Total gap hours: {total_gap_hours}")
        
    else:
        print(f"\n✅ NO GAPS - All courses fully scheduled!")
    
    # Check for over-scheduling (exceeding max per day)
    print(f"\n{'='*80}")
    print(f"DAY LIMIT VIOLATIONS")
    print(f"{'='*80}")
    
    violations = []
    for course in all_courses:
        for section in sections:
            # Get all entries for this course-section
            entries = TimetableEntry.objects.filter(
                timetable=timetable,
                course=course,
                section_number=section,
                is_evaluator=False
            ).select_related('meeting_time')
            
            # Count hours per day
            by_day = defaultdict(int)
            for entry in entries:
                by_day[entry.meeting_time.day] += 1
            
            # Check violations
            for day, hours in by_day.items():
                if hours > course.max_continuous_hours:
                    violations.append({
                        'course': course.course_number,
                        'name': course.course_name,
                        'section': section,
                        'day': day,
                        'hours': hours,
                        'max': course.max_continuous_hours
                    })
    
    if violations:
        print(f"\n❌ {len(violations)} day limit violations found\n")
        for v in violations:
            print(f"  {v['course']} - {v['name']} Section {v['section']}")
            print(f"    {v['day']}: {v['hours']} hours (max: {v['max']}) - EXCEEDS BY {v['hours'] - v['max']}")
    else:
        print(f"\n✅ NO VIOLATIONS - All courses respect max hours per day")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80 + "\n")
