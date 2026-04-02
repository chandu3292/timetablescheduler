import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, MeetingTime

print("\n" + "="*80)
print("FIXING MAX CONTINUOUS HOURS VIOLATION")
print("="*80)

# Find the violating entry - 23TP09104 on Wednesday 2:45-3:35 for 3rd Year Sec 1
# This was the gap I filled earlier

violation_entry = TimetableEntry.objects.filter(
    course__course_number='23TP09104',
    year__id=13,
    section_number=1,
    meeting_time__day='Wednesday',
    meeting_time__time='2:45 - 3:35'
).first()

if violation_entry:
    print(f"\nFound violation entry:")
    print(f"  Course: {violation_entry.course.course_number}")
    print(f"  Year: {violation_entry.year.year_name} Section {violation_entry.section_number}")
    print(f"  Time: {violation_entry.meeting_time.day} {violation_entry.meeting_time.time}")
    print(f"  Instructor: {violation_entry.instructor.name}")
    
    # Delete this entry
    violation_entry.delete()
    print(f"\n✅ Deleted violating entry")
    
    # Verify the course still has all required hours
    remaining = TimetableEntry.objects.filter(
        course__course_number='23TP09104',
        year__id=13,
        section_number=1
    ).count()
    
    required = violation_entry.course.hours_per_week
    print(f"\nVerification:")
    print(f"  Required hours: {required}")
    print(f"  Remaining scheduled hours: {remaining}")
    print(f"  Status: {'✅ Still complete' if remaining >= required else '⚠️ Now incomplete'}")
else:
    print("\n⚠️ Violation entry not found")

print("\n" + "="*80)
