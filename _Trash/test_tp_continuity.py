import os
import django
import sys
import codecs

sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.views import initialize_data, initialize_population, check_instructor_availability

data = initialize_data()

year_data = {
    'courses': data.get_course(),
    'instructors': data.get_instructor(), 
    'meeting_times': data.get_meetingTime(),
    'sections': [s for s in data.get_section() if s.year == 3]
}

# The scheduler requires years as a form parameter for the UI, but under the hood:
class DummyScheduler:
    from SchedulerApp.views import build_schedule, _schedule_theory_course, _schedule_theory_course_relaxed, _has_consecutive_violation
    build_schedule = build_schedule
    _schedule_theory_course = _schedule_theory_course
    _schedule_theory_course_relaxed = _schedule_theory_course_relaxed
    _has_consecutive_violation = _has_consecutive_violation

scheduler = DummyScheduler()
pop = initialize_population(scheduler, year_data, 3)
schedule = pop.get_schedules()[0]

# Now let's extract the TP courses and their times
print("\n--- 3RD YEAR TP COURSES CONTINUITY CHECK ---")
classes = schedule.get_classes()
section_tp = {}

for cls in classes:
    if cls.course.course_type == 'TP':
        sec = cls.section.section_id
        day = cls.meeting_time.day
        time = cls.meeting_time.time
        
        if sec not in section_tp:
            section_tp[sec] = {}
        if day not in section_tp[sec]:
            section_tp[sec][day] = []
            
        section_tp[sec][day].append(time)

for sec, days in sorted(section_tp.items()):
    print(f"\nSection {sec}:")
    for day, times in days.items():
        print(f"  {day}:")
        for time in times:
            print(f"    - {time}")
