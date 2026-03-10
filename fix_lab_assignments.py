import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Course, Year, LabRoom

print("=" * 80)
print("FIXING INCORRECT LAB ROOM ASSIGNMENTS")
print("=" * 80)

# Get the lab rooms
cad_lab = LabRoom.objects.filter(lab_name__icontains='CAD').first()
phy_lab = LabRoom.objects.filter(lab_name__icontains='Phy').first()
iot_lab = LabRoom.objects.filter(lab_name__icontains='IOT').first()

print("\nLab Rooms Found:")
print(f"  CAD Lab: {cad_lab}")
print(f"  Phy Lab: {phy_lab}")
print(f"  IOT Lab: {iot_lab}")

# Remove incorrect assignments (CAD lab from PCS, Phy lab from CN)
print("\n" + "-" * 80)
print("REMOVING INCORRECT ASSIGNMENTS:")
print("-" * 80)

# Find PCS course (2nd year)
pcs_courses = Course.objects.filter(course_name__icontains='PCS')
for course in pcs_courses:
    if cad_lab in course.lab_rooms.all():
        course.lab_rooms.remove(cad_lab)
        year = Year.objects.filter(courses=course).first()
        year_name = year.year_name if year else "Unknown"
        print(f"✓ Removed CAD lab from {course.course_name} ({year_name})")

# Find CN course (2nd year)
cn_courses = Course.objects.filter(course_name__icontains='CN', course_type='LAB')
for course in cn_courses:
    if phy_lab in course.lab_rooms.all():
        course.lab_rooms.remove(phy_lab)
        year = Year.objects.filter(courses=course).first()
        year_name = year.year_name if year else "Unknown"
        print(f"✓ Removed Phy lab from {course.course_name} ({year_name})")

# Verify CAD lab is only assigned to CAD course (1st year)
print("\n" + "-" * 80)
print("VERIFYING CAD LAB ASSIGNMENTS:")
print("-" * 80)

cad_course = Course.objects.filter(course_name__icontains='CAD', course_type='LAB').first()
if cad_course:
    year = Year.objects.filter(courses=cad_course).first()
    year_name = year.year_name if year else "Unknown"
    
    if cad_lab not in cad_course.lab_rooms.all():
        cad_course.lab_rooms.add(cad_lab)
        print(f"✓ Added CAD lab to {cad_course.course_name} ({year_name})")
    else:
        print(f"✓ CAD lab already assigned to {cad_course.course_name} ({year_name})")
    
    # Show all courses using CAD lab
    all_cad_users = Course.objects.filter(lab_rooms=cad_lab)
    print(f"\nAll courses using CAD lab:")
    for c in all_cad_users:
        y = Year.objects.filter(courses=c).first()
        y_name = y.year_name if y else "Unknown"
        print(f"  - {c.course_name} ({y_name})")

# Verify Phy lab is only assigned to Phy course (1st year)
print("\n" + "-" * 80)
print("VERIFYING PHY LAB ASSIGNMENTS:")
print("-" * 80)

phy_course = Course.objects.filter(course_name__icontains='phy', course_type='LAB').first()
if phy_course:
    year = Year.objects.filter(courses=phy_course).first()
    year_name = year.year_name if year else "Unknown"
    
    if phy_lab not in phy_course.lab_rooms.all():
        phy_course.lab_rooms.add(phy_lab)
        print(f"✓ Added Phy lab to {phy_course.course_name} ({year_name})")
    else:
        print(f"✓ Phy lab already assigned to {phy_course.course_name} ({year_name})")
    
    # Show all courses using Phy lab
    all_phy_users = Course.objects.filter(lab_rooms=phy_lab)
    print(f"\nAll courses using Phy lab:")
    for c in all_phy_users:
        y = Year.objects.filter(courses=c).first()
        y_name = y.year_name if y else "Unknown"
        print(f"  - {c.course_name} ({y_name})")

# Verify IOT lab is only assigned to IOT course
print("\n" + "-" * 80)
print("VERIFYING IOT LAB ASSIGNMENTS:")
print("-" * 80)

iot_courses = Course.objects.filter(course_name__icontains='IOT', course_type='LAB')
print(f"\nAll courses using IOT lab:")
all_iot_users = Course.objects.filter(lab_rooms=iot_lab)
for c in all_iot_users:
    y = Year.objects.filter(courses=c).first()
    y_name = y.year_name if y else "Unknown"
    print(f"  - {c.course_name} ({y_name})")

# Check what labs 2nd year courses should use
print("\n" + "=" * 80)
print("2ND YEAR LAB COURSES AND THEIR ASSIGNED LABS:")
print("=" * 80)

second_year = Year.objects.filter(year_name__icontains='2').first()
if second_year:
    second_lab_courses = Course.objects.filter(year=second_year, course_type='LAB')
    for course in second_lab_courses:
        labs = list(course.lab_rooms.all())
        lab_names = [lab.lab_name for lab in labs] if labs else ["NO LABS ASSIGNED"]
        print(f"{course.course_name}: {', '.join(lab_names)}")

print("\n" + "=" * 80)
print("IMPORTANT: You need to regenerate timetables after this fix!")
print("Run: python generate_sequential.py")
print("=" * 80)
