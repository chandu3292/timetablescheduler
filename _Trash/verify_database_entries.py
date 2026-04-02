import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, MeetingTime

print("\n" + "="*80)
print("VERIFYING DATABASE ENTRIES FOR FRIDAY GAPS")
print("="*80)

# Check 2nd Year Section 3 - Friday 1:05-1:55
print("\n2nd Year Section 3 - Friday 1:05-1:55:")
print("-" * 80)
entries = TimetableEntry.objects.filter(
    year__id=12,
    section_number=3,
    meeting_time__day='Friday',
    meeting_time__time='1:05 - 1:55'
).select_related('course', 'instructor', 'meeting_time')

if entries.exists():
    for entry in entries:
        print(f"✅ Database has: {entry.course.course_number} - {entry.instructor.name}")
        print(f"   Entry ID: {entry.id}")
        print(f"   Timetable ID: {entry.timetable.id}")
        print(f"   Batch: {entry.batch}")
        print(f"   Is Evaluator: {entry.is_evaluator}")
else:
    print("❌ No entry found in database!")

# Check 3rd Year Section 3 - Friday 10:35-11:25
print("\n3rd Year Section 3 - Friday 10:35-11:25:")
print("-" * 80)
entries = TimetableEntry.objects.filter(
    year__id=13,
    section_number=3,
    meeting_time__day='Friday',
    meeting_time__time='10:35 - 11:25'
).select_related('course', 'instructor', 'meeting_time')

if entries.exists():
    for entry in entries:
        print(f"✅ Database has: {entry.course.course_number} - {entry.instructor.name}")
        print(f"   Entry ID: {entry.id}")
        print(f"   Timetable ID: {entry.timetable.id}")
        print(f"   Batch: {entry.batch}")
        print(f"   Is Evaluator: {entry.is_evaluator}")
else:
    print("❌ No entry found in database!")

# Check ALL Friday entries for 2nd Year Section 3
print("\n\nALL Friday entries for 2nd Year Section 3:")
print("-" * 80)
all_friday = TimetableEntry.objects.filter(
    year__id=12,
    section_number=3,
    meeting_time__day='Friday'
).select_related('course', 'instructor', 'meeting_time').order_by('meeting_time__time')

for entry in all_friday:
    print(f"{entry.meeting_time.time}: {entry.course.course_number} - {entry.instructor.name}")

# Check ALL Friday entries for 3rd Year Section 3
print("\n\nALL Friday entries for 3rd Year Section 3:")
print("-" * 80)
all_friday = TimetableEntry.objects.filter(
    year__id=13,
    section_number=3,
    meeting_time__day='Friday'
).select_related('course', 'instructor', 'meeting_time').order_by('meeting_time__time')

for entry in all_friday:
    print(f"{entry.meeting_time.time}: {entry.course.course_number} - {entry.instructor.name}")

print("\n" + "="*80)
print("SUGGESTION: If entries exist in database but not showing in view,")
print("please REFRESH the timetable view page in your browser (Ctrl+F5)")
print("="*80 + "\n")
