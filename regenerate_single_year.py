"""
SINGLE YEAR REGENERATION SCRIPT
================================
Use this when one year's semester ends and you need to regenerate only that year's timetable.
This script does NOT affect other years' timetables - they remain unchanged.

Usage:
    python regenerate_single_year.py "2nd Year"
    python regenerate_single_year.py "3rd Year"
    
Year names must match exactly as they appear in the database.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from django.db import transaction
from SchedulerApp.models import TimetableEntry, Year, Section
from SchedulerApp.views import ConstraintScheduler

def regenerate_single_year(year_name):
    """
    Regenerate timetables for a single year without affecting other years.
    
    Args:
        year_name: Exact year name (e.g., "1st Year", "2nd Year", "3rd Year")
    """
    print(f"\n{'='*80}")
    print(f"SINGLE YEAR REGENERATION: {year_name}")
    print(f"{'='*80}\n")
    
    # Get the year object
    try:
        year = Year.objects.get(year_name=year_name)
    except Year.DoesNotExist:
        print(f"❌ ERROR: Year '{year_name}' not found in database!")
        print("\nAvailable years:")
        for y in Year.objects.all():
            print(f"  - {y.year_name}")
        return False
    
    # Get sections for this year
    sections = Section.objects.filter(year=year).order_by('section_number')
    if not sections.exists():
        print(f"❌ ERROR: No sections found for {year_name}!")
        return False
    
    print(f"Found {sections.count()} section(s) for {year_name}")
    print()
    
    # Show current timetable entries
    current_entries = TimetableEntry.objects.filter(year=year)
    print(f"Current timetable entries for {year_name}: {current_entries.count()}")
    print()
    
    # Confirm deletion
    if current_entries.count() > 0:
        print(f"⚠️  This will DELETE all {current_entries.count()} existing entries for {year_name}")
        print(f"⚠️  Other years' timetables will NOT be affected")
        response = input("\nContinue? (yes/no): ").strip().lower()
        if response != 'yes':
            print("Cancelled.")
            return False
        print()
    
    # Delete existing entries for this year ONLY
    with transaction.atomic():
        deleted_count = current_entries.count()
        current_entries.delete()
        print(f"✅ Deleted {deleted_count} existing entries for {year_name}")
        print()
    
    # Generate new timetable for this year
    print(f"{'='*80}")
    print(f"GENERATING TIMETABLE FOR {year_name}")
    print(f"{'='*80}\n")
    
    scheduler = ConstraintScheduler()
    schedule = scheduler.generate_schedule(year=year)
    
    if schedule is None:
        print(f"\n❌ FAILED: Could not generate timetable for {year_name}")
        print("See error logs above for details.")
        return False
    
    # Count new entries
    new_entries = TimetableEntry.objects.filter(year=year)
    print(f"\n{'='*80}")
    print(f"GENERATION COMPLETE")
    print(f"{'='*80}\n")
    print(f"✅ Successfully generated {new_entries.count()} timetable entries for {year_name}")
    print()
    
    # Show summary by section
    for section in sections:
        section_entries = new_entries.filter(section_number=section.section_number)
        print(f"  Section {section.section_number}: {section_entries.count()} entries")
    
    print()
    print(f"✅ {year_name} timetable regeneration COMPLETE!")
    print(f"   Other years remain unchanged.")
    print()
    
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python regenerate_single_year.py \"YEAR_NAME\"")
        print("\nExamples:")
        print("  python regenerate_single_year.py \"1st Year\"")
        print("  python regenerate_single_year.py \"2nd Year\"")
        print("  python regenerate_single_year.py \"3rd Year\"")
        print("  python regenerate_single_year.py \"4th Year\"")
        print("\nAvailable years:")
        for year in Year.objects.all():
            print(f"  - {year.year_name}")
        sys.exit(1)
    
    year_name = sys.argv[1]
    success = regenerate_single_year(year_name)
    
    if not success:
        sys.exit(1)

if __name__ == '__main__':
    main()
