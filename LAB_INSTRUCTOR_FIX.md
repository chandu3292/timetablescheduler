# Lab Instructor Assignment Fix

## Problem
The current system incorrectly assigns lab instructors using batch splitting, where:
- Labs are divided into batches (A, B, C)
- Each batch gets a different instructor
- Students are physically separated

## Correct Requirement

### 1st Year Labs:
- **ONE instructor only**
- No evaluators
- No batch splitting

### 2nd, 3rd, 4th Year Labs:
- **ONE main instructor** (fixed for the course-section)
- **1-2 evaluators** (based on availability)
- All instructors present at the **same time**
- All students attend together (no batch splitting)
- Evaluators **must be from the same department** as the course

## Implementation Changes

### Model Changes (COMPLETED ✅)
1. Added `Instructor.department` field
2. Added `Course.dept_code` field  
3. Added `TimetableEntry.is_evaluator` field

### Scheduling Logic Changes (TODO):

1. **Detect course department automatically**:
   - Extract from course code (e.g., "23IT4215" → "IT", "23EC3201" → "EC")

2. **Modify lab scheduling**:
   - For 1st Year: Assign ONLY main instructor
   - For 2nd-4th Year: Assign main instructor + find available evaluators from same department

3. **Remove batch splitting**:
   - All labs use `batch='FULL'`
   - Multiple TimetableEntry rows for same time slot represent co-teaching (not batch splits)

4. **Evaluator selection**:
   - Check evaluator's department matches course department
   - Check evaluator is available (not teaching another class at same time)
   - Limit to 1-2 evaluators per lab session

## Files Modified
- `SchedulerApp/models.py`: Added new fields
- `SchedulerApp/migrations/0027_auto_20260308_2312.py`: Migration created
- Database: Migration applied ✅

## Next Steps
1. Update department codes for existing courses in database
2. Update department codes for existing instructors
3. Modify `_schedule_lab_course()` in views.py
4. Modify `_get_available_evaluators()` to filter by department
5. Remove/disable batch splitting logic
6. Regenerate timetables with new logic
