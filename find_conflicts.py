import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry

# Get all entries
all_entries = TimetableEntry.objects.all()

print("Finding instructor conflicts...")
print()

instructor_conflicts = 0
found_conflicts = []

for entry1 in all_entries:
    if entry1.instructor:
        # Find other entries at same time with same instructor
        conflicts_with = all_entries.filter(
            meeting_time=entry1.meeting_time,
            instructor=entry1.instructor
        ).exclude(id=entry1.id)
        
        # Filter out co-teaching entries (same course, section, year)
        real_conflicts = conflicts_with.exclude(
            course=entry1.course,
            section_number=entry1.section_number,
            year=entry1.year
        )
        
        if real_conflicts.exists():
            for entry2 in real_conflicts:
                conflict_key = tuple(sorted([entry1.id, entry2.id]))
                if conflict_key not in found_conflicts:
                    found_conflicts.append(conflict_key)
                    instructor_conflicts += 1
                    print(f"CONFLICT #{instructor_conflicts}:")
                    print(f"  {entry1.instructor.name} teaching:")
                    print(f"    - {entry1.year.year_name} {entry1.course.course_name} Sec{entry1.section_number} Batch:{entry1.batch}")
                    print(f"    - {entry2.year.year_name} {entry2.course.course_name} Sec{entry2.section_number} Batch:{entry2.batch}")
                    print(f"  Time: {entry1.meeting_time.day} {entry1.meeting_time.time}")
                    print()

print(f"Total instructor conflicts: {instructor_conflicts}")
