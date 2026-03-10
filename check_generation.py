import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, Year

print("=" * 80)
print("TIMETABLE GENERATION SUMMARY")
print("=" * 80)

years = Year.objects.all().order_by('id')

total = 0
for year in years:
    count = TimetableEntry.objects.filter(year=year).count()
    total += count
    print(f"{year.year_name}: {count} classes")

print(f"\nTotal: {total} classes")

print("\n" + "=" * 80)
print("Expected:")
print("  1st Year: ~96 classes")
print("  2nd Year: ~105 classes")
print("  3rd Year: ~117 classes")
print("  Total: ~318 classes")
print("=" * 80)

if total < 300:
    print("\n⚠ WARNING: Generation incomplete!")
    print("Some year(s) failed to generate.")
    print("\nPossible reasons:")
    print("  - 2nd year has tight lab room constraints")
    print("  - Try running generation again (it uses randomization)")
