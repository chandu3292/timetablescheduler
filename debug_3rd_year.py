import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import (
    Year, Course, CourseInstructorAssignment, 
    LabBatchAssignment, MeetingTime, LabRoom
)

print("\n=== DEBUGGING 3RD YEAR GENERATION ===\n")

# Get 3rd year
year_3 = Year.objects.get(year_name__icontains='3')
print(f"Year: {year_3.year_name}\n")

# Check courses
courses = Course.objects.filter(year=year_3)
print(f"Courses: {courses.count()}")
theory_courses = courses.filter(course_type='THEORY')
lab_courses = courses.filter(course_type='LAB')
elective_courses = courses.filter(course_type='ELECTIVE')
print(f"  Theory: {theory_courses.count()}")
print(f"  Lab: {lab_courses.count()}")
print(f"  Elective: {elective_courses.count()}")

#Check instructor assignments
assignments = CourseInstructorAssignment.objects.filter(year=year_3)
print(f"\nInstructor Assignments: {assignments.count()}")
theory_assignments = assignments.filter(course__course_type='THEORY')
elective_assignments = assignments.filter(course__course_type='ELECTIVE')
print(f"  Theory: {theory_assignments.count()}")
print(f"  Elective: {elective_assignments.count()}")

if assignments.count() == 0:
    print("  ⚠️ NO INSTRUCTOR ASSIGNMENTS FOR 3RD YEAR!")
else:
    for assignment in assignments:
        instructors = assignment.instructors.all()
        print(f"  - {assignment.course.course_name}: {[i.name for i in instructors]}")

# Check lab batch assignments
lab_batches = LabBatchAssignment.objects.filter(year=year_3)
print(f"\nLab Batch Assignments: {lab_batches.count()}")

if lab_batches.count() == 0:
    print("  ⚠️ NO LAB BATCH ASSIGNMENTS FOR 3RD YEAR!")

# Check meeting times
meeting_times = MeetingTime.objects.filter(year=year_3)
print(f"\nMeeting Times: {meeting_times.count()}")
if meeting_times.count() == 0:
    print("  ⚠️ NO MEETING TIMES FOR 3RD YEAR!")

# Summary
print("\n=== SUMMARY ===")
if assignments.count() == 0:
    print("❌ PROBLEM: No instructor assignments for 3rd year theory/elective courses")
    print("   Generation cannot proceed without instructor assignments!")
if lab_batches.count() == 0:
    print("❌ PROBLEM: No lab batch assignments for 3rd year lab courses")
    print("   Generation cannot proceed without lab batch assignments!")
if meeting_times.count() == 0:
    print("❌ PROBLEM: No meeting times for 3rd year")
    print("   Generation cannot proceed without meeting times!")
for room in lab_rooms:
    print(f"  - {room.room_number}")
