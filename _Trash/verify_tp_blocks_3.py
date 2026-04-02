import os
import sys
import django
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from SchedulerApp.models import Year, TIME_SLOTS
from SchedulerApp.views import ConstraintScheduler, Data

try:
    year = Year.objects.get(year_name='3rd Year')
    scheduler = ConstraintScheduler()
    year_data = Data(year)
    year_data.elective_time_tracker = {}

    schedule = scheduler.build_schedule(year_data, year)

    classes = schedule.getClasses()

    section_tp = {}

    for cls in classes:
        # According to standard python format used in this project
        course = cls.course
        course_type = course.course_type
        
        if course_type == 'TP':
            sec_id = cls.section.section_id
            day = cls.meeting_time.day
            time_str = cls.meeting_time.time
            
            if sec_id not in section_tp:
                section_tp[sec_id] = {}
            if day not in section_tp[sec_id]:
                section_tp[sec_id][day] = []
                
            section_tp[sec_id][day].append(time_str)

    with open('FINAL_TP_CHECK_RESULT.txt', 'w', encoding='utf-8') as f:
        f.write("--- 3RD YEAR TP COURSES CONTINUITY CHECK ---\n")
        if not section_tp:
            f.write("No TP courses were found/scheduled.\n")
        
        for sec, days in sorted(section_tp.items()):
            f.write(f"\nSection {sec}:\n")
            for day, times in days.items():
                sorted_times = sorted(times, key=lambda t: [i for i, v in enumerate(TIME_SLOTS) if v[0] == t][0])
                f.write(f"  {day}:\n")
                for time_str in sorted_times:
                    f.write(f"    - {time_str}\n")
                    
    print("SUCCESS: See FINAL_TP_CHECK_RESULT.txt")

except Exception as e:
    with open('FINAL_TP_CHECK_RESULT.txt', 'w', encoding='utf-8') as f:
        f.write("ERROR OCCURRED:\n")
        f.write(traceback.format_exc())
    print("FAILED: See FINAL_TP_CHECK_RESULT.txt")
