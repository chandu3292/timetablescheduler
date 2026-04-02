import os
import sys
import django
import codecs
import time

# Ignore logging unicode errors securely
import logging
logging.getLogger().setLevel(logging.CRITICAL)

sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from SchedulerApp.models import Year, TIME_SLOTS
from SchedulerApp.views import ConstraintScheduler, Data

year = Year.objects.get(year_name='3rd Year')
print(f"Generating for {year.year_name}...")

scheduler = ConstraintScheduler()
year_data = Data(year)
year_data.elective_time_tracker = {}

schedule = scheduler.build_schedule(year_data, year)

print("\n--- 3RD YEAR TP COURSES CONTINUITY CHECK ---")
classes = schedule.getClasses() # that's what test_generate.py uses actually it uses schedule.getClasses() wait no scheduler does get_classes()? Let's check view. 

section_tp = {}

for cls in classes:
    # Use proper attributes depending on if it's the internal Class vs Model
    course = getattr(cls, 'course', None) or cls.get_course()
    course_type = course.course_type
    
    if course_type == 'TP':
        sec = getattr(cls, 'section', None) or cls.get_section()
        sec_id = sec.section_id
        
        mt = getattr(cls, 'meeting_time', None) or cls.get_meetingTime()
        day = mt.day
        time_str = mt.time
        
        if sec_id not in section_tp:
            section_tp[sec_id] = {}
        if day not in section_tp[sec_id]:
            section_tp[sec_id][day] = []
            
        section_tp[sec_id][day].append(time_str)

for sec, days in sorted(section_tp.items()):
    print(f"\nSection {sec}:")
    for day, times in days.items():
        # sort times by standard slots
        sorted_times = sorted(times, key=lambda t: [i for i, v in enumerate(TIME_SLOTS) if v[0] == t][0])
        print(f"  {day}:")
        for time_str in sorted_times:
            print(f"    - {time_str}")
