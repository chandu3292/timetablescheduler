import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Year, Course, CourseInstructorAssignment
from SchedulerApp.views import Data, ConstraintScheduler, Schedule

class DebugScheduler(ConstraintScheduler):
    def test_single(self, schedule, section, course, meeting_time, instructor, year):
        # Check section conflicts 
        for cls in schedule._classes:
            if cls.section_number == section and cls.year == year and cls.meeting_time.pid == meeting_time.pid:
                if cls.course != course:
                    print(f"  Fail: Section {section} already has {cls.course.course_number} at {meeting_time.day} {meeting_time.time}")
                    return False

        # === Check instructor conflicts
        if instructor:
            for cls in schedule._classes:
                if cls.instructor == instructor and cls.meeting_time.pid == meeting_time.pid:
                    if cls.course != course or cls.section_number != section:
                        print(f"  Fail: Instructor {instructor.name} already teaching {cls.course.course_number} Sec {cls.section_number} at {meeting_time.day} {meeting_time.time}")
                        return False

            from SchedulerApp.models import TimetableEntry
            existing_entries = TimetableEntry.objects.filter(
                instructor=instructor,
                meeting_time__day=meeting_time.day,
                meeting_time__time=meeting_time.time
            ).exclude(timetable__year=year)
            for entry in existing_entries:
                print(f"  Fail: Instructor DB conflict - {instructor.name} teaching {entry.course.course_number} for {entry.year.year_name} at {meeting_time.day} {meeting_time.time}")
                return False

        # Check max continuous hours for instructor
        if instructor:
            continuous_count = 1
            pid_int = int(meeting_time.pid)
            
            # Count back
            current_pid = pid_int - 1
            while current_pid >= 0:
                has_class = False
                for cls in schedule._classes:
                    if cls.instructor == instructor and int(cls.meeting_time.pid) == current_pid:
                        has_class = True
                        break
                if not has_class:
                    existing = TimetableEntry.objects.filter(
                        instructor=instructor, meeting_time__pid=str(current_pid)
                    ).exclude(timetable__year=year)
                    if existing.exists():
                        has_class = True
                
                if has_class:
                    continuous_count += 1
                    current_pid -= 1
                else:
                    break
            
            # Count forward
            current_pid = pid_int + 1
            while current_pid <= 100:
                has_class = False
                for cls in schedule._classes:
                    if cls.instructor == instructor and int(cls.meeting_time.pid) == current_pid:
                        has_class = True
                        break
                if not has_class:
                    existing = TimetableEntry.objects.filter(
                        instructor=instructor, meeting_time__pid=str(current_pid)
                    ).exclude(timetable__year=year)
                    if existing.exists():
                        has_class = True
                        
                if has_class:
                    continuous_count += 1
                    current_pid += 1
                else:
                    break
                    
            if continuous_count > 3:  # Hardcoded max continuous for instructor
                print(f"  Fail: Instructor {instructor.name} would exceed 3 continuous hours at {meeting_time.day} {meeting_time.time}")
                return False

        return True

scheduler = DebugScheduler()
y = Year.objects.get(year_name='3rd Year')
data = Data(y)
course = Course.objects.get(course_number='23TP9104')
for section in [1, 2, 3]:
    assignment = CourseInstructorAssignment.objects.filter(course=course, section_number=section).first()
    if not assignment: continue
    instructor = assignment.instructors.first()

    print(f"--------------------------------------------------")
    print(f"Testing for course {course.course_number} Sec {section}, instructor {instructor.name}")
    blocks = scheduler._find_continuous_blocks(data, 2, instructor, y)

    # Let's create an empty schedule
    schedule = Schedule()

    for block in blocks:
        can_schedule = True
        for mt in block:
            if not scheduler.test_single(schedule, section, course, mt, instructor, y):
                can_schedule = False
        if can_schedule:
            print(f"SUCCESS! Found valid empty-schedule block: {[mt.time for mt in block]} on {block[0].day}")
            break
    print(f"Total blocks available: {len(blocks)}")
