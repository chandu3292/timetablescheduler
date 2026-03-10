import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import LabBatchAssignment, Year, Course, Instructor, LabRoom

print("=" * 80)
print("FIXING BATCH ASSIGNMENTS FOR CORRECT ROTATION")
print("=" * 80)

third_year = Year.objects.filter(year_name__icontains='3').first()
if not third_year:
    print("ERROR: 3rd Year not found!")
    exit(1)

# Get the courses
try:
    iot_lab = Course.objects.get(course_number='23IT4222')
    cryp_lab = Course.objects.get(course_number='23IT4221')
except Course.DoesNotExist as e:
    print(f"ERROR: Could not find courses: {e}")
    exit(1)

# Get lab rooms
try:
    iot_room = LabRoom.objects.get(lab_name='IOT lab')
    ns_lab = LabRoom.objects.get(lab_name='NS lab')
except LabRoom.DoesNotExist as e:
    print(f"ERROR: Could not find lab rooms: {e}")
    exit(1)

# Get instructors from CourseInstructorAssignment
from SchedulerApp.models import CourseInstructorAssignment

for section in [1, 2, 3]:
    print(f"\n{'='*80}")
    print(f"SECTION {section}")
    print('='*80)
    
    # Get assigned instructors for this section
    iot_assignment = CourseInstructorAssignment.objects.filter(
        year=third_year,
        section_number=section,
        course=iot_lab
    ).first()
    
    cryp_assignment = CourseInstructorAssignment.objects.filter(
        year=third_year,
        section_number=section,
        course=cryp_lab
    ).first()
    
    if not iot_assignment or not cryp_assignment:
        print(f"WARNING: No instructor assignments found for section {section}")
        continue
    
    iot_instructors = list(iot_assignment.instructors.all())
    cryp_instructors = list(cryp_assignment.instructors.all())
    
    print(f"\nIoT Lab instructors: {', '.join([i.name for i in iot_instructors])}")
    print(f"Cryptography Lab instructors: {', '.join([i.name for i in cryp_instructors])}")
    
    # Delete existing batch assignments for this section
    deleted_count = LabBatchAssignment.objects.filter(
        year=third_year,
        section_number=section,
        course__in=[iot_lab, cryp_lab]
    ).delete()
    print(f"\nDeleted {deleted_count[0]} existing batch assignments")
    
    # Create correct rotation:
    # Session 1: B1 does IoT, B2 does Cryptography (parallel)
    # Session 2: B1 does Cryptography, B2 does IoT (parallel)
    
    # Split instructors for each batch
    # For simplicity, use first half for one batch, second half for another
    mid_iot = len(iot_instructors) // 2
    mid_cryp = len(cryp_instructors) // 2
    
    iot_b1_instructors = iot_instructors[:mid_iot] if mid_iot > 0 else iot_instructors[:1]
    iot_b2_instructors = iot_instructors[mid_iot:] if mid_iot > 0 else iot_instructors[-1:]
    
    cryp_b1_instructors = cryp_instructors[:mid_cryp] if mid_cryp > 0 else cryp_instructors[:1]
    cryp_b2_instructors = cryp_instructors[mid_cryp:] if mid_cryp > 0 else cryp_instructors[-1:]
    
    print(f"\nCreating batch assignments:")
    
    # Session 1: B1 -> IoT, B2 -> Cryptography
    print(f"\n  Session 1:")
    
    # B1 does IoT
    ba1 = LabBatchAssignment.objects.create(
        year=third_year,
        section_number=section,
        course=iot_lab,
        batch='B1',
        session_number=1,
        lab_room=iot_room,
        paired_course=cryp_lab
    )
    ba1.instructors.set(iot_b1_instructors)
    print(f"    B1: IoT Lab with {', '.join([i.uid for i in iot_b1_instructors])}")
    
    # B2 does Cryptography
    ba2 = LabBatchAssignment.objects.create(
        year=third_year,
        section_number=section,
        course=cryp_lab,
        batch='B2',
        session_number=1,
        lab_room=ns_lab,
        paired_course=iot_lab
    )
    ba2.instructors.set(cryp_b2_instructors)
    print(f"    B2: Cryptography Lab with {', '.join([i.uid for i in cryp_b2_instructors])}")
    
    # Session 2: B1 -> Cryptography, B2 -> IoT (SWAPPED)
    print(f"\n  Session 2:")
    
    # B1 does Cryptography
    ba3 = LabBatchAssignment.objects.create(
        year=third_year,
        section_number=section,
        course=cryp_lab,
        batch='B1',
        session_number=2,
        lab_room=ns_lab,
        paired_course=iot_lab
    )
    ba3.instructors.set(cryp_b1_instructors)
    print(f"    B1: Cryptography Lab with {', '.join([i.uid for i in cryp_b1_instructors])}")
    
    # B2 does IoT
    ba4 = LabBatchAssignment.objects.create(
        year=third_year,
        section_number=section,
        course=iot_lab,
        batch='B2',
        session_number=2,
        lab_room=iot_room,
        paired_course=cryp_lab
    )
    ba4.instructors.set(iot_b2_instructors)
    print(f"    B2: IoT Lab with {', '.join([i.uid for i in iot_b2_instructors])}")

print("\n" + "=" * 80)
print("BATCH ASSIGNMENTS FIXED!")
print("=" * 80)
print("\nCorrect rotation pattern applied:")
print("  Session 1: B1=IoT, B2=Cryptography (parallel)")
print("  Session 2: B1=Cryptography, B2=IoT (parallel, swapped)")
print("\nNow regenerate the timetables to apply these changes.")
