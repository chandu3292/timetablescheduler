import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry
from collections import defaultdict

print("=" * 80)
print("INSTRUCTOR CONFLICT DETAILS")
print("=" * 80)

# Check instructor conflicts
inst_time = defaultdict(list)

for entry in TimetableEntry.objects.all().select_related('instructor', 'meeting_time', 'year', 'course'):
    if entry.instructor:
        key = (entry.instructor.uid, entry.meeting_time.day, entry.meeting_time.time)
        inst_time[key].append(f"{entry.year.year_name} Sec{entry.section_number} - {entry.course.course_name} ({entry.batch})")

# Show conflicts
conflicts = {k: v for k, v in inst_time.items() if len(v) > 1}

if conflicts:
    print(f"\nFound {len(conflicts)} instructor conflicts:\n")
    for (uid, day, time), courses in sorted(conflicts.items()):
        print(f"{uid} on {day} {time}:")
        for course in courses:
            print(f"  - {course}")
        print()
else:
    print("\n[OK] No instructor conflicts!")
