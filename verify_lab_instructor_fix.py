"""
Verify lab instructor assignment after fix.
Expected:
- 1st Year labs: 1 instructor only
- 2nd-4th Year labs: 1 main instructor + 1-2 evaluators from same department
- All instructors for a lab are at the SAME time (not batch splits)
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, Year, Course
from collections import defaultdict

print("="*80)
print("LAB INSTRUCTOR ASSIGNMENT VERIFICATION")
print("="*80)

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
        print(f"\n  Course: {course.course_number} - {course.course_name}(Dept: {course.dept_code})")
        
        # Get all lab entries for this course
        entries = TimetableEntry.objects.filter(
            year=year,
            course=course
        ).select_related('instructor', 'meeting_time').order_by('section_number', 'meeting_time__day', 'meeting_time__time')
        
        if not entries.exists():
            print("    No timetable entries found")
            continue
        
        # Group by section, day, time
        sessions = defaultdict(list)
        for entry in entries:
            key = (entry.section_number, entry.meeting_time.day, entry.meeting_time.time)
            sessions[key].append(entry)
        
        # Analyze each unique session
        for (section, day, time), session_entries in sorted(sessions.items()):
            instructors = [e.instructor.name if e.instructor else 'N/A' for e in session_entries]
            main_instructors = [e.instructor for e in session_entries if not e.is_evaluator]
            evaluators = [e.instructor for e in session_entries if e.is_evaluator]
            
            instructor_depts = [e.instructor.department for e in session_entries if e.instructor and e.instructor.department]
            
            print(f"    Section {section}, {day} {time}:")
            print(f"      Total instructors: {len(session_entries)}")
            print(f"      Main instructor: {main_instructors[0].name if main_instructors else 'NONE'}")
            if evaluators:
                print(f"      Evaluators ({len(evaluators)}): {', '.join([e.name for e in evaluators])}")
            
            # Verify department consistency
            if instructor_depts and len(set(instructor_depts)) > 1:
                print(f"      [ERROR] Multiple departments: {set(instructor_depts)}")
            elif instructor_depts:
                dept = instructor_depts[0]
                if dept != course.dept_code:
                    print(f"      [WARN] Department mismatch: Course={course.dept_code}, Instructors={dept}")
                else:
                    print(f"      [OK] All from {dept} department")
            
            # Verify year-specific requirements
            if year.year_name == '1st Year':
                if len(session_entries) > 1:
                    print(f"      [ERROR] 1st Year should have 1 instructor only, has {len(session_entries)}")
                else:
                    print(f"      [OK] 1st Year: Single instructor")
            else:
                if len(main_instructors) != 1:
                    print(f"      [ERROR] Should have exactly 1 main instructor, has {len(main_instructors)}")
                elif len(evaluators) == 0:
                    print(f"      [WARN] No evaluators assigned (expected 1-2)")
                elif len(evaluators) > 2:
                    print(f"      [WARN] Too many evaluators: {len(evaluators)} (expected 1-2)")
                else:
                    print(f"      [OK] {year.year_name}: 1 main + {len(evaluators)} evaluators")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)

# Count instructor assignments per lab session
all_lab_sessions = TimetableEntry.objects.filter(course__course_type='LAB').values(
    'year__year_name', 'section_number', 'course__course_number', 'meeting_time__day', 'meeting_time__time'
).distinct()

session_instructor_counts = defaultdict(int)

for session in all_lab_sessions:
    entries_count = TimetableEntry.objects.filter(
        year__year_name=session['year__year_name'],
        section_number=session['section_number'],
        course__course_number=session['course__course_number'],
        meeting_time__day=session['meeting_time__day'],
        meeting_time__time=session['meeting_time__time']
    ).count()
    session_instructor_counts[entries_count] += 1

print("\nLab sessions by number of instructors:")
for count, num_sessions in sorted(session_instructor_counts.items()):
    print(f"  {count} instructor(s): {num_sessions} sessions")

print("\n" + "="*80)
