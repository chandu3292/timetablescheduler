import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Course, CourseInstructorAssignment

print("\n" + "="*80)
print("ISSUE ANALYSIS: Course 23IT6121 OE (THEORY) - Same Time Across All Sections")
print("="*80)

course = Course.objects.filter(course_number='23IT6121').first()
assignments = CourseInstructorAssignment.objects.filter(course=course)

print("\n📋 CURRENT CONFIGURATION:")
print(f"   Course: {course.course_number} ({course.course_name})")
print(f"   Type: {course.course_type} ✓")
print(f"   Hours/Week: {course.hours_per_week}")
print(f"   Needs Section Alignment: YES (starts with 23IT6)")

print("\n👥 SECTION ASSIGNMENTS:")
instructor_map = {}
for a in assignments:
    instructors = list(a.instructors.all())
    instructor_map[a.section_number] = instructors
    inst_names = [str(i) for i in instructors]
    print(f"   Section {a.section_number}: {', '.join(inst_names)}")

print("\n❌ THE PROBLEM:")
print(f"   Sections 2 & 3 share the SAME instructor: {instructor_map[2][0]}")
print(f"   But the scheduler forces them at the SAME TIME for 'alignment'")
print(f"   This creates PHYSICAL IMPOSSIBILITY:")
print(f"      - IT23 Ms B keerthana CANNOT teach Sec2 AND Sec3 simultaneously!")

print("\n🔍 ROOT CAUSE IN CODE:")
print("""
   Location: SchedulerApp/views.py, function needs_section_alignment()
   
   def needs_section_alignment(course):
       if course.course_type == 'LAB':
           return False
       if course.course_type == 'ELECTIVE':
           return True
       if course.course_number.startswith('23IT6'):  <- MATCHES 23IT6121
           return True
       ...
       return False
   
   The logic forces alignment (same time) for ALL 23IT6* and 23IT7* courses.
   But it doesn't check if different sections have DIFFERENT instructors!
""")

print("\n✅ SOLUTION OPTIONS:")
print("""
   OPTION 1 (Recommended): Modify the alignment logic
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Before forcing alignment for 23IT6*/23IT7* courses:
   - Check if all sections have the same instructor(s)
   - If different instructors: DON'T force alignment
   - Schedule each section independently
   
   OPTION 2: Change assignment in database
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Since Sec 2 & 3 have same instructor, combine them:
   - Remove Section 3 assignment
   - Merge Sec 2 & 3 students into one session taught by IT23
   - Or reassign Sec 3 to a different instructor
   
   OPTION 3: Change course type
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   If this IS truly a combined lecture:
   - Mark course as 'combined' or 'lecture'  
   - Don't split into sections for this course
   - Teach all 3 sections in one lecture hall
   
   OPTION 4: Split instructors properly
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Keep alignment BUT give each section a different instructor:
   - Section 1: IT22 Mrs B sunayana
   - Section 2: IT23 Ms B keerthana
   - Section 3: [Assign a different instructor, e.g., IT21]
""")

print("\n" + "="*80)
