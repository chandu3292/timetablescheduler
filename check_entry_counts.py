import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, Year

print("=" * 80)
print("TIMETABLE ENTRY COUNTS")
print("=" * 80)

for year in Year.objects.all().order_by('id'):
    count = TimetableEntry.objects.filter(year=year).count()
    status = "[OK]" if count > 0 else "[EMPTY]"
    print(f"{status} {year.year_name}: {count} entries")
