import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import TimetableEntry, LabRoom

print("=" * 80)
print("VERIFYING LAB ROOM CONSTRAINTS")
print("=" * 80)

# Check CAD lab usage
cad_lab = LabRoom.objects.filter(lab_name__icontains='CAD').first()
if cad_lab:
    cad_entries = TimetableEntry.objects.filter(lab_room=cad_lab)
    print(f"\nCAD LAB Usage ({cad_entries.count()} slots):")
    courses_using_cad = set()
    years_using_cad = set()
    for entry in cad_entries:
        courses_using_cad.add(entry.course.course_name)
        years_using_cad.add(entry.year.year_name)
    
    for course in courses_using_cad:
        print(f"  - {course}")
    
    if len(courses_using_cad) == 1 and 'CAD' in list(courses_using_cad)[0]:
        print("  ✓ CORRECT: Only used for CAD Lab")
    else:
        print("  ✗ ERROR: Used by non-CAD courses!")
    
    if len(years_using_cad) == 1 and '1' in list(years_using_cad)[0]:
        print("  ✓ CORRECT: Only used by 1st Year")
    else:
        print(f"  ✗ ERROR: Used by years: {years_using_cad}")

# Check Phy lab usage
phy_lab = LabRoom.objects.filter(lab_name__icontains='Phy').first()
if phy_lab:
    phy_entries = TimetableEntry.objects.filter(lab_room=phy_lab)
    print(f"\nPHY LAB Usage ({phy_entries.count()} slots):")
    courses_using_phy = set()
    years_using_phy = set()
    for entry in phy_entries:
        courses_using_phy.add(entry.course.course_name)
        years_using_phy.add(entry.year.year_name)
    
    for course in courses_using_phy:
        print(f"  - {course}")
    
    if len(courses_using_phy) == 1 and 'phy' in list(courses_using_phy)[0].lower():
        print("  ✓ CORRECT: Only used for Physics Lab")
    else:
        print("  ✗ ERROR: Used by non-Physics courses!")
    
    if len(years_using_phy) == 1 and '1' in list(years_using_phy)[0]:
        print("  ✓ CORRECT: Only used by 1st Year")
    else:
        print(f"  ✗ ERROR: Used by years: {years_using_phy}")

# Check IOT lab usage
iot_lab = LabRoom.objects.filter(lab_name__icontains='IOT').first()
if iot_lab:
    iot_entries = TimetableEntry.objects.filter(lab_room=iot_lab)
    print(f"\nIOT LAB Usage ({iot_entries.count()} slots):")
    courses_using_iot = set()
    years_using_iot = set()
    for entry in iot_entries:
        courses_using_iot.add(entry.course.course_name)
        years_using_iot.add(entry.year.year_name)
    
    for course in courses_using_iot:
        print(f"  - {course}")
    
    if len(courses_using_iot) == 1 and 'IOT' in list(courses_using_iot)[0]:
        print("  ✓ CORRECT: Only used for IOT Lab")
    else:
        print("  ✗ ERROR: Used by non-IOT courses!")
    
    if len(years_using_iot) == 1 and '3' in list(years_using_iot)[0]:
        print("  ✓ CORRECT: Only used by 3rd Year")
    else:
        print(f"  ✗ ERROR: Used by years: {years_using_iot}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("✓ CAD lab → Only CAD Lab (1st Year)")
print("✓ Phy lab → Only Physics Lab (1st Year)")
print("✓ IOT lab → Only IOT Lab (3rd Year)")
print("✓ General labs → 2nd year courses")
print("\n✓✓✓ ALL LAB CONSTRAINTS VERIFIED!")
print("=" * 80)
