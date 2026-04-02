import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, Course, Instructor
from collections import defaultdict

print("\n" + "="*80)
print("EVALUATOR ASSIGNMENT VERIFICATION")
print("="*80)

print("\n📋 CURRENT EVALUATOR ASSIGNMENT LOGIC:")
print("-" * 80)
print("""
The system automatically selects evaluators for lab courses based on:
  1. ✅ Same department as the course (dept_code match)
  2. ✅ Availability during the lab time block (no conflicts)
  3. ✅ Designation = Assistant Professor (ASST_PROF only)
  4. ✅ Excludes main instructors of the course

This is implemented in: SchedulerApp/views.py -> _get_available_evaluators()
(Lines 2192-2275)
""")

print("\n" + "="*80)
print("VERIFYING EVALUATOR ASSIGNMENTS IN CURRENT TIMETABLE")
print("="*80)

# Get all lab courses with evaluators
lab_entries = TimetableEntry.objects.filter(
    course__course_type='LAB',
    is_evaluator=True
).select_related('course', 'instructor', 'year').distinct()

# Group by course
course_evaluators = defaultdict(lambda: {
    'main_instructors': set(),
    'evaluators': set(),
    'sections': set(),
    'dept_code': None,
    'course_name': None
})

# First, get all main instructors for labs
main_instructors_entries = TimetableEntry.objects.filter(
    course__course_type='LAB',
    is_evaluator=False
).select_related('course', 'instructor', 'year')

for entry in main_instructors_entries:
    key = (entry.course.course_number, entry.year.year_name)
    course_evaluators[key]['main_instructors'].add(entry.instructor)
    course_evaluators[key]['sections'].add(entry.section_number)
    course_evaluators[key]['dept_code'] = entry.course.dept_code
    course_evaluators[key]['course_name'] = entry.course.course_name

# Then, get all evaluators
for entry in lab_entries:
    key = (entry.course.course_number, entry.year.year_name)
    course_evaluators[key]['evaluators'].add(entry.instructor)
    course_evaluators[key]['sections'].add(entry.section_number)
    course_evaluators[key]['dept_code'] = entry.course.dept_code
    course_evaluators[key]['course_name'] = entry.course.course_name

print(f"\nFound {len(course_evaluators)} lab courses with evaluator assignments\n")

# Verify each course
verification_results = {
    'same_dept': 0,
    'diff_dept': 0,
    'asst_prof': 0,
    'not_asst_prof': 0,
    'excluded_main': 0,
    'used_main_as_eval': 0
}

dept_violations = []
designation_violations = []
main_instructor_violations = []

for (course_num, year_name), data in course_evaluators.items():
    print(f"{course_num} ({year_name}) - {data['course_name']}")
    print(f"  Department: {data['dept_code']}")
    print(f"  Main Instructors: {', '.join([i.name for i in data['main_instructors']])}")
    print(f"  Evaluators: {', '.join([i.name for i in data['evaluators']]) if data['evaluators'] else 'None'}")
    
    # Check if evaluators are from same department
    for evaluator in data['evaluators']:
        if evaluator.department == data['dept_code']:
            print(f"    ✅ {evaluator.name}: Same dept ({evaluator.department})")
            verification_results['same_dept'] += 1
        else:
            print(f"    ⚠️ {evaluator.name}: Different dept ({evaluator.department} != {data['dept_code']})")
            verification_results['diff_dept'] += 1
            dept_violations.append({
                'course': course_num,
                'year': year_name,
                'evaluator': evaluator.name,
                'eval_dept': evaluator.department,
                'course_dept': data['dept_code']
            })
        
        # Check designation
        if evaluator.designation == 'ASST_PROF':
            print(f"    ✅ {evaluator.name}: Assistant Professor")
            verification_results['asst_prof'] += 1
        else:
            print(f"    ⚠️ {evaluator.name}: NOT Assistant Professor ({evaluator.designation})")
            verification_results['not_asst_prof'] += 1
            designation_violations.append({
                'course': course_num,
                'year': year_name,
                'evaluator': evaluator.name,
                'designation': evaluator.designation
            })
        
        # Check if evaluator is also a main instructor for this course
        if evaluator in data['main_instructors']:
            print(f"    ⚠️ {evaluator.name}: Used as BOTH main instructor AND evaluator!")
            verification_results['used_main_as_eval'] += 1
            main_instructor_violations.append({
                'course': course_num,
                'year': year_name,
                'evaluator': evaluator.name
            })
        else:
            verification_results['excluded_main'] += 1
    
    print()

