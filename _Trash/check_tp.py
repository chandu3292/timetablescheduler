import os
import django
import sys
import codecs

sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Schedule, Section, Course
from SchedulerApp.views import _generate_empty_timetable

print("Removing all schedules and regenerating...")
Schedule.objects.all().delete()
_generate_empty_timetable()
print("Success! Schedules regenerated")

tp_courses = Course.objects.filter(course_type='TP')
print(f"Found {tp_courses.count()} TP courses")

sections = Section.objects.all()

for section in sections:
    print(f"\nSection {section.section_id}:")
    tp_schedules = Schedule.objects.filter(section=section, course__course_type='TP').order_by('day', 'meeting_time')
    day_schedules = {}
    for sch in tp_schedules:
        day_schedules.setdefault(sch.day, []).append(sch)
        
    for day, schs in day_schedules.items():
        times = [s.meeting_time.time for s in schs]
        print(f"  {day}: {times} for course {schs[0].course.course_number}")
