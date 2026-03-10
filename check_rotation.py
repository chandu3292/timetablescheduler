import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import LabBatchAssignment, Year

print("=" * 80)
print("BATCH ASSIGNMENT CONFIGURATION - CHECKING ROTATION")
print("=" * 80)

third_year = Year.objects.filter(year_name__icontains='3').first()
if third_year:
    print(f"\n3rd Year - Section 1:")
    print("-" * 80)
    batches = LabBatchAssignment.objects.filter(
        year=third_year,
        section_number=1
    ).order_by('session_number', 'course__course_name', 'batch')
    
    print(f"\nSession 1:")
    session1 = batches.filter(session_number=1)
    for b in session1:
        paired = b.paired_course.course_name if b.paired_course else "None"
        print(f"  {b.batch}: {b.course.course_name} (paired with {paired})")
    
    print(f"\nSession 2:")
    session2 = batches.filter(session_number=2)
    for b in session2:
        paired = b.paired_course.course_name if b.paired_course else "None"
        print(f"  {b.batch}: {b.course.course_name} (paired with {paired})")
    
    print("\n" + "=" * 80)
    print("CORRECT ROTATION SHOULD BE:")
    print("=" * 80)
    print("\nSession 1 (same time):")
    print("  B1: IoT Lab")
    print("  B2: Cryptography Lab")
    print("\nSession 2 (same time):")
    print("  B1: Cryptography Lab")
    print("  B2: IoT Lab")
    print("\nCURRENT CONFIGURATION:")
    print("Session 1: " + ", ".join([f"{b.batch}={b.course.course_name}" for b in session1]))
    print("Session 2: " + ", ".join([f"{b.batch}={b.course.course_name}" for b in session2]))
    print("\n⚠️  WARNING: If B1 and B2 have the SAME course in the same session,")
    print("   they will conflict! Proper rotation requires SWAPPING.")
