import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from SchedulerApp.models import GeneratedTimetable, TimetableEntry, Year

print("Generated Timetables in Database:")
print("="*60)
for gt in GeneratedTimetable.objects.all().order_by('year__id'):
    entries = TimetableEntry.objects.filter(timetable=gt).count()
    print(f"{gt.year.year_name:12} | Entries: {entries:3} | Fitness: {gt.fitness_score:6.2%} | Generated: {gt.generated_at}")

print("\n" + "="*60)
print("Total generated:", GeneratedTimetable.objects.count())
