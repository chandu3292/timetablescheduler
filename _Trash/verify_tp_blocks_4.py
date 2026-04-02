import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from SchedulerApp.models import Year, TIME_SLOTS
from SchedulerApp.views import ConstraintScheduler, Data
import traceback

try:
    year = Year.objects.get(year_name='3rd Year')
    scheduler = ConstraintScheduler()
    year_data = Data(year)
    year_data.elective_time_tracker = {}

    schedule = scheduler.build_schedule(year_data, year)
    classes = schedule.getClasses()

    section_tp = {}
    
    # Store just the courses that were evaluated
    tp_courses_found = set()

    for cls in classes:
        course = cls.course if hasattr(cls, 'course') else cls.get_course()
        if course.course_type != 'LAB' and course.max_continuous_hours > 1:
            tp_courses_found.add(course.course_number)
            sec_id = cls.section_number
            
            mt = cls.meeting_time if hasattr(cls, 'meeting_time') else cls.get_meetingTime()
            day = mt.day
            time_str = mt.time
            
            if sec_id not in section_tp:
                section_tp[sec_id] = {}
            if day not in section_tp[sec_id]:
                section_tp[sec_id][day] = []
                
            section_tp[sec_id][day].append(time_str)

    with open('FINAL_TP_CHECK_RESULT.txt', 'w', encoding='utf-8') as f:
        f.write("--- 3RD YEAR TP COURSES CONTINUITY CHECK ---\n")
        f.write(f"Identified TP Courses: {list(tp_courses_found)}\n\n")
        
        if not section_tp:
            f.write("No TP courses were found/scheduled.\n")
        
        for sec, days in sorted(section_tp.items()):
            f.write(f"Section {sec}:\n")
            for day, times in days.items():
                # Extract starting time to sort properly
                def get_slot_idx(t):
                    for i, slot in enumerate(TIME_SLOTS):
                        if slot[0] == t:
                            return i
                    return 0
                
                sorted_times = sorted(times, key=get_slot_idx)
                f.write(f"  {day}:\n")
                for time_str in sorted_times:
                    f.write(f"    - {time_str}\n")
            f.write("\n")
                    
    print("SUCCESS: See FINAL_TP_CHECK_RESULT.txt")

except Exception as e:
    with open('FINAL_TP_CHECK_RESULT.txt', 'w', encoding='utf-8') as f:
        f.write("ERROR OCCURRED:\n")
        f.write(traceback.format_exc())
    print("FAILED")
