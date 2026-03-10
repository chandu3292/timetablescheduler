import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Year, MeetingTime
from SchedulerApp.views import ConstraintScheduler, Data, TIME_SLOTS

def check_consecutive_periods(classes, day):
    """Check for consecutive periods on a specific day"""
    # Build time order from TIME_SLOTS
    time_order = [t[0] for t in TIME_SLOTS]
    
    # Sort by time
    sorted_classes = sorted(classes, key=lambda x: time_order.index(x.meeting_time.time) if x.meeting_time.time in time_order else 999)
    
    if not sorted_classes:
        return 0
    
    max_consecutive = 1
    current_consecutive = 1
    
    for i in range(1, len(sorted_classes)):
        try:
            prev_idx = time_order.index(sorted_classes[i-1].meeting_time.time)
            curr_idx = time_order.index(sorted_classes[i].meeting_time.time)
            
            if curr_idx == prev_idx + 1:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 1
        except ValueError:
            # Time not in order, treat as non-consecutive
            current_consecutive = 1
    
    return max_consecutive

print('=== VERIFICATION: Consecutive Period Limits ===\n')

years = Year.objects.filter(year_name__in=['1st Year', '2nd Year'])

for year in years:
    print(f'{year.year_name}:')
    
    data = Data(year)
    scheduler = ConstraintScheduler()
    schedule = scheduler.build_schedule(data, year)
    
    if not schedule or not hasattr(schedule, '_classes'):
        print('  FAILED - No schedule generated\n')
        continue
    
    # Group by section and course
    section_courses = {}
    for cls in schedule._classes:
        key = (cls.section_number, cls.course.course_number)
        if key not in section_courses:
            section_courses[key] = []
        section_courses[key].append(cls)
    
    # Check each course's consecutive periods
    violations = []
    for (section, course_num), classes in section_courses.items():
        # Get the course's max_continuous_hours limit
        course = classes[0].course
        max_continuous = course.max_continuous_hours if course.max_continuous_hours > 0 else 999
        
        # Group by day
        day_groups = {}
        for cls in classes:
            day = cls.meeting_time.day
            if day not in day_groups:
                day_groups[day] = []
            day_groups[day].append(cls)
        
        # Check consecutive periods for each day
        for day, day_classes in day_groups.items():
            consecutive = check_consecutive_periods(day_classes, day)
            if consecutive > max_continuous:
                violations.append({
                    'section': section,
                    'course': course_num,
                    'day': day,
                    'max_allowed': max_continuous,
                    'actual': consecutive,
                    'total_on_day': len(day_classes)
                })
    
    if violations:
        print('  ⚠️ VIOLATIONS FOUND:')
        for v in violations:
            print(f'    Section {v["section"]}, {v["course"]} on {v["day"]}:')
            print(f'      Max allowed consecutive: {v["max_allowed"]}')
            print(f'      Actual consecutive: {v["actual"]}')
            print(f'      Total periods on day: {v["total_on_day"]}')
    else:
        print('  ✓ No violations - all courses respect max_continuous_hours')
    
    # Show DMS distribution as example (if exists)
    dms_by_section = {key: classes for key, classes in section_courses.items() if key[1] == 'DMS'}
    if dms_by_section:
        print(f'\n  DMS Course Distribution:')
        for (section, course_num), classes in dms_by_section.items():
            day_dist = {}
            for cls in classes:
                day = cls.meeting_time.day
                day_dist[day] = day_dist.get(day, 0) + 1
            
            print(f'    Section {section}: {sum(day_dist.values())} total periods')
            for day, count in sorted(day_dist.items()):
                consecutive = check_consecutive_periods([c for c in classes if c.meeting_time.day == day], day)
                print(f'      {day}: {count} periods (max consecutive: {consecutive})')
    
    print()
