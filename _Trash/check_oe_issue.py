import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Course, CourseInstructorAssignment, TimetableEntry, GeneratedTimetable, MeetingTime

# Check course details
course = Course.objects.filter(course_number='23IT6121').first()
if course:
    print(f"Course: {course.course_number} - {course.course_name}")
    print(f"Course Type: {course.course_type}")
    print(f"Hours per week: {course.hours_per_week}")
    print(f"Max continuous hours: {course.max_continuous_hours}")
    print(f"Split into batches: {course.split_into_batches}")
    print(f"Instructors: {[str(i) for i in course.instructors.all()]}")
else:
    print("Course 23IT6121 not found")

# Check course assignments
print("\n--- COURSE ASSIGNMENTS ---")
assignments = CourseInstructorAssignment.objects.filter(course__course_number='23IT6121')
print(f"Assignments for this course: {assignments.count()}")
for a in assignments:
    instructors = [str(i) for i in a.instructors.all()]
    print(f"  - Year: {a.year}, Section: {a.section_number}, Main Instructor: {a.main_instructor}, All Instructors: {instructors}")

# Check timetable entries for this course
print("\n--- TIMETABLE ENTRIES ---")
timetables = GeneratedTimetable.objects.all()
print(f"Total generated timetables: {timetables.count()}")

entries = TimetableEntry.objects.filter(course__course_number='23IT6121').select_related('meeting_time', 'year', 'course', 'instructor')
print(f"Total timetable entries for 23IT6121: {entries.count()}")

for entry in entries:
    batch_info = f" [{entry.batch}]" if entry.batch != 'FULL' else ""
    role = " (Evaluator)" if entry.is_evaluator else ""
    print(f"  - Year: {entry.year}, Section: {entry.section_number}{batch_info}, Day: {entry.meeting_time.day}, Time: {entry.meeting_time.time}, Instructor: {entry.instructor}{role}")

# Check if same time slot is used across sections
print("\n--- TIME SLOTS ANALYSIS ---")
time_slots = {}
for entry in entries:
    key = (entry.meeting_time.day, entry.meeting_time.time)
    if key not in time_slots:
        time_slots[key] = []
    time_slots[key].append({
        'section': entry.section_number,
        'batch': entry.batch,
        'instructor': str(entry.instructor),
        'role': 'Evaluator' if entry.is_evaluator else 'Main'
    })

print("\nTime slot conflicts (same time across sections):")
for slot, entries_list in sorted(time_slots.items()):
    day, time = slot
    if len(entries_list) > 1:
        sections = [f"Sec{e['section']} ({e['instructor']})" for e in entries_list]
        print(f"  CONFLICT: {day} {time} → {', '.join(sections)}")
