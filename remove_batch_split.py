"""
REMOVE BATCH-SPLIT LAB SYSTEM
==============================
This script removes batch splitting and converts all labs to full-section mode.
This simplifies scheduling significantly.
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Course, LabBatchAssignment, TimetableEntry

print("="*80)
print("REMOVING BATCH-SPLIT LAB SYSTEM")
print("="*80)

# Step 1: Find all batch-split courses
batch_courses = Course.objects.filter(split_into_batches=True)
print(f"\nFound {batch_courses.count()} batch-split courses:")
for course in batch_courses:
    print(f"  - {course.course_name} ({course.course_number})")
    print(f"    Current: split_into_batches=True")
    print(f"    Will change to: split_into_batches=False")

# Step 2: Clear existing timetables
print("\n" + "-"*80)
print("Clearing existing timetables...")
entry_count = TimetableEntry.objects.count()
TimetableEntry.objects.all().delete()
print(f"Deleted {entry_count} timetable entries")

# Step 3: Delete all LabBatchAssignments
print("\n" + "-"*80)
print("Deleting batch assignments...")
batch_count = LabBatchAssignment.objects.count()
LabBatchAssignment.objects.all().delete()
print(f"Deleted {batch_count} batch assignments")

# Step 4: Update courses to disable batch splitting
print("\n" + "-"*80)
print("Converting courses to full-section mode...")
updated = 0
for course in batch_courses:
    course.split_into_batches = False
    course.save()
    updated += 1
    print(f"  ✓ {course.course_name}: Now full-section lab")

print(f"\nUpdated {updated} courses")

# Step 5: Verify
print("\n" + "="*80)
print("VERIFICATION")
print("="*80)
remaining_batch_courses = Course.objects.filter(split_into_batches=True).count()
remaining_batch_assignments = LabBatchAssignment.objects.count()

print(f"\nCourses with split_into_batches=True: {remaining_batch_courses}")
print(f"Remaining batch assignments: {remaining_batch_assignments}")

if remaining_batch_courses == 0 and remaining_batch_assignments == 0:
    print("\n✅ SUCCESS! Batch-split system completely removed.")
    print("\nAll labs are now full-section mode.")
    print("You can regenerate timetables with: python generate_sequential.py")
else:
    print("\n⚠️  WARNING: Some batch data remains!")

print("\n" + "="*80)
print("NEXT STEPS")
print("="*80)
print("\n1. Regenerate timetables:")
print("   python generate_sequential.py")
print("\n2. Verify generation is faster:")
print("   - 3rd year should complete on 1st attempt")
print("   - No batch assignment complexity")
print("\n3. Benefits:")
print("   - Simpler scheduling (no B1/B2 coordination)")
print("   - Faster generation (less complexity)")
print("   - Fewer instructor conflicts")
print("   - But: Full section in lab instead of half")
