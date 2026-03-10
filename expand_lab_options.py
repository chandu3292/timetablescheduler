import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Course, LabRoom, Year

print("=" * 80)
print("ADDING MORE LAB OPTIONS TO 2ND YEAR COURSES")
print("=" * 80)

# Get all available general-purpose labs (not CAD, Phy, IOT)
general_labs = LabRoom.objects.exclude(
    lab_name__in=['CAD lab', 'Phy lab', 'IOT lab']
)

print(f"\nGeneral purpose labs available:")
for lab in general_labs:
    print(f"  - {lab.lab_name}")

# Get 2nd year
second_year = Year.objects.filter(year_name__icontains='2').first()

if second_year:
    # Get all lab courses for 2nd year
    lab_courses = []
    for course in Course.objects.filter(course_type='LAB'):
        year = Year.objects.filter(courses=course).first()
        if year and '2' in year.year_name:
            lab_courses.append(course)
    
    print(f"\n2nd Year Lab Courses: {len(lab_courses)}")
    print("-" * 80)
    
    # Ensure each course has multiple lab options
    for course in lab_courses:
        current_labs = list(course.lab_rooms.all())
        current_lab_names = [lab.lab_name for lab in current_labs]
        
        print(f"\n{course.course_name}:")
        print(f"  Current labs: {', '.join(current_lab_names) if current_labs else 'NONE'}")
        
        # Add more lab options if they don't have enough
        if len(current_labs) < 2:
            added = []
            for lab in general_labs:
                if lab not in current_labs:
                    course.lab_rooms.add(lab)
                    added.append(lab.lab_name)
                    if len(current_labs) + len(added) >= 3:  # Give each course at least 3 lab options
                        break
            
            if added:
                print(f"  Added: {', '.join(added)}")
                updated_labs = list(course.lab_rooms.all())
                print(f"  New total: {[lab.lab_name for lab in updated_labs]}")
    
    print("\n" + "=" * 80)
    print("FINAL 2ND YEAR LAB ASSIGNMENTS:")
    print("=" * 80)
    
    for course in lab_courses:
        labs = list(course.lab_rooms.all())
        lab_names = [lab.lab_name for lab in labs]
        print(f"{course.course_name}: {', '.join(lab_names)}")
    
    print("\n" + "=" * 80)
    print("Ready to regenerate!")
    print("=" * 80)
