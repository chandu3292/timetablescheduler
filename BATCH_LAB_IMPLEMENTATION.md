# Batch Lab Splitting Implementation Summary

## Date: March 7, 2026

## What Was Implemented

This implementation adds support for **lab batch splitting and rotation** - a feature that allows sections to be divided into Batch 1 (B1) and Batch 2 (B2) for lab courses, with different instructors and lab rooms on different days.

---

## Changes Made

### 1. Database Models (`SchedulerApp/models.py`)

#### Added BATCH_CHOICES constant:
```python
BATCH_CHOICES = (
    ('B1', 'Batch 1'),
    ('B2', 'Batch 2'),
    ('FULL', 'Full Section'),
)
```

#### Updated Course Model:
- Added field: `split_into_batches = BooleanField(default=False)`
- This flag indicates whether a course should be split into B1 and B2

#### New Model: LabBatchAssignment
```python
class LabBatchAssignment(models.Model):
    year = ForeignKey(Year)
    section_number = IntegerField(1-3)
    course = ForeignKey(Course)
    batch = CharField('B1' or 'B2')
    day = CharField(DAYS_OF_WEEK)
    instructor = ForeignKey(Instructor)
    lab_room = ForeignKey(LabRoom)
    paired_course = ForeignKey(Course, optional)
```
- Stores batch-specific assignments for each day
- Allows different instructors and rooms for each batch
- Supports pairing with other labs running simultaneously

#### Updated TimetableEntry Model:
- Added field: `batch = CharField(max_length=4, default='FULL')`
- Stores which batch (B1, B2, or FULL) this entry is for

---

### 2. Admin Interface (`SchedulerApp/admin.py`)

#### Added LabBatchAssignmentAdmin:
- Custom admin interface for managing batch assignments
- List display shows: year, section, course, batch, day, instructor, lab_room, paired_course
- Filter by: year, section, batch, day
- Search by: course name, instructor name, lab room name
- Organized fieldsets with helpful descriptions

---

### 3. Scheduling Algorithm (`SchedulerApp/views.py`)

#### Updated Class Model:
- Added `batch` parameter to `__init__()` method
- Default value: `'FULL'` for non-split courses

#### Modified `_schedule_lab_course()`:
- Checks if `course.split_into_batches == True`
- If yes, calls new `_schedule_split_lab_course()` method
- If no, uses regular lab scheduling with `batch='FULL'`

#### New Method: `_schedule_split_lab_course()`:
```python
def _schedule_split_lab_course(self, schedule, data, course, year, section):
    # Reads LabBatchAssignment records
    # Groups assignments by day
    # For each day:
    #   - Finds continuous time blocks
    #   - Schedules B1 with its assigned instructor/room
    #   - Schedules B2 with its assigned instructor/room
    # Both batches run at same time (parallel labs)
```

**Key features:**
- Uses LabBatchAssignment to determine scheduling
- Supports different instructors for different batches
- Supports different lab rooms for different batches
- Prevents conflicts (instructor clash, room clash)
- Batches can swap labs on different days (rotation)

#### Updated TimetableEntry Creation:
- Checks if course has batch splitting
- Saves batch information (B1, B2, or FULL)
- Creates separate entries for each batch
- Deduplication now includes batch in key

#### Updated Timetable Loading from Database:
- Includes `batch` in deduplication key
- Loads batch information into Class objects
- B1 and B2 entries kept separate (not deduplicated)

#### Updated All Class Instantiations:
- Added `batch='FULL'` parameter to all `Class()` calls
- Ensures compatibility with new batch system

---

### 4. Template Display (`SchedulerApp/templatetags/index.py`)

#### Updated `sub()` Tag:
- Detects multiple classes at same time (batch splits)
- Shows batch label: `Course [B1]` or `Course [B2]`
- Groups multiple batches with `<br>` separator
- Displays instructor and room for each batch

**Example output:**
```
IoT Lab [B1] (Mr. A, Lab-101)
Cryptography Lab [B2] (Mr. D, Lab-101)
```

#### Updated `sub_instructor()` Tag:
- Shows batch information in instructor timetables
- Format: `Course [B1] (Year - Sec 1, Lab-101)`

---

### 5. Template Updates (`templates/timetable.html`)

#### Updated Cell Rendering:
```django
{% sub schedule section_number week.0 time.0 as cell_content %}
{{ cell_content|safe }}
```
- Uses `safe` filter to render HTML from batch display
- Allows `<br>` tags to create multi-line cells

---

### 6. Database Migration

#### Created Migration: `0023_auto_20260307_1015.py`
- Adds `split_into_batches` field to Course
- Adds `batch` field to TimetableEntry
- Creates LabBatchAssignment table

**Applied successfully** with `python manage.py migrate`

---

## Files Modified

1. ✅ `SchedulerApp/models.py` - Added models and fields
2. ✅ `SchedulerApp/admin.py` - Registered LabBatchAssignment admin
3. ✅ `SchedulerApp/views.py` - Updated scheduling logic
4. ✅ `SchedulerApp/templatetags/index.py` - Updated display tags
5. ✅ `templates/timetable.html` - Updated cell rendering
6. ✅ `SchedulerApp/migrations/0023_auto_20260307_1015.py` - New migration

---

## Files Created

