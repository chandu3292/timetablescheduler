import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Course, CourseInstructorAssignment, TimetableEntry, MeetingTime

# Get the course
course = Course.objects.filter(course_number='23IT6121').first()

print("=" * 70)
print("COURSE 23IT6121 - OE (THEORY) ISSUE ANALYSIS")
print("=" * 70)

print(f"\n1. COURSE DEFINITION:")
print(f"   - Course Number: {course.course_number}")
print(f"   - Course Name: {course.course_name}")
print(f"   - Course Type: {course.course_type} ✓ (Correctly set as THEORY)")
print(f"   - Hours per week: {course.hours_per_week}")
print(f"   - Max continuous hours: {course.max_continuous_hours}")
print(f"   - Instructors assigned globally: {[str(i) for i in course.instructors.all()]}")

print(f"\n2. SECTION ASSIGNMENTS:")
assignments = CourseInstructorAssignment.objects.filter(course__course_number='23IT6121')
for a in assignments:
    instructors = list(a.instructors.all())
    print(f"   Section {a.section_number}:")
    print(f"      - Main Instructor: {a.main_instructor}")
    print(f"      - Assigned Instructors: {[str(i) for i in instructors]}")

print(f"\n3. THE CONFLICT - SAME TIME SLOTS ACROSS SECTIONS:")
entries = TimetableEntry.objects.filter(course__course_number='23IT6121').select_related('meeting_time')
time_slots = {}

for entry in entries:
    key = (entry.meeting_time.day, entry.meeting_time.time)
    if key not in time_slots:
        time_slots[key] = []
    time_slots[key].append({
        'section': entry.section_number,
        'instructor': str(entry.instructor)
    })

print(f"\n   All 4 hours scheduled at SAME TIME across all 3 sections:")
for (day, time_slot), entries_list in sorted(time_slots.items()):
    sections = [f"Sec{e['section']} ({e['instructor']})" for e in entries_list]
    print(f"      {day:10} {time_slot:15} → {', '.join(sections)}")

print(f"\n4. ROOT CAUSE ANALYSIS:")
print(f"   Problem 1: Section 2 & 3 share the SAME instructor (IT23 Ms B keerthana)")
print(f"             When one instructor teaches multiple sections, they can't be at")
print(f"             the same time! This is a HARD CONSTRAINT VIOLATION.")
print(f"")
print(f"   Problem 2: Even Section 1 (different instructor) is at the same time.")
print(f"             This might be acceptable IF designed as 'combined lecture' sessions")
print(f"             BUT with same instructor for Sec 2 & 3, it creates a physical")
print(f"             impossibility.")

print(f"\n5. WHAT SHOULD HAPPEN:")
print(f"   Since both Section 2 and Section 3 are taught by IT23 Ms B keerthana,")
print(f"   they MUST be at different times. For example:")
print(f"      - Section 1: [any schedule]")
print(f"      - Section 2 & 3: Must be spread into different time slots")
print(f"")
print(f"   OR if this is meant as 'combined sections', then Section 2 & 3")
print(f"   should be merged into one course entry in the database.")

print("\n" + "=" * 70)
