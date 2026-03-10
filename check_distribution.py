import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Year
from SchedulerApp.views import ConstraintScheduler, Data

print('=== FULL DISTRIBUTION REPORT ===\n')

for year_name in ['1st Year', '2nd Year']:
    year = Year.objects.get(year_name=year_name)
    data = Data(year)
    scheduler = ConstraintScheduler()
    schedule = scheduler.build_schedule(data, year)
    
    if not schedule:
        print(f'{year_name}: FAILED\n')
        continue
    
    print(f'{year_name}: {len(schedule._classes)} classes generated')
    
    # Get theory courses only
    theory_classes = [c for c in schedule._classes if c.course.course_type == 'THEORY']
    
    # Group by course and section
    course_sections = {}
    for cls in theory_classes:
        key = (cls.course.course_number, cls.section_number)
        if key not in course_sections:
            course_sections[key] = []
        course_sections[key].append(cls)
    
    # Check distribution for each course/section
    poor_distribution = []
    for (course_num, sec), classes in course_sections.items():
        course = classes[0].course
        
        # Count periods per day
        day_dist = {}
        for cls in classes:
            day = cls.meeting_time.day
            day_dist[day] = day_dist.get(day, 0) + 1
        
        max_per_day = max(day_dist.values()) if day_dist else 0
        days_used = len(day_dist)
        
        # Flag if too many periods on one day
        if max_per_day > 2:
            poor_distribution.append((course_num, sec, len(classes), days_used, max_per_day))
    
    if poor_distribution:
        print('  ⚠️ Courses with >2 periods on one day:')
        for course_num, sec, total, days, max_pd in poor_distribution:
            print(f'    {course_num} Sec{sec}: {total} periods across {days} days (max {max_pd}/day)')
    else:
        print('  ✓ All theory courses well-distributed across days!')
    
    print()
