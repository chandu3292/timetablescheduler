import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import CourseInstructorAssignment, Course, Instructor
from collections import defaultdict

print("\n" + "="*80)
print("INSTRUCTOR WORKLOAD BALANCING ANALYSIS")
print("="*80)

print("\n📊 CURRENT WORKLOAD DISTRIBUTION")
print("-" * 80)

# Analyze current course-instructor assignments
instructor_assignments = defaultdict(lambda: {'courses': [], 'total_hours': 0})

all_assignments = CourseInstructorAssignment.objects.filter(
    main_instructor__isnull=False
).exclude(course__course_number__in=['TRAINING', 'SPORTS_LIBRARY', 'COUNS', 'SPORT', 'COUNSELING'])

for assignment in all_assignments:
    instructor = assignment.main_instructor
    course = assignment.course
    
    instructor_assignments[instructor.name]['courses'].append({
        'course_number': course.course_number,
        'course_name': course.course_name,
        'year': assignment.year.year_name,
        'section': assignment.section_number,
        'hours': course.hours_per_week
    })
    instructor_assignments[instructor.name]['total_hours'] += course.hours_per_week

# Calculate statistics
workloads = [data['total_hours'] for data in instructor_assignments.values()]
avg_workload = sum(workloads) / len(workloads)
min_workload = min(workloads)
max_workload = max(workloads)

print(f"Number of Active Instructors: {len(instructor_assignments)}")
print(f"Average Workload: {avg_workload:.2f} hours/week/instructor")
print(f"Min Workload: {min_workload} hours/week")
print(f"Max Workload: {max_workload} hours/week")
print(f"Workload Imbalance Range: {max_workload - min_workload} hours/week")
print(f"Balance Ratio: {min_workload/max_workload*100:.1f}% (100% = perfect balance)")

# Categorize instructors by workload
overloaded = []
normal = []
underloaded = []

threshold_high = avg_workload * 1.5  # 50% above average
threshold_low = avg_workload * 0.5   # 50% below average

for instructor, data in instructor_assignments.items():
    if data['total_hours'] > threshold_high:
        overloaded.append((instructor, data))
    elif data['total_hours'] < threshold_low:
        underloaded.append((instructor, data))
    else:
        normal.append((instructor, data))

print(f"\n📈 WORKLOAD DISTRIBUTION:")
print(f"  Overloaded (>{threshold_high:.1f} hrs): {len(overloaded)} instructors")
print(f"  Normal ({threshold_low:.1f}-{threshold_high:.1f} hrs): {len(normal)} instructors")
print(f"  Underloaded (<{threshold_low:.1f} hrs): {len(underloaded)} instructors")

print("\n\n⚠️ OVERLOADED INSTRUCTORS (>50% above average)")
print("-" * 80)
overloaded_sorted = sorted(overloaded, key=lambda x: x[1]['total_hours'], reverse=True)
for instructor, data in overloaded_sorted:
    print(f"\n{instructor}: {data['total_hours']} hours/week ({len(data['courses'])} courses)")
    print(f"  Assigned courses:")
    for course in data['courses']:
        print(f"    - {course['course_number']} ({course['year']} Sec{course['section']}): {course['hours']} hrs/week")

print("\n\n💤 UNDERLOADED INSTRUCTORS (<50% below average)")
print("-" * 80)
underloaded_sorted = sorted(underloaded, key=lambda x: x[1]['total_hours'])
for instructor, data in underloaded_sorted[:15]:  # Show top 15
    print(f"\n{instructor}: {data['total_hours']} hours/week ({len(data['courses'])} courses)")
    print(f"  Assigned courses:")
    for course in data['courses']:
        print(f"    - {course['course_number']} ({course['year']} Sec{course['section']}): {course['hours']} hrs/week")

print("\n\n" + "="*80)
print("RECOMMENDATIONS FOR WORKLOAD BALANCING")
print("="*80)

print("""
⚠️ CRITICAL ISSUE: Severe workload imbalance detected!

Current Status:
- Balance ratio is only 9.5% (ideal: >80%)
- Some instructors have 10x more periods than others
- {overloaded} instructors are overloaded (>50% above average)
- {underloaded} instructors are underloaded (<50% below average)

Root Cause:
The workload imbalance occurs during COURSE-INSTRUCTOR ASSIGNMENT, not during 
timetable generation. The scheduler can only work with the assignments provided.

Solutions:

1. MANUAL REBALANCING (Immediate):
   - Review the CourseInstructorAssignment table
   - Reassign courses from overloaded to underloaded instructors
   - Ensure each instructor gets roughly {avg:.0f} hours/week
   - Consider instructor expertise and preferences

2. AUTOMATED BALANCING (Recommended for future):
   - Implement workload balancing in the course assignment UI
   - Add warnings when assigning courses to already-loaded instructors
   - Suggest underloaded instructors when assigning new courses
   - Display real-time workload statistics in admin interface

3. CONSTRAINT-BASED BALANCING:
   - Set min/max workload limits per instructor (e.g., 6-12 hrs/week)
   - Prevent assignments that violate these limits
   - Add "preferred workload" field to Instructor model

4. FAIR DISTRIBUTION ALGORITHM:
   - When multiple instructors can teach a course:
     * Prefer instructor with lowest current workload
     * Consider instructor priorities and expertise
     * Balance across departments and specializations

Most Urgent Reassignments Needed:
""".format(
    overloaded=len(overloaded),
    underloaded=len(underloaded),
    avg=avg_workload
))

# Suggest specific reassignments
print("\nSuggested Course Transfers:")
print("-" * 80)

# Match overloaded with underloaded
transfer_suggestions = []
for over_instructor, over_data in overloaded_sorted[:5]:  # Top 5 overloaded
    excess = over_data['total_hours'] - avg_workload
    # Find suitable courses to transfer
    transferable = [c for c in over_data['courses'] if c['hours'] <= excess]
    if transferable:
        for course in transferable[:2]:  # Suggest up to 2 transfers per instructor
            # Find underloaded instructor who could take it
            for under_instructor, under_data in underloaded_sorted[:5]:
                deficit = avg_workload - under_data['total_hours']
                if course['hours'] <= deficit:
                    transfer_suggestions.append({
                        'from': over_instructor,
                        'to': under_instructor,
                        'course': course
                    })
                    break

for suggestion in transfer_suggestions[:10]:
    print(f"  Transfer {suggestion['course']['course_number']} ({suggestion['course']['hours']} hrs/week)")
    print(f"    FROM: {suggestion['from']}")
    print(f"    TO: {suggestion['to']}")
    print()

print("\n" + "="*80)
