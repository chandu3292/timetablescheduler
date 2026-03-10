import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, Year, Course
from collections import defaultdict

print("="*80)
print("LAB INSTRUCTOR ASSIGNMENT ANALYSIS")
print("="*80)

# Get all years
years = Year.objects.all().order_by('id')

for year in years:
    print(f"\n{'='*80}")
    print(f"{year.year_name}")
    print(f"{'='*80}")
    
    # Get all lab courses for this year
    lab_courses = Course.objects.filter(year=year, course_type='LAB')
    
    if not lab_courses:
        print("  No lab courses found")
        continue
    
    for course in lab_courses:
        print(f"\n  Course: {course.course_number} - {course.course_name}")
        print(f"  Hours per week: {course.hours_per_week}")
        
        # Get all timetable entries for this lab course
        entries = TimetableEntry.objects.filter(
            year=year, 
            course=course
        ).select_related('instructor', 'meeting_time').order_by('section_number', 'batch')
        
        if not entries.exists():
            print("    No timetable entries found")
            continue
        
        # Group by section and batch
        section_data = defaultdict(lambda: defaultdict(list))
        
        for entry in entries:
            section = entry.section_number
            batch = entry.batch if entry.batch else 'FULL'
            instructor = entry.instructor.name if entry.instructor else 'No Instructor'
            time = f"{entry.meeting_time.day} {entry.meeting_time.time}"
            
            section_data[section][batch].append({
                'instructor': instructor,
                'time': time
            })
        
        # Analyze each section
        for section in sorted(section_data.keys()):
            print(f"\n    Section {section}:")
            
            batches = section_data[section]
            
            for batch in sorted(batches.keys()):
                entries_list = batches[batch]
                
                # Get unique instructors for this batch
                instructors = list(set([e['instructor'] for e in entries_list]))
                
                print(f"      Batch {batch}:")
                print(f"        Total lab slots: {len(entries_list)}")
                print(f"        Number of instructors: {len(instructors)}")
                
                if len(instructors) == 1:
                    print(f"        Instructor: {instructors[0]}")
                    print(f"        [SINGLE INSTRUCTOR - All {len(entries_list)} lab hours taught by same instructor]")
                else:
                    print(f"        [MULTIPLE INSTRUCTORS - Lab hours split among {len(instructors)} instructors]")
                    for instructor in instructors:
                        count = sum(1 for e in entries_list if e['instructor'] == instructor)
                        print(f"          - {instructor}: {count} hours")
                
                # Show time schedule
                print(f"        Schedule:")
                for entry_info in entries_list:
                    print(f"          {entry_info['time']}: {entry_info['instructor']}")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)

# Overall statistics
all_lab_entries = TimetableEntry.objects.filter(course__course_type='LAB').select_related('course', 'instructor')

lab_batches = defaultdict(lambda: defaultdict(set))

for entry in all_lab_entries:
    key = (entry.year.year_name, entry.course.course_number, entry.section_number, entry.batch or 'FULL')
    if entry.instructor:
        lab_batches[key]['instructors'].add(entry.instructor.name)
    lab_batches[key]['count'] = lab_batches[key].get('count', 0) + 1

single_instructor_count = 0
multi_instructor_count = 0

for key, data in lab_batches.items():
    if len(data['instructors']) == 1:
        single_instructor_count += 1
    else:
        multi_instructor_count += 1

print(f"\nTotal lab sections/batches: {len(lab_batches)}")
print(f"  Single instructor: {single_instructor_count} ({single_instructor_count / len(lab_batches) * 100:.1f}%)")
print(f"  Multiple instructors: {multi_instructor_count} ({multi_instructor_count / len(lab_batches) * 100:.1f}%)")

if multi_instructor_count > 0:
    print("\n[WARNING] Some lab batches have multiple instructors!")
    print("This typically happens when:")
    print("  1. Lab hours exceed a single instructor's availability")
    print("  2. Instructor conflicts force splitting lab sessions")
    print("  3. Manual instructor assignments override default behavior")
else:
    print("\n[OK] All lab batches are taught by a single instructor (consistent)")

print("\n" + "="*80)
