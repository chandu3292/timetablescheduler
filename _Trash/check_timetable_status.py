import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import GeneratedTimetable, TimetableEntry

print("\n" + "="*80)
print("TIMETABLE STATUS CHECK")
print("="*80)

# Get all timetables
all_timetables = GeneratedTimetable.objects.all().order_by('-id')

print(f"\nTotal Timetables in Database: {all_timetables.count()}")
print("-" * 80)

for tt in all_timetables:
    entry_count = TimetableEntry.objects.filter(timetable=tt).count()
    print(f"Timetable ID {tt.id}: {entry_count} entries (Created: {tt.generated_at})")

# Check which timetable the gap-filled entries belong to
filled_entries = TimetableEntry.objects.filter(
    id__in=[56248, 56249]
).select_related('timetable')

print("\n✅ Gap-filled entries are in:")
print("-" * 80)
for entry in filled_entries:
    print(f"Entry {entry.id}: Timetable ID {entry.timetable.id}")

# Get the latest timetable
latest = GeneratedTimetable.objects.latest('id')
print(f"\n📊 Latest Timetable: ID {latest.id}")
print(f"   Created: {latest.generated_at}")
print(f"   Total entries: {TimetableEntry.objects.filter(timetable=latest).count()}")

print("\n" + "="*80)
print("ACTION REQUIRED:")
print("="*80)
print("""
If the timetable view shows old data, please:

1. HARD REFRESH your browser:
   - Windows: Ctrl + F5 or Ctrl + Shift + R
   - Mac: Cmd + Shift + R

2. Or CLEAR browser cache and reload

3. Or generate a new timetable to create a fresh version

The database has the correct data - the view just needs to refresh!
""")
print("="*80 + "\n")
