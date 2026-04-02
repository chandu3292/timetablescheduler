import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import GeneratedTimetable, TimetableEntry

print("\n" + "="*80)
print("RECENT TIMETABLE GENERATION HISTORY")
print("="*80)

# Get last 10 timetables
timetables = GeneratedTimetable.objects.all().order_by('-id')[:10]

for tt in timetables:
    entry_count = TimetableEntry.objects.filter(timetable=tt).count()
    
    status = "✅ SUCCESS" if entry_count > 100 else f"❌ FAILED (only {entry_count} entries)"
    
    print(f"\nID: {tt.id} - {tt.year.year_name}")
    print(f"  Generated: {tt.generated_at}")
    print(f"  Entries: {entry_count}")
    print(f"  Fitness: {tt.fitness_score}")
    print(f"  Status: {status}")

print("\n" + "="*80)
print()