# Summary
print("\n" + "="*80)
print("VERIFICATION SUMMARY")
print("="*80)

total_evaluators = verification_results['same_dept'] + verification_results['diff_dept']
if total_evaluators > 0:
    print(f"\n1. Department Matching:")
    print(f"   ✅ Same Department: {verification_results['same_dept']}/{total_evaluators} ({verification_results['same_dept']*100/total_evaluators:.1f}%)")
    print(f"   ⚠️ Different Department: {verification_results['diff_dept']}/{total_evaluators} ({verification_results['diff_dept']*100/total_evaluators:.1f}%)")
    
    print(f"\n2. Designation Check:")
    print(f"   ✅ Assistant Professor: {verification_results['asst_prof']}/{total_evaluators} ({verification_results['asst_prof']*100/total_evaluators:.1f}%)")
    print(f"   ⚠️ Other Designation: {verification_results['not_asst_prof']}/{total_evaluators} ({verification_results['not_asst_prof']*100/total_evaluators:.1f}%)")
    
    print(f"\n3. Main Instructor Exclusion:")
    print(f"   ✅ Not a Main Instructor: {verification_results['excluded_main']}/{total_evaluators} ({verification_results['excluded_main']*100/total_evaluators:.1f}%)")
    print(f"   ⚠️ Also Main Instructor: {verification_results['used_main_as_eval']}/{total_evaluators} ({verification_results['used_main_as_eval']*100/total_evaluators:.1f}%)")

# Show violations if any
if dept_violations:
    print("\n⚠️ DEPARTMENT MISMATCHES:")
    for v in dept_violations:
        print(f"   {v['course']} ({v['year']}): {v['evaluator']} from {v['eval_dept']} evaluating {v['course_dept']} course")

if designation_violations:
    print("\n⚠️ DESIGNATION VIOLATIONS:")
    for v in designation_violations:
        print(f"   {v['course']} ({v['year']}): {v['evaluator']} is {v['designation']} (not ASST_PROF)")

if main_instructor_violations:
    print("\n⚠️ MAIN INSTRUCTOR USED AS EVALUATOR:")
    for v in main_instructor_violations:
        print(f"   {v['course']} ({v['year']}): {v['evaluator']}")

# Check availability (this would require checking time conflicts)
print("\n\n4. Availability Check:")
print("   ℹ️ System checks availability during assignment - evaluators are only")
print("   assigned if they have no conflicts during the lab time block.")
print("   This is verified in real-time during timetable generation.")

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)

if verification_results['diff_dept'] == 0 and verification_results['not_asst_prof'] == 0 and verification_results['used_main_as_eval'] == 0:
    print("\n✅ ALL EVALUATOR ASSIGNMENTS ARE CORRECT!")
    print("   - All evaluators are from the same department as their courses")
    print("   - All evaluators are Assistant Professors")
    print("   - No main instructors are used as evaluators for their own courses")
    print("   - Availability is automatically checked during generation")
else:
    print("\n⚠️ SOME EVALUATOR ASSIGNMENTS NEED REVIEW")
    print(f"   - {verification_results['diff_dept']} evaluators from different departments")
    print(f"   - {verification_results['not_asst_prof']} evaluators with non-ASST_PROF designation")
    print(f"   - {verification_results['used_main_as_eval']} main instructors also serving as evaluators")

print("\n" + "="*80 + "\n")
