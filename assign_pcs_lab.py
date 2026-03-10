import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Course, LabRoom

print("=" * 80)
print("ASSIGNING LAB TO PCS (2nd Year)")
print("=" * 80)

# Find PCS course
pcs_course = Course.objects.filter(course_name__icontains='PCS', course_type='LAB').first()

if pcs_course:
    # Check current assignments
    current_labs = list(pcs_course.lab_rooms.all())
    print(f"\nPCS current labs: {[lab.lab_name for lab in current_labs] if current_labs else 'NONE'}")
    
    # Assign lab2 (less congested than others)
    lab2 = LabRoom.objects.filter(lab_name='lab 2').first()
    
    if lab2:
        if lab2 not in current_labs:
            pcs_course.lab_rooms.add(lab2)
            print(f"✓ Added lab 2 to PCS")
        else:
            print(f"✓ PCS already has lab 2")
    
    # Verify
    updated_labs = list(pcs_course.lab_rooms.all())
    print(f"\nPCS updated labs: {[lab.lab_name for lab in updated_labs]}")
    
    print("\n" + "=" * 80)
    print("ALL 2ND YEAR LAB ASSIGNMENTS:")
    print("=" * 80)
    
    from SchedulerApp.models import Year
    second_year = Year.objects.filter(year_name__icontains='2').first()
    if second_year:
        second_lab_courses = Course.objects.filter(course_type='LAB')
        for course in second_lab_courses:
            year = Year.objects.filter(courses=course).first()
            if year and '2' in year.year_name:
                labs = list(course.lab_rooms.all())
                lab_names = [lab.lab_name for lab in labs] if labs else ["NO LABS"]
                print(f"  {course.course_name}: {', '.join(lab_names)}")
    
    print("\n" + "=" * 80)
    print("Ready to regenerate timetables!")
    print("Run: python generate_sequential.py")
    print("=" * 80)
else:
    print("ERROR: PCS course not found!")
