import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, Course
from collections import defaultdict

print("\n" + "="*80)
print("COMPREHENSIVE MAX HOURS PER DAY VERIFICATION")
print("="*80)

# Get the active timetable
from SchedulerApp.models import GeneratedTimetable
timetables = GeneratedTimetable.objects.all().order_by('-id')
active_timetable = None

for tt in timetables:
    entry_count = TimetableEntry.objects.filter(timetable=tt).count()
    if entry_count > 100:
        active_timetable = tt
        break

print(f"\nAnalyzing Timetable ID: {active_timetable.id} ({TimetableEntry.objects.filter(timetable=active_timetable).count()} entries)")
print("-" * 80)

# Get all THEORY entries (exclude labs and special courses)
theory_entries = TimetableEntry.objects.filter(
    timetable=active_timetable,
    course__course_type='THEORY',
    batch='FULL'  # Only count full section entries
).exclude(
    course__course_number__in=['TRAINING', 'SPORTS_LIBRARY', 'COUNS', 'SPORT', 'COUNSELING']
).select_related('course', 'year', 'meeting_time')

# Group by course-year-section-day
course_day_hours = defaultdict(lambda: defaultdict(list))

for entry in theory_entries:
    key = (entry.course.course_number, entry.year.year_name, entry.section_number, entry.course.course_name)
    day = entry.meeting_time.day
    course_day_hours[key][day].append(entry.meeting_time.time)

# Analyze violations
violations = []
compliant = []

for (course_num, year_name, section, course_name), days in course_day_hours.items():
    course = Course.objects.get(course_number=course_num)
    max_continuous = course.max_continuous_hours
    total_hours = sum(len(times) for times in days.values())
    
    has_violation = False
    for day, times in days.items():
        hours_on_day = len(times)
        
        if hours_on_day > max_continuous:
            violations.append({
                'course': course_num,
                'course_name': course_name,
                'year': year_name,
                'section': section,
                'day': day,
                'hours': hours_on_day,
                'max': max_continuous,
                'excess': hours_on_day - max_continuous,
                'total_weekly': total_hours
            })
            has_violation = True
    
    if not has_violation:
        compliant.append({
            'course': course_num,
            'year': year_name,
            'section': section,
            'max': max_continuous,
            'total_weekly': total_hours
        })

print(f"\n{'='*80}")
print(f"RESULTS SUMMARY")
print(f"{'='*80}\n")

print(f"Total Theory Courses Analyzed: {len(course_day_hours)}")
print(f"✅ Compliant: {len(compliant)} courses ({len(compliant)*100/len(course_day_hours):.1f}%)")
print(f"⚠️ Violations: {len(violations)} violations in {len(set((v['course'], v['year'], v['section']) for v in violations))} courses ({len(violations)*100/len(course_day_hours) if course_day_hours else 0:.1f}%)")

if violations:
    print(f"\n{'='*80}")
    print("⚠️ VIOLATIONS FOUND - COURSES EXCEEDING MAX HOURS PER DAY")
    print(f"{'='*80}\n")
    
    # Sort by excess hours
    violations.sort(key=lambda x: x['excess'], reverse=True)
    
    for v in violations:
        print(f"❌ {v['course']} ({v['course_name']})")
        print(f"   {v['year']} Section {v['section']}")
        print(f"   {v['day']}: {v['hours']} hours (max allowed: {v['max']}) - EXCEEDS BY {v['excess']}")
        print(f"   Total weekly hours: {v['total_weekly']}")
        print()
    
    # Recommendations
    print(f"{'='*80}")
    print("RECOMMENDATIONS")
    print(f"{'='*80}\n")
    print("The system should enforce max_continuous_hours as a strict day limit.")
    print("These violations indicate the constraint is not being properly enforced.")
    print("\nAction Required:")
    print("1. Regenerate the timetable to apply the updated scheduling logic")
    print("2. The new code enforces day limits in all phases (day-filling + gap-filling)")
    print()
    
else:
    print(f"\n{'='*80}")
    print("✅ PERFECT! NO VIOLATIONS FOUND")
    print(f"{'='*80}\n")
    print("All theory courses respect their max_continuous_hours as a day limit!")
    print("Every course stays within its allowed hours per day.")
    print()
    
    # Show some examples
    print("Sample Compliant Courses:")
    print("-" * 80)
    for c in compliant[:10]:
        print(f"  ✓ {c['course']} ({c['year']} Sec{c['section']}): max {c['max']} hrs/day, {c['total_weekly']} hrs/week")

print("\n" + "="*80)
print("VERIFICATION COMPLETE")
print("="*80 + "\n")
