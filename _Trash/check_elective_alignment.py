import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, Course, GeneratedTimetable
from collections import defaultdict

print("\n" + "="*80)
print("ELECTIVE COURSE ALIGNMENT ANALYSIS")
print("="*80)

# Get active timetable
timetables = GeneratedTimetable.objects.all().order_by('-id')
active_timetable = None
for tt in timetables:
    entry_count = TimetableEntry.objects.filter(timetable=tt).count()
    if entry_count > 100:
        active_timetable = tt
        break

print(f"\nAnalyzing Timetable ID: {active_timetable.id}")
print("-" * 80)

# Find all elective courses (OE, PE, etc.)
elective_entries = TimetableEntry.objects.filter(
    timetable=active_timetable,
    course__course_number__in=['23IT6121', '23IT5211', '23IT4211']  # OE, PE courses
).select_related('course', 'year', 'meeting_time').order_by('year__year_name', 'section_number', 'meeting_time__day', 'meeting_time__time')

# Group by course type
pe_entries = [e for e in elective_entries if e.course.course_number == '23IT5211']
oe_entries = [e for e in elective_entries if e.course.course_number == '23IT6121']

print("\n" + "="*80)
print("PROFESSIONAL ELECTIVE (PE) - 23IT5211")
print("="*80)

# Group PE by section and show times
pe_by_section = defaultdict(list)
for entry in pe_entries:
    key = (entry.year.year_name, entry.section_number)
    pe_by_section[key].append({
        'day': entry.meeting_time.day,
        'time': entry.meeting_time.time,
        'is_evaluator': entry.is_evaluator,
        'batch': entry.batch
    })

for (year, section), entries in sorted(pe_by_section.items()):
    print(f"\n{year} Section {section}:")
    day_time_map = defaultdict(list)
    for e in entries:
        if not e['is_evaluator']:  # Only show main entries
            day_time_map[e['day']].append(e['time'])
    
    for day, times in sorted(day_time_map.items()):
        print(f"  {day}: {', '.join(sorted(times))}")

print("\n" + "="*80)
print("OPEN ELECTIVE (OE) - 23IT6121")
print("="*80)

# Group OE by section and show times
oe_by_section = defaultdict(list)
for entry in oe_entries:
    key = (entry.year.year_name, entry.section_number)
    oe_by_section[key].append({
        'day': entry.meeting_time.day,
        'time': entry.meeting_time.time,
        'is_evaluator': entry.is_evaluator,
        'batch': entry.batch
    })

for (year, section), entries in sorted(oe_by_section.items()):
    print(f"\n{year} Section {section}:")
    day_time_map = defaultdict(list)
    for e in entries:
        if not e['is_evaluator']:  # Only show main entries
            day_time_map[e['day']].append(e['time'])
    
    for day, times in sorted(day_time_map.items()):
        print(f"  {day}: {', '.join(sorted(times))}")

print("\n" + "="*80)
print("ALIGNMENT CHECK")
print("="*80)

# Check if electives are at the same time across sections (for student movement)
print("\nChecking if elective time slots align across sections...")

# For PE (2nd year)
print("\n2nd Year PE Alignment:")
pe_2nd_year = [(sec, entries) for (year, sec), entries in pe_by_section.items() if '2nd' in year]
if len(pe_2nd_year) > 1:
    # Get all time slots
    all_slots = set()
    for sec, entries in pe_2nd_year:
        for e in entries:
            if not e['is_evaluator']:
                all_slots.add((e['day'], e['time']))
    
    # Check if each section has the same slots
    section_slots = {}
    for sec, entries in pe_2nd_year:
        slots = set()
        for e in entries:
            if not e['is_evaluator']:
                slots.add((e['day'], e['time']))
        section_slots[sec] = slots
    
    # Compare
    aligned = all(slots == section_slots[pe_2nd_year[0][0]] for _, slots in section_slots.items())
    if aligned:
        print(f"  ✅ All sections have PE at same time slots")
        print(f"  Time slots: {sorted(all_slots)}")
    else:
        print(f"  ❌ MISALIGNED - Sections have different PE time slots:")
        for sec, slots in sorted(section_slots.items()):
            print(f"    Section {sec}: {sorted(slots)}")

# For OE (3rd year)
print("\n3rd Year OE Alignment:")
oe_3rd_year = [(sec, entries) for (year, sec), entries in oe_by_section.items() if '3rd' in year]
if len(oe_3rd_year) > 1:
    # Get all time slots
    all_slots = set()
    for sec, entries in oe_3rd_year:
        for e in entries:
            if not e['is_evaluator']:
                all_slots.add((e['day'], e['time']))
    
    # Check if each section has the same slots
    section_slots = {}
    for sec, entries in oe_3rd_year:
        slots = set()
        for e in entries:
            if not e['is_evaluator']:
                slots.add((e['day'], e['time']))
        section_slots[sec] = slots
    
    # Compare
    aligned = all(slots == section_slots[oe_3rd_year[0][0]] for _, slots in section_slots.items())
    if aligned:
        print(f"  ✅ All sections have OE at same time slots")
        print(f"  Time slots: {sorted(all_slots)}")
    else:
        print(f"  ❌ MISALIGNED - Sections have different OE time slots:")
        for sec, slots in sorted(section_slots.items()):
            print(f"    Section {sec}: {sorted(slots)}")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80 + "\n")
