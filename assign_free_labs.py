import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Course, LabRoom

print("=" * 80)
print("ASSIGNING FREE LAB ROOMS TO 2ND YEAR COURSES")
print("=" * 80)

# Get the free lab rooms
try:
    lab3 = LabRoom.objects.get(lab_name='lab3')
    cad_lab = LabRoom.objects.get(lab_name='CAD lab')
    phy_lab = LabRoom.objects.get(lab_name='Phy lab')
except LabRoom.DoesNotExist as e:
    print(f"ERROR: Could not find lab room: {e}")
    exit(1)

# Get 2nd year lab courses that need room assignments
try:
    na_course = Course.objects.get(course_number='23TP9102')  # NA
    pcs_course = Course.objects.get(course_number='23TP9103')  # PCS
    dbms_course = Course.objects.get(course_number='23IT4215')  # DBMS Lab
    cn_course = Course.objects.get(course_number='23IT4216')  # CN Lab
except Course.DoesNotExist as e:
    print(f"ERROR: Could not find course: {e}")
    exit(1)

# Assign NA to lab3 (completely free)
print(f"\nAssigning {na_course.course_name} to lab3...")
na_course.lab_rooms.add(lab3)
print("  [OK] Added lab3")

# Assign PCS to CAD lab (mostly free)
print(f"\nAssigning {pcs_course.course_name} to CAD lab...")
pcs_course.lab_rooms.add(cad_lab)
print("  [OK] Added CAD lab")

# Also add lab3 to DBMS (it only has NS lab which is busy)
print(f"\nAdding lab3 to {dbms_course.course_name} (currently only has NS lab)...")
dbms_course.lab_rooms.add(lab3)
print("  [OK] Added lab3")

# Add Phy lab to CN Lab (currently only has sales force lab)
print(f"\nAdding Phy lab to {cn_course.course_name} (currently only has sales force lab)...")
cn_course.lab_rooms.add(phy_lab)
print("  [OK] Added Phy lab")

print("\n" + "=" * 80)
print("LAB ROOM ASSIGNMENTS UPDATED")
print("=" * 80)

print("\nNew assignments:")
for course_num in ['23TP9102', '23TP9103', '23IT4215', '23IT4216']:
    course = Course.objects.get(course_number=course_num)
    rooms = ', '.join([r.lab_name for r in course.lab_rooms.all()])
    print(f"  {course.course_name}: {rooms}")

print("\n[NEXT STEP] Try regenerating 2nd year timetable now.")