1. ✅ `BATCH_LAB_GUIDE.md` - Complete user guide
2. ✅ `BATCH_LAB_IMPLEMENTATION.md` - This file

---

## How It Works - Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│ 1. Course Setup                                         │
│    - Mark course: split_into_batches = True            │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Create LabBatchAssignment Records                   │
│    For each section, create assignments for:           │
│    - B1 on Day 1 (Instructor X, Lab A)                │
│    - B2 on Day 1 (Instructor Y, Lab B)                │
│    - B1 on Day 2 (Instructor Z, Lab B) ← rotation!    │
│    - B2 on Day 2 (Instructor W, Lab A)                │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Generate Timetable                                   │
│    Scheduler checks split_into_batches flag            │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                          │
        ▼                          ▼
┌──────────────┐          ┌──────────────────┐
│ Regular Lab  │          │ Split Lab        │
│ (FULL)       │          │ (_schedule_split)│
└──────────────┘          └────────┬─────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │ Read LabBatchAssignment  │
                    │ Group by day             │
                    └────────┬─────────────────┘
                             │
                             ▼
                    ┌──────────────────────────┐
                    │ For each day:            │
                    │ - Find continuous block  │
                    │ - Schedule B1            │
                    │ - Schedule B2            │
                    │ (at same time!)          │
                    └────────┬─────────────────┘
                             │
                             ▼
                    ┌──────────────────────────┐
                    │ Create TimetableEntry    │
                    │ with batch='B1' or 'B2'  │
                    └────────┬─────────────────┘
                             │
                             ▼
                    ┌──────────────────────────┐
                    │ Display in timetable     │
                    │ with [B1] or [B2] label  │
                    └──────────────────────────┘
```

---

## Example Usage

### Step-by-Step Setup for IoT & Cryptography Lab Rotation

#### 1. Configure Courses:
```
Course: "IoT Lab"
- course_type: LAB
- split_into_batches: ✓
- max_continuous_hours: 3
- hours_per_week: 6
```

```
Course: "Cryptography Lab"  
- course_type: LAB
- split_into_batches: ✓
- max_continuous_hours: 3
- hours_per_week: 6
```

#### 2. Create Batch Assignments (Section 1):

**Tuesday (Day 1):**
```
LabBatchAssignment:
- Year: III/IV B.Tech II Sem
- Section: 1
- Course: IoT Lab
- Batch: B1
- Day: Tuesday
- Instructor: Mr. A
- Lab Room: Lab-101
```

```
LabBatchAssignment:
- Year: III/IV B.Tech II Sem  
- Section: 1
- Course: Cryptography Lab
- Batch: B2
- Day: Tuesday
- Instructor: Mr. B
- Lab Room: Lab-102
```

**Friday (Day 2 - Rotation):**
```
LabBatchAssignment:
- Year: III/IV B.Tech II Sem
- Section: 1
- Course: IoT Lab
- Batch: B1
- Day: Friday
- Instructor: Mr. C
- Lab Room: Lab-102  ← Swapped!
```

```
LabBatchAssignment:
- Year: III/IV B.Tech II Sem
- Section: 1
- Course: Cryptography Lab
- Batch: B2
- Day: Friday
- Instructor: Mr. D
- Lab Room: Lab-101  ← Swapped!
```

#### 3. Generated Timetable Will Show:

**Tuesday 10:30-12:30:**
```
Section 1:
  IoT Lab [B1] (Mr. A, Lab-101)
  Cryptography Lab [B2] (Mr. B, Lab-102)
```

**Friday 10:30-12:30:**
```
Section 1:
  IoT Lab [B1] (Mr. C, Lab-102)  ← Different instructor & room!
  Cryptography Lab [B2] (Mr. D, Lab-101)
```

---

## Testing Checklist

- [x] Models created successfully
- [x] Migration applied without errors
- [x] Admin interface registered
- [x] Syntax check passed
- [ ] Create test batch assignments
- [ ] Generate timetable with batch splits
- [ ] Verify display in section view
- [ ] Verify display in instructor view
- [ ] Test rotation (different days)
- [ ] Test conflict detection

---

## Benefits

✅ **Flexible Batch Management**
- Different instructors for different batches
- Different rooms for different batches
- Different instructors on different days (rotation)

✅ **Automatic Scheduling**
- Scheduler handles batch rotation automatically
- Conflict detection prevents double-booking
- Parallel labs scheduled at same time

✅ **Clear Display**
- Batch labels [B1] [B2] show clearly
- Instructor and room info included
- Multi-line display for simultaneous batches

✅ **Backward Compatible**
- Existing courses work with batch='FULL'
- No changes needed for non-split courses
- Existing timetables load correctly

---

## Next Steps

1. **Add batch assignments** in Django Admin
2. **Test with your IoT/Cryptography labs**
3. **Generate timetable** and verify display
4. **Adjust assignments** if needed
5. **Repeat for all sections** (1, 2, 3)

---

## Support

For questions or issues:
1. Check `BATCH_LAB_GUIDE.md` for usage instructions
2. Verify batch assignments in Django Admin
3. Check logs for scheduling warnings
4. Ensure all required fields are filled

---

## Credits

Implementation completed: March 7, 2026
Feature: Lab Batch Splitting & Rotation
System: Timetable Scheduler - Constraint-based Scheduling
