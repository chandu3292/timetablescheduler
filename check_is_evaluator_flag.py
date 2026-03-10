import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, Course

print("Checking is_evaluator flag in database...")
print("="*80)

# Check DBMS Lab (23IT4215) Section 1
lab = Course.objects.filter(course_number='23IT4215').first()
entries = TimetableEntry.objects.filter(course=lab, section_number=1).select_related('instructor').order_by('meeting_time__time')[:9]

print("\n23IT4215 (DBMS Lab) - Section 1 - First 9 entries:")
for e in entries:
    print(f"  {e.meeting_time.time}: {e.instructor.name if e.instructor else 'N/A'} - is_evaluator={e.is_evaluator}")

# Count by is_evaluator
main_count = entries.filter(is_evaluator=False).count()
eval_count = entries.filter(is_evaluator=True).count()

print(f"\nSummary for this lab session:")
print(f"  Main instructors (is_evaluator=False): {main_count}")
print(f"  Evaluators (is_evaluator=True): {eval_count}")
print(f"  Total entries: {entries.count()}")

if main_count == 3 and eval_count == 6:
    print("\n[OK] Correctly saved: 3 main entries + 6 evaluator entries")
elif main_count == 9 and eval_count == 0:
    print("\n[ERROR] All marked as main instructors - is_evaluator flag not working!")
else:
    print(f"\n[WARNING] Unexpected distribution")

print("\n" + "="*80)
