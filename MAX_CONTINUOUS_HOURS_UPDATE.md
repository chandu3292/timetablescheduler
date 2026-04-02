# MAX CONTINUOUS HOURS PER DAY - ENFORCEMENT UPDATE

## Changes Made

Updated the timetable scheduling system to enforce `max_continuous_hours` as a **strict limit per day**, not just for consecutive periods.

### What Changed

**Before:**
- ✗ Gap-filling only checked if periods were consecutive
- ✗ A course could have more than max_continuous_hours on a day if they weren't consecutive
- ✗ Example: Course with max_continuous=2 could have 4 periods on Monday (8:45, 10:35, 1:05, 2:45)

**After:**
- ✅ Gap-filling checks TOTAL hours on each day
- ✅ A course CANNOT exceed max_continuous_hours on any single day
- ✅ Example: Course with max_continuous=2 can have MAX 2 periods on Monday (regardless of timing)

### Updated Methods

#### 1. `_schedule_theory_course()` - Gap-Filling Phase 1 (Line ~1680)
```python
# NEW CHECK: Total hours on this day
hours_on_day = day_hours[mt.day]
if hours_on_day >= max_continuous:
    logger.debug(f"Day limit reached ({hours_on_day}/{max_continuous})")
    continue
```

#### 2. `_schedule_theory_course()` - Gap-Filling Phase 2 (Line ~1710)
```python
# CRITICAL: Still respect day limit even in ultra-relaxed mode
hours_on_day = day_hours[mt.day]
if hours_on_day >= max_continuous:
    logger.debug(f"Day limit reached ({hours_on_day}/{max_continuous})")
    continue
```

#### 3. `_force_schedule_single_hour()` (Line ~1845)
```python
# Count current hours per day
day_hours = defaultdict(int)
for cls in schedule._classes:
    if (cls.section_number == section and cls.course == course):
        day_hours[cls.meeting_time.day] += 1

# Respect day limit
if day_hours[mt.day] >= max_continuous:
    continue
```

## Behavior After Update

### Constraint Hierarchy

1. **HARD CONSTRAINTS** (Never violated):
   - No instructor conflicts
   - No room conflicts
   - No section conflicts
   - **Max hours per day = max_continuous_hours** ⭐ NEW

2. **SOFT CONSTRAINTS** (Relaxed if needed):
   - Consecutive periods (can be non-consecutive)
   - Day distribution preferences
   - Instructor period priorities

### Examples

#### Example 1: Course with max_continuous_hours = 2
```
✅ ALLOWED:
Monday: 8:45-9:45, 9:45-10:35 (2 hours, consecutive)
Tuesday: 1:05-1:55, 2:45-3:35 (2 hours, non-consecutive)

❌ NOT ALLOWED:
Monday: 8:45-9:45, 9:45-10:35, 1:05-1:55 (3 hours > max 2)
```

#### Example 2: TP Course with max_continuous_hours = 2, hours_per_week = 2
```
✅ ALLOWED:
Monday: 8:45-9:45, 9:45-10:35 (2 hours, consecutive - preferred)
OR
Monday: 8:45-9:45 (1 hour)
Tuesday: 10:35-11:25 (1 hour - non-consecutive across days)

❌ NOT ALLOWED:
Monday: 8:45-9:45, 9:45-10:35, 10:35-11:25 (3 hours > max 2)
```

## Gap-Filling Strategy

When filling empty slots in the timetable:

1. **Check instructor availability** ✅
2. **Check section conflicts** ✅
3. **Check hours on that day** ✅ NEW
   - If course already has max_continuous_hours on that day → Skip
   - Try a different course instead
4. **Prefer consecutive periods** (Phase 1)
5. **Allow non-consecutive if needed** (Phase 2)

## Benefits

✅ **Better schedule distribution**: Courses spread across more days
✅ **Respects course limits**: No course exceeds its designed max hours per day
✅ **Student-friendly**: Prevents too many hours of the same subject in one day
✅ **Still fills gaps**: Can use non-consecutive slots if needed

## Testing Recommendation

After regenerating the timetable, verify:

```bash
# Check for violations
python find_theory_violations.py

# Expected output: "No theory course violations found!"
```

## Notes

- Lab courses still show 9 entries for a 3-hour block (3 instructors × 3 hours)
- This is CORRECT - it's not a violation, it's multiple instructors teaching simultaneously
- Theory courses are the ones that this update affects

---

**Update Date**: March 11, 2026
**Impact**: All gap-filling logic now respects max_continuous_hours as a day limit
**Backwards Compatible**: Yes - existing schedules won't be affected until regenerated
