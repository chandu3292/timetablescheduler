"""
View Database Tables and Records
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from SchedulerApp.models import *
from django.db import connection

def view_all_tables():
    """Display all database tables with record counts"""
    
    print("\n" + "="*80)
    print("DATABASE TABLES OVERVIEW")
    print("="*80 + "\n")
    
    tables = [
        ('Instructor', Instructor, ['uid', 'name', 'email', 'department', 'designation']),
        ('Course', Course, ['course_number', 'course_name', 'course_type', 'hours_per_week']),
        ('LabRoom', LabRoom, ['id', 'lab_name', 'seating_capacity']),
        ('Year', Year, ['id', 'year_name', 'lunch_period']),
        ('MeetingTime', MeetingTime, ['pid', 'day', 'time']),
        ('InstructorPriority', InstructorPriority, ['id', 'instructor', 'day']),
        ('CourseInstructorAssignment', CourseInstructorAssignment, ['id', 'year', 'section_number', 'course']),
        ('LabBatchAssignment', LabBatchAssignment, ['id', 'year', 'section_number', 'course', 'batch']),
        ('GeneratedTimetable', GeneratedTimetable, ['id', 'year', 'fitness_score', 'generation_count']),
        ('TimetableEntry', TimetableEntry, ['id', 'year', 'section_number', 'course', 'meeting_time']),
        ('SpecialPeriod', SpecialPeriod, ['id', 'period_type', 'year']),
    ]
    
    for table_name, model, fields in tables:
        count = model.objects.count()
        print(f"📊 {table_name}")
        print(f"   Records: {count}")
        print(f"   Fields: {', '.join(fields)}")
        print()
    
    print("="*80 + "\n")


def view_table_details(table_name):
    """View detailed records from a specific table"""
    
    tables_map = {
        'instructor': (Instructor, lambda obj: f"{obj.uid} - {obj.name} ({obj.department})"),
        'course': (Course, lambda obj: f"{obj.course_number} - {obj.course_name} [{obj.course_type}]"),
        'labroom': (LabRoom, lambda obj: f"{obj.lab_name} (Capacity: {obj.seating_capacity})"),
        'year': (Year, lambda obj: f"{obj.year_name}"),
        'meetingtime': (MeetingTime, lambda obj: f"{obj.pid} - {obj.day} {obj.time}"),
        'priority': (InstructorPriority, lambda obj: f"{obj.instructor.name} - {obj.day}"),
        'assignment': (CourseInstructorAssignment, lambda obj: f"{obj.year} Sec{obj.section_number} - {obj.course}"),
        'labbatch': (LabBatchAssignment, lambda obj: f"{obj.year} Sec{obj.section_number} - {obj.course} [{obj.batch}]"),
        'timetable': (GeneratedTimetable, lambda obj: f"{obj.year} (Fitness: {obj.fitness_score:.2%})"),
        'entry': (TimetableEntry, lambda obj: f"{obj.year} Sec{obj.section_number} - {obj.course} @ {obj.meeting_time.day} {obj.meeting_time.time}"),
        'special': (SpecialPeriod, lambda obj: f"{obj.period_type} - {obj.year}"),
    }
    
    if table_name.lower() not in tables_map:
        print(f"❌ Unknown table: {table_name}")
        print(f"Available tables: {', '.join(tables_map.keys())}")
        return
    
    model, formatter = tables_map[table_name.lower()]
    records = model.objects.all()[:20]  # Limit to 20 records
    
    print(f"\n📋 {model.__name__} Table (showing {len(records)} of {model.objects.count()} records)\n")
    print("-" * 80)
    
    for i, record in enumerate(records, 1):
        print(f"{i:3d}. {formatter(record)}")
    
    if model.objects.count() > 20:
        print(f"\n... and {model.objects.count() - 20} more records")
    
    print("-" * 80 + "\n")


def view_database_schema():
    """Display database schema with table structure"""
    
    print("\n" + "="*80)
    print("DATABASE SCHEMA")
    print("="*80 + "\n")
    
    with connection.cursor() as cursor:
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = cursor.fetchall()
        
        for (table_name,) in tables:
            if not table_name.startswith('django_') and not table_name.startswith('auth_') and not table_name.startswith('sqlite_'):
                print(f"📁 Table: {table_name}")
                
                # Get table info
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                
                print("   Columns:")
                for col in columns:
                    col_id, name, col_type, not_null, default, pk = col
                    pk_marker = " [PRIMARY KEY]" if pk else ""
                    null_marker = " NOT NULL" if not_null else ""
                    print(f"      • {name} ({col_type}){pk_marker}{null_marker}")
                
                print()
    
    print("="*80 + "\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'schema':
            view_database_schema()
        elif command in ['instructor', 'course', 'labroom', 'year', 'meetingtime', 
                         'priority', 'assignment', 'labbatch', 'timetable', 'entry', 'special']:
            view_table_details(command)
        else:
            print(f"❌ Unknown command: {command}")
            print("\nUsage:")
            print("  python view_database_tables.py              # View all tables summary")
            print("  python view_database_tables.py schema       # View detailed schema")
            print("  python view_database_tables.py instructor   # View instructor records")
            print("  python view_database_tables.py course       # View course records")
            print("  python view_database_tables.py labroom      # View lab room records")
            print("  ... and so on")
    else:
        view_all_tables()
