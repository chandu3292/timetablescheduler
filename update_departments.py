"""
Auto-populate department codes for Courses and Instructors
based on course numbers and instructor assignments.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Course, Instructor
import re

def extract_dept_from_course_code(course_number):
    """
    Extract department code from course number.
    Examples:
    - 23IT4215 → IT
    - 23EC3201 → EC
    - 23ME4105 → ME
    - 23MA1107 → MA (Mathematics)
    - 23PY1102 → PY (Physics)
    - 23TP9102 → TP (Training & Placement)
    - 23MC0104 → MC (Multi-disciplinary/Communication)
    """
    match = re.search(r'^\d{2}([A-Z]{2})', course_number)
    if match:
        return match.group(1)
    return None

print("="*80)
print("UPDATING COURSE DEPARTMENT CODES")
print("="*80)

courses = Course.objects.all()
updated_courses = 0

for course in courses:
    dept = extract_dept_from_course_code(course.course_number)
    if dept:
        course.dept_code = dept
        course.save()
        print(f"  {course.course_number}: {dept}")
        updated_courses += 1
    else:
        print(f"  {course.course_number}: Could not determine department")

print(f"\nUpdated {updated_courses} courses")

print("\n" + "="*80)
print("UPDATING INSTRUCTOR DEPARTMENT CODES")
print("="*80)
print("(Based on courses they teach)")

from SchedulerApp.models import CourseInstructorAssignment
from collections import Counter

instructors = Instructor.objects.all()
updated_instructors = 0

for instructor in instructors:
    # Find all courses this instructor teaches
    assignments = CourseInstructorAssignment.objects.filter(
        instructors=instructor
    ).select_related('course')
    
    if assignments.exists():
        # Count department occurrences
        dept_counts = Counter()
        for assignment in assignments:
            if assignment.course.dept_code:
                dept_counts[assignment.course.dept_code] += 1
        
        if dept_counts:
            # Assign the most common department
            most_common_dept = dept_counts.most_common(1)[0][0]
            instructor.department = most_common_dept
            instructor.save()
            print(f"  {instructor.name}: {most_common_dept} (teaches {dept_counts[most_common_dept]} {most_common_dept} courses)")
            updated_instructors += 1
        else:
            print(f"  {instructor.name}: No department info from courses")
    else:
        print(f"  {instructor.name}: No course assignments found")

print(f"\nUpdated {updated_instructors} instructors")

print("\n" + "="*80)
print("DEPARTMENT SUMMARY")
print("="*80)

from django.db.models import Count

course_depts = Course.objects.values('dept_code').annotate(count=Count('dept_code')).order_by('-count')
print("\nCourses by Department:")
for dept in course_depts:
    if dept['dept_code']:
        print(f"  {dept['dept_code']}: {dept['count']} courses")

instructor_depts = Instructor.objects.values('department').annotate(count=Count('department')).order_by('-count')
print("\nInstructors by Department:")
for dept in instructor_depts:
    if dept['department']:
        print(f"  {dept['department']}: {dept['count']} instructors")

print("\n" + "="*80)
print("DONE!")
print("="*80)
