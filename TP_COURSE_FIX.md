# TP COURSE CONTINUOUS SCHEDULING FIX

## Problem Statement

TP department courses (Training & Placement) required 2 continuous hours like labs, but should **NOT** use lab rooms. Previously, these courses were being scheduled as separate 1-hour periods on different days.

### Affected Courses:
- **2nd Year:** 23TP9102 (NA), 23TP9103 (PCS)
- **3rd Year:** 23TP9104 (HLR), 23TP09104 (AGIS), 23TP19104 (SESD)

### Requirements:
1. ✅ 2 continuous hours on the SAME day
2. ✅ NO lab room assignment
3. ✅ Scheduled like labs but in regular classrooms

---

## Solution Implemented

### 1. Modified ConstraintScheduler._schedule_theory_course()
**File:** `SchedulerApp/views.py` (Lines 1383-1434)

Added special handling for courses where `hours_per_week == max_continuous_hours > 1`:

```python
# ⭐ CRITICAL FIX FOR TP COURSES:
# If hours_per_week == max_continuous_hours > 1, ALL hours MUST be continuous
if hours_per_week == max_continuous_hours and max_continuous > 1:
    logger.info(f"Scheduling as {max_continuous}-hour continuous block (TP course)")
    
    # Find continuous blocks
    available_blocks = self._find_continuous_blocks(data, max_continuous)
    
    # Filter blocks without conflicts
    valid_blocks = [block for block in available_blocks if all conflict checks pass]
    
    # Schedule the entire block at once
    for mt in selected_block:
        new_class = Class(year, section, course, batch='FULL')
        new_class.set_meetingTime(mt)
        new_class.set_instructor(instructor)
        new_class.set_room(None)  # Theory courses don't use lab rooms
        schedule._classes.append(new_class)
    
    return True
```

**Key Changes:**
- Detects TP courses by checking if `hours_per_week == max_continuous_hours > 1`
- Uses `_find_continuous_blocks()` to find valid 2-hour blocks
- Schedules ALL hours as a single continuous block
- Sets `room = None` (no lab room assignment)

### 2. Enhanced addContinuousCourse() in Schedule class
**File:** `SchedulerApp/views.py` (Lines 305-349)

Added conflict detection to prefer conflict-free continuous blocks:

```python
# ⭐ ENHANCED: Check for conflicts to prefer conflict-free blocks
for mt in block:
    if self.isSectionBusy(section_number, mt) or self.isInstructorBusy(instructor, mt):
        has_conflict = True
        break

# Add block with conflict flag
valid_blocks.append((block, has_conflict))

# Prefer conflict-free blocks over conflicted ones
conflict_free_blocks = [block for block, has_conflict in valid_blocks if not has_conflict]
blocks_to_use = conflict_free_blocks if conflict_free_blocks else conflicted_blocks
```

### 3. Fixed fallback scheduling in Schedule.initialize()
**File:** `SchedulerApp/views.py` (Lines 489-501)

Prevented TP courses from falling back to separate 1-hour scheduling:

```python
#⭐ CRITICAL FIX FOR TP COURSES:
# Only schedule remaining hours separately if the course ALLOWS partial continuity
# For TP courses where hours_per_week == max_continuous_hours (e.g., 2==2),
# ALL hours MUST be continuous - do NOT fall back to separate scheduling
if course.hours_per_week > course.max_continuous_hours:
    # Course allows some hours to be separate (e.g., 4 hrs/week, 2 max continuous)
    # Schedule remaining hours separately
    ...
# Otherwise, do NOT schedule remaining hours - force continuous scheduling
```

---

## Verification Results

### Before Fix:
```
23TP9102 Sec1:
  ✗ Monday 1:05-1:55 (1 hour, separate)
  ✗ Wednesday 11:25-12:15 (1 hour, separate)
```

### After Fix:
```
23TP9102 Sec1:
  ✓ Tuesday 1:55-3:35 (2 continuous hours)
  ✓ Lab: None
```

### All TP Courses Verification:
- ✅ **23TP9102 (NA)**: ALL sections have 2 continuous hours, no lab rooms
- ✅ **23TP9103 (PCS)**: ALL sections have 2 continuous hours, no lab rooms
- ✅ **23TP9104 (HLR)**: ALL sections have 2 continuous hours, no lab rooms
- ✅ **23TP09104 (AGIS)**: ALL sections have 2 continuous hours, no lab rooms
- ✅ **23TP19104 (SESD)**: ALL sections have 2 continuous hours, no lab rooms

---

## Course Configuration Requirements

For any course to get continuous scheduling without lab rooms:

1. **course_type**: Must be `THEORY` (not LAB)
2. **hours_per_week**: Set to number of total hours (e.g., 2)
3. **max_continuous_hours**: Set equal to hours_per_week (e.g., 2)
4. **lab_rooms**: Leave empty (no lab rooms assigned)

Example for TP courses:
```python
course_type = 'THEORY'
hours_per_week = 2
max_continuous_hours = 2
lab_rooms = []  # Empty
```

---

## How It Works

### Detection Logic
The algorithm detects TP-type courses using this condition:
```python
if hours_per_week == max_continuous_hours and max_continuous_hours > 1:
    # This is a continuous theory course (like TP courses)
    # Schedule as ONE continuous block
```

### Scheduling Process
1. **Phase 3** of constraint scheduler handles continuous theory courses
2. Finds all available 2-hour continuous blocks using `_find_continuous_blocks()`
3. Filters blocks to avoid conflicts (section busy, instructor busy)
4. Selects first valid conflict-free block
5. Schedules ALL hours in that block at once
6. Sets room = None (no lab assignment)

### Why This Works
- Regular theory courses: `max_continuous_hours = 1`, scheduled hour-by-hour
- TP courses: `max_continuous_hours = 2 == hours_per_week`, scheduled as block
- Lab courses: `course_type = 'LAB'`, get lab rooms assigned
- TP courses: `course_type = 'THEORY'`, no lab rooms

---

## Files Modified

1. **SchedulerApp/views.py**
   - Line 305-349: Enhanced `addContinuousCourse()` with conflict detection
   - Line 489-501: Fixed fallback scheduling in `Schedule.initialize()`
   - Line 1383-1434: Modified `_schedule_theory_course()` for TP courses

2. **regenerate_for_tp_fix.py** (New)
   - Regeneration script with verification

3. **verify_tp_courses.py** (New)
   - Verification script for TP course configuration

---

## Testing

Run the verification script to check TP courses:
```bash
python verify_tp_courses.py
```

Regenerate timetables:
```bash
python regenerate_for_tp_fix.py
```

Or use the main generation:
```bash
python generate_sequential.py
```

---

## Summary

✅ **TP courses now work correctly:**
- Scheduled with 2 continuous hours on the same day
- No lab rooms assigned (Theory courses)
- All sections configured properly

✅ **No changes needed to database:**
- Courses already configured correctly as THEORY type
- Just needed algorithm fix to respect continuous scheduling

✅ **Backward compatible:**
- Regular theory courses (1 hour each) still work
- Lab courses (with lab rooms) still work
- Only affects courses where hours_per_week == max_continuous_hours > 1

---

**Status:** ✅ COMPLETE - All TP courses verified with 2 continuous hours and no lab rooms!
