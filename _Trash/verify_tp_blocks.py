import os
import sys
import django
import codecs

sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from SchedulerApp.models import Year, TimetableEntry, GeneratedTimetable, TIME_SLOTS
from SchedulerApp.views import ConstraintScheduler, Data

# Just test the 3rd year
year = Year.objects.get(year_name='3rd Year')
print(f"Generating for {year.year_name}...")

scheduler = ConstraintScheduler()
year_data = Data(year)
year_data.elective_time_tracker = {}

schedule = scheduler.build_schedule(year_data, year)

print("\n--- 3RD YEAR TP COURSES CONTINUITY CHECK ---")
classes = schedule.getClasses()
section_tp = {}

for cls in classes:
    if cls.getCourse().course_type == 'TP':
        sec = cls.getSection().section_id
        day = cls.getMeetingTime().day
        time = cls.getMeetingTime().time
        
        if sec not in section_tp:
            section_tp[sec] = {}
        if day not in section_tp[sec]:
            section_tp[sec][day] = []
            
        section_tp[sec][day].append(time)

for sec, days in sorted(section_tp.items()):
    print(f"\nSection {sec}:")
    for day, times in days.items():
        # sort times by standard slots
        sorted_times = sorted(times, key=lambda t: [i for i, v in enumerate(TIME_SLOTS) if v[0] == t][0])
        print(f"  {day}:")
        for time in sorted_times:
            print(f"    - {time}")
