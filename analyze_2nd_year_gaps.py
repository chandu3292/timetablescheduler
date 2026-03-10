import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, Year, MeetingTime
from collections import defaultdict

# Get 2nd Year
year = Year.objects.get(year_name='2nd Year')

# Get all timetable entries for 2nd year
entries = TimetableEntry.objects.filter(year=year).select_related('course', 'meeting_time', 'instructor').order_by('section_number', 'meeting_time__day', 'meeting_time__time')

# Define time slots in order
TIME_SLOTS = [
    '8:45 - 9:45',
    '9:45 - 10:35',
    '10:35 - 11:25',
    '11:25 - 12:15',
    '12:15 - 1:05',  # LUNCH
    '1:05 - 1:55',
    '1:55 - 2:45',
    '2:45 - 3:35'
]

DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

print("="*80)
print("SECOND YEAR TIMETABLE GAP ANALYSIS")
print("="*80)

# Organize by section
sections = defaultdict(lambda: defaultdict(list))
for entry in entries:
    sections[entry.section_number][entry.meeting_time.day].append({
        'time': entry.meeting_time.time,
        'course': entry.course.course_number,
        'instructor': entry.instructor.name if entry.instructor else 'N/A'
    })

# Analyze each section
for section in sorted(sections.keys()):
    print(f"\n{'='*80}")
    print(f"SECTION {section}")
    print(f"{'='*80}")
    
    total_gaps = 0
    total_classes = 0
    
    for day in DAYS:
        classes = sections[section].get(day, [])
        if not classes:
            print(f"\n{day}: NO CLASSES")
            continue
            
        # Sort by time
        classes_sorted = sorted(classes, key=lambda x: TIME_SLOTS.index(x['time']) if x['time'] in TIME_SLOTS else 99)
        
        print(f"\n{day}:")
        
        # Find occupied slots
        occupied_slots = [TIME_SLOTS.index(c['time']) for c in classes_sorted if c['time'] in TIME_SLOTS]
        
        if occupied_slots:
            first_class = min(occupied_slots)
            last_class = max(occupied_slots)
            
            # Count gaps (empty slots between first and last class, excluding lunch)
            gaps = []
            for i in range(first_class, last_class + 1):
                if i not in occupied_slots and TIME_SLOTS[i] != '12:15 - 1:05':
                    gaps.append(TIME_SLOTS[i])
            
            # Display schedule
            for i, time_slot in enumerate(TIME_SLOTS):
                if time_slot == '12:15 - 1:05':
                    print(f"  {time_slot}: LUNCH BREAK")
                elif i in occupied_slots:
                    class_info = next(c for c in classes_sorted if TIME_SLOTS.index(c['time']) == i)
                    print(f"  {time_slot}: {class_info['course']} - {class_info['instructor']}")
                elif i >= first_class and i <= last_class:
                    print(f"  {time_slot}: [GAP]")
            
            # Summary
            print(f"\n  Classes on {day}: {len(classes_sorted)}")
            print(f"  Gaps on {day}: {len(gaps)}")
            if gaps:
                print(f"  Gap slots: {', '.join(gaps)}")
            
            total_gaps += len(gaps)
            total_classes += len(classes_sorted)
    
    print(f"\n{'-'*80}")
    print(f"SECTION {section} SUMMARY:")
    print(f"  Total Classes: {total_classes}")
    print(f"  Total Gaps: {total_gaps}")
    if total_classes > 0:
        gap_ratio = (total_gaps / total_classes) * 100
        print(f"  Gap Ratio: {gap_ratio:.1f}% (gaps per class)")

print("\n" + "="*80)
print("POTENTIAL CAUSES OF GAPS:")
print("="*80)
print("""
1. INSTRUCTOR CONFLICTS:
   - If an instructor teaches multiple sections/courses, their availability
     creates forced gaps when scheduling around their other commitments

2. LAB ROOM AVAILABILITY:
   - Lab courses need specific rooms, limiting scheduling flexibility
   - When the required lab room is occupied, course must be delayed

3. ELECTIVE SYNCHRONIZATION:
   - Electives must be synchronized across all sections (same time)
   - This rigid requirement can force gaps in individual section schedules

4. TP COURSE CONTINUOUS BLOCKS:
   - TP courses need 2 continuous hours
   - Finding continuous blocks can push other courses into suboptimal slots

5. SCHEDULING ORDER:
   - The constraint scheduler processes courses in this order:
     LAB → ELECTIVE → CONTINUOUS THEORY (TP) → REGULAR THEORY
   - Early phases consume prime slots, forcing later courses into gaps

6. RANDOM SLOT SELECTION:
   - When multiple valid slots exist, random selection may not choose
     the gap-minimizing option

SOLUTIONS:
- Increase MAX_ATTEMPTS for more schedule variations
- Implement gap penalty in fitness function (already exists: 20 points per gap)
- Add instructor assignment optimization
- Consider section-balanced instructor distribution
""")

# Check for common gap causes
print("\n" + "="*80)
print("CHECKING SPECIFIC GAP CAUSES:")
print("="*80)

from SchedulerApp.models import Course, Instructor

# Check instructor teaching loads
print("\nINSTRUCTOR TEACHING MULTIPLE 2ND YEAR SECTIONS:")
for entry in entries:
    if entry.instructor:
        instructor_entries = TimetableEntry.objects.filter(
            year=year,
            instructor=entry.instructor
        ).values_list('section_number', 'course__course_number').distinct()
        
        if instructor_entries.count() > 3:  # Teaching more than 3 different section-course combos
            print(f"  {entry.instructor.name}: {instructor_entries.count()} section-course assignments")
            break  # Just show first few

# Check electives
print("\nELECTIVE COURSES (Must be synchronized across sections):")
electives = Course.objects.filter(course_type='ELECTIVE', year=year)
for elective in electives:
    times = TimetableEntry.objects.filter(course=elective, year=year).values('meeting_time__day', 'meeting_time__time', 'section_number').distinct()
    if times.count() > 0:
        time_info = times.first()
        print(f"  {elective.course_number}: {time_info['meeting_time__day']} {time_info['meeting_time__time']}")

# Check TP courses
print("\nTP COURSES (Need 2 continuous hours):")
tp_courses = Course.objects.filter(year=year, course_number__startswith='23TP')
for tp_course in tp_courses:
    entries_tp = TimetableEntry.objects.filter(course=tp_course, year=year).values('section', 'meeting_time__day', 'meeting_time__time').order_by('section', 'meeting_time__day', 'meeting_time__time')
    for section_num in [1, 2, 3]:
        section_entries = [e for e in entries_tp if e['section_number'] == section_num]
        if section_entries:
            print(f"  {tp_course.course_number} Sec{section_num}: {section_entries[0]['meeting_time__day']} - {len(section_entries)} consecutive slots")

print("\n" + "="*80)
