"""
Disable batch splitting for all courses.
Set split_into_batches=False for all courses.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Course

print("="*80)
print("DISABLING BATCH SPLITTING FOR ALL COURSES")
print("="*80)

courses = Course.objects.all()
updated = 0

for course in courses:
    if course.split_into_batches:
        print(f"  {course.course_number}: Disabling batch splitting")
        course.split_into_batches = False
        course.save()
        updated += 1
    else:
        print(f"  {course.course_number}: Already not split")

print(f"\nUpdated {updated} courses")
print("\n" + "="*80)
print("DONE!")
print("="*80)
