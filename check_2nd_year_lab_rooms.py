import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import Course, Year, LabRoom

print("=" * 80)
print("2ND YEAR LAB COURSE ROOM ASSIGNMENTS")
print("=" * 80)

second_year = Year.objects.filter(year_name__icontains='2').first()
if second_year:
    labs = Course.objects.filter(year=second_year, course_type='LAB').order_by('-max_continuous_hours')
    
    all_lab_rooms = LabRoom.objects.all()
    print(f"\nAvailable lab rooms: {', '.join([lr.lab_name for lr in all_lab_rooms])}")
    
    print("\n" + "=" * 80)
    for lab in labs:
        assigned_rooms = list(lab.lab_rooms.all())
        room_names = [r.lab_name for r in assigned_rooms] if assigned_rooms else []
        
        print(f"\n{lab.course_name} ({lab.course_number})")
        print(f"  Needs: {lab.max_continuous_hours} continuous hours")
        print(f"  Assigned to: {', '.join(room_names) if room_names else 'NO LAB ROOMS ASSIGNED!'}")
        
        if not room_names:
            print(f"  [ACTION NEEDED] Must assign lab rooms to this course!")

print("\n" + "=" * 80)
print("RECOMMENDATION:")
print("=" * 80)
print("\nlab3, CAD lab, Phy lab are mostly FREE.")
print("Assign 2nd year labs to these rooms for successful scheduling.")
