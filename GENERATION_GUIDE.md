# TIMETABLE GENERATION GUIDE

## Two Generation Approaches

Your timetable system supports TWO ways to generate timetables, each for different situations:

### 1. **Full Regeneration** (Start of Academic Year)
**When to use:** Beginning of academic year, major changes to all years

**Script:** `python generate_sequential.py`

**What it does:**
- ✅ Clears ALL existing timetables (all years)
- ✅ Generates ALL years fresh: 1st → 2nd → 3rd → 4th
- ✅ Zero main instructor conflicts (checked via database)
- ⚠️  May have some evaluator overlaps (evaluators auto-selected without cross-year checking)

**Results:**
- Total classes: ~564
- Instructor conflicts: 0 (main instructors only)
- Room conflicts: 0
- Section conflicts: 0

### 2. **Single-Year Regeneration** (Mid-Year/Semester Changes)
**When to use:** One year's semester ends, need to regenerate only that year

**Script:** `python regenerate_single_year.py "YEAR_NAME"`

**Examples:**
```bash
python regenerate_single_year.py "1st Year"
python regenerate_single_year.py "2nd Year"  
python regenerate_single_year.py "3rd Year"
```

**What it does:**
- ✅ Deletes only the specified year's timetable
- ✅ Other years remain untouched
- ✅ Generates new timetable for that year only
- ⚠️  May fail if instructors are over-committed across years

**Important Notes:**
1. The script will ask for confirmation before deleting existing entries
2. Other years' timetables are NOT affected
3. If generation fails, check instructor assignments (see below)

## Understanding Conflicts

### Types of Overlaps

1. **Main Instructor Conflicts** ❌ CRITICAL
   - One instructor teaching 2+ classes at the same time
   - Example: Dr. Smith teaching both 2nd Year Lab AND 3rd Year Theory at Monday 9:00
   - **Impact:** Instructor physically cannot be in two places
   
2. **Evaluator Overlaps** ⚠️ ACCEPTABLE (in some cases)
   - Lab evaluators assigned to multiple labs at same time
   - Example: Prof. Kumar evaluating 2nd Year DBMS Lab AND 3rd Year IOT Lab simultaneously
   - **Impact:** Depends on your institution's flexibility
   
3. **Lab Room Conflicts** ❌ CRITICAL
   - Same lab room scheduled for 2+ classes simultaneously  
   - Example: NS Lab used by both 2nd Year CN Lab AND 3rd Year Cryptography Lab at Tuesday 10:00
   - **Impact:** Physical space cannot accommodate both classes

### Checking for Overlaps

After generation, run the comprehensive overlap checker:

```bash
python check_overlaps.py
```

This reports:
- Instructor overlaps (both main instructors and evaluators)
- Lab room conflicts
- Section double-bookings

## Single-Year Regeneration Strategy

### Prerequisites

**BEFORE regenerating a single year, review:**

1. **Main Instructor Assignments**
   - Go to Django Admin → Course Instructor Assignments
   - Filter by the year you're regenerating
   - Check which instructors are marked as "Main Instructor"
   - Verify they're NOT main instructors for other years at conflicting times

2. **Lab Room Availability**
   -Check if labs are available or being used by other years   - Specialized labs (IOT Lab, NS Lab, CAD Lab) are shared resources

3. **Shared Instructors**
   - Identify instructors teaching BOTH the year you're regenerating AND other years
   - These are high-risk for conflicts

### Workflow

```
[User's Real-World Scenario]
Semester ends for 2nd Year → Need to update 2nd Year timetable only

Step 1: Review instructor assignments
   - Check who teaches 2nd Year
   - Identify overlaps with 1st/3rd year
   - Adjust assignments if needed (remove conflicting ones)

Step 2: Run single-year regeneration
   python regenerate_single_year.py "2nd Year"

Step 3: Check for overlaps
   python check_overlaps.py
   
Step 4: If overlaps found:
   Option A: Re-assign instructors and regenerate again
   Option B: Accept evaluator overlaps (if institutionally acceptable)
   Option C: Do full regeneration (if conflicts are extensive)
```

### Handling Generation Failures

If single-year regeneration fails:

**Error: "Could not generate timetable"**

**Likely causes:**
1. Too many shared instructors with other years
2. Not enough lab rooms available
3. Continuous lab hours conflicting with other years' labs

**Solutions:**
1. **Reduce cross-year sharing:**
   - Assign different main instructors for the problem year
   - Use instructors who are free (not teaching other years)

2. **Relax lab constraints:**
   - Reduce `max_continuous_hours` for some lab courses
   - Split labs into smaller batches if possible

3. **Fall back to full regeneration:**
   ```bash
   python generate_sequential.py
   ```
   This clears everything and starts fresh

## Best Practices

### For IT Department Heads / Admins

1. **Start of Academic Year:**
   - Use `generate_sequential.py` for fresh start
   - Review and accept initial timetable
   - Minimal adjustments needed

2. **Mid-Year Changes:**
   - Use `regenerate_single_year.py "YEAR"`
   - Review conflicts before confirming
   - Be prepared to adjust instructor assignments

3. **Emergency Adjustments:**
   - If single-year fails repeatedly → use full regeneration
   - Document which instructors cause most conflicts
   - Plan future semesters with dedicated instructors per year

### Main Instructor Assignment Strategy

**Dedicated Approach** (Recommended):
- Assign instructors exclusively to ONE year
- Example: Dr. A teaches only 2nd Year, Dr. B teaches only 3rd Year
- **Benefit:** Single-year regeneration always succeeds

**Shared Approach** (Current):  
- Instructors teach across multiple years
- Example: Dr. Smith teaches 2nd Year AND 3rd Year
- **Challenge:** Single-year regeneration may fail or create conflicts
- **Mitigation:** Use full regeneration more frequently

## Technical Details

### What Gets Checked During Generation?

**Full Regeneration (generate_sequential.py):**
- ✅ Main instructor availability (within current generation)
- ✅ Lab room availability (within current generation)
- ✅ Section double-booking
- ❌ Cross-year evaluator conflicts (NOT checked - hence some overlaps)

**Single-Year Regeneration (regenerate_single_year.py):**
- ✅ Main instructor availability (checks database for other years)
- ✅ Lab room availability (checks database for other years)
- ✅ Section double-booking
- ⚠️  Evaluator availability (limited checking - may have overlaps)

### Why Evaluator Overlaps Happen

The auto-evaluator system:
1. Identifies department (IT, ME, PY) from course code
2. Finds available instructors from that department
3. Checks if they're free in the CURRENT generation
4. Does NOT comprehensively check if they're teaching other years

**Reason:** Evaluators are assistants/monitors, may be able to handle multiple labs if institutional policy allows.

**If your institution prohibits evaluator overlaps:**
- Manually review evaluator assignments after generation
- Remove overlapping evaluators via Django Admin
- Assign different evaluators who are truly free

## Summary

| Feature | Full Regeneration | Single-Year Regeneration |
|---------|------------------|------------------------|
| **Command** | `python generate_sequential.py` | `python regenerate_single_year.py "YEAR"` |
| **Affects** | All years | One year only |
| **Main Instructor Conflicts** | 0 | 0 (if successful) |
| **Evaluator Overlaps** | Possible | Possible  |
| **Lab Room Conflicts** | 0 | 0 (if successful) |
| **Success Rate** | ~100% | Varies (depends on constraints) |
| **Use When** | Start of year, major changes | Mid-semester, single year updates |

**Recommendation:** For your real-time semester-end workflow, use single-year regeneration as primary method. If it fails or creates too many conflicts, fall back to full regeneration.
