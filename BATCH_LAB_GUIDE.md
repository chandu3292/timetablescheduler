# Lab Batch Splitting & Rotation Guide

## Overview

This feature allows you to **split sections into 2 batches (B1 and B2)** for lab courses that use **batch rotation**. This is common for elective labs where students alternate between different labs on different days.

### Example from Your Timetable:
**III/IV B.Tech II Semester - IoT Lab & Cryptography Lab**

- **Tuesday**:
  - Batch 1 (B1) → IoT/App.Cryptography Lab
  - Batch 2 (B2) → PE-3 (or Cryptography Lab)
  
- **Another Day** (e.g., Friday):
  - Batch 1 (B1) → Cryptography Lab  
  - Batch 2 (B2) → IoT/App.Cryptography Lab

**Different instructors** can teach different batches on different days.

---

## How to Enable Batch Splitting

### Step 1: Mark Course as Batch-Split

1. Go to **Django Admin** → **Courses**
2. Select the lab course (e.g., "IoT Lab" or "Cryptography Lab")
3. Check the box **"Split into batches"**
4. Save the course

### Step 2: Create Batch Assignments

For each course that splits into batches, you need to create **LabBatchAssignment** records.

1. Go to **Django Admin** → **Lab Batch Assignments**
2. Click **"Add Lab Batch Assignment"**
3. Fill in the details:

#### Fields Explanation:

| Field | Description | Example |
|-------|-------------|---------|
| **Year** | The academic year | "III/IV B.Tech II Semester" |
| **Section Number** | Which section (1, 2, or 3) | 1 |
| **Course** | The lab course | "IoT Lab" |
| **Batch** | B1 or B2 | B1 |
| **Day** | Day of the week | Tuesday |
| **Instructor** | Instructor for this batch on this day | Mr. X |
| **Lab Room** | Lab room for this batch | Lab-101 |
| **Paired Course** | (Optional) The other lab running simultaneously | "Cryptography Lab" |

---

## Example Configuration

### Scenario: IoT Lab & Cryptography Lab Rotation

**Course Setup:**
1. Create course "IoT Lab" - Mark "Split into batches" = ✓
2. Create course "Cryptography Lab" - Mark "Split into batches" = ✓

**Batch Assignments for Section 1:**

#### Tuesday Assignments:
1. **IoT Lab - B1 - Tuesday**
   - Instructor: Mr. A
   - Lab Room: Lab-101
   - Paired Course: Cryptography Lab

2. **IoT Lab - B2 - Tuesday**  
   - Instructor: Mr. B
   - Lab Room: Lab-102
   - Paired Course: (leave empty or same)

3. **Cryptography Lab - B1 - Tuesday**
   - Instructor: Mr. C
   - Lab Room: Lab-102
   - Paired Course: IoT Lab

4. **Cryptography Lab - B2 - Tuesday**
   - Instructor: Mr. D
   - Lab Room: Lab-101
   - Paired Course: (leave empty or same)

#### Friday Assignments (Rotation):
5. **IoT Lab - B1 - Friday**
   - Instructor: Mr. E (different instructor!)
   - Lab Room: Lab-102
   - Paired Course: Cryptography Lab

6. **IoT Lab - B2 - Friday**
   - Instructor: Mr. F
   - Lab Room: Lab-101
   - Paired Course: (leave empty)

7. **Cryptography Lab - B1 - Friday**
   - Instructor: Mr. G
   - Lab Room: Lab-101
   - Paired Course: IoT Lab

8. **Cryptography Lab - B2 - Friday**
   - Instructor: Mr. H
   - Lab Room: Lab-102
   - Paired Course: (leave empty)

---

## How Scheduling Works

### When you generate a timetable:

1. **The scheduler reads LabBatchAssignment records** for courses marked with `split_into_batches=True`

2. **For each day with batch assignments:**
   - Finds available continuous time blocks on that day
   - Schedules B1 with its assigned instructor and lab
   - Schedules B2 with its assigned instructor and lab
   - Both batches run **at the same time** (parallel labs)

3. **The timetable displays:**
   ```
   IoT Lab [B1] (Mr. A, Lab-101)
   Cryptography Lab [B2] (Mr. D, Lab-101)
   ```

---

## Timetable Display

### Section View:
When viewing a section's timetable, you'll see batch information:

```
Tuesday 10:30-11:30
IoT Lab [B1] (Mr. A, Lab-101)
Cryptography Lab [B2] (Mr. D, Lab-101)
```

### Instructor View:
When viewing an instructor's timetable:

```
Tuesday 10:30-11:30
IoT Lab [B1] (III/IV B.Tech - Sec 1, Lab-101)
```

---

## Important Notes

### ✅ Requirements:
- Each batch assignment must have:
  - Unique combination of (Year, Section, Course, Batch, Day)
  - Assigned instructor
  - Assigned lab room

### ⚠️ Common Mistakes:
1. **Forgetting to mark course as "Split into batches"**
   - Solution: Check the box in Course settings

2. **Not creating assignments for both B1 and B2**
   - Solution: Create batch assignments for all batches

3. **Using same lab room for both batches at same time**
   - Solution: Assign different lab rooms to B1 and B2 on the same day

4. **Not specifying all required days**
   - Solution: If lab meets twice per week, create batch assignments for both days

### 🔍 Validation:
Before generating timetable:
1. Check that all courses with `split_into_batches=True` have LabBatchAssignment records
2. Verify that each day has assignments for both B1 and B2
3. Ensure no conflicts (same instructor/room at same time for different batches)

---

## Troubleshooting

### Problem: Batch splits not showing in timetable
**Solution:** 
- Verify course has `split_into_batches=True`
- Check LabBatchAssignment records exist
- Regenerate timetable

### Problem: "No LabBatchAssignment found" warning
**Solution:**
- Create batch assignments in Django Admin
- Ensure Year, Section, and Course match exactly

### Problem: Batches scheduled at different times
**Solution:**
- This is expected - batches on different days will be at different times
- Same day batches should be parallel (same time)

---

## Quick Setup Checklist

- [ ] Mark lab course as "Split into batches"
- [ ] Create LabBatchAssignment for B1 on Day 1
- [ ] Create LabBatchAssignment for B2 on Day 1  
- [ ] Create LabBatchAssignment for B1 on Day 2 (if labs meet twice/week)
- [ ] Create LabBatchAssignment for B2 on Day 2 (if labs meet twice/week)
- [ ] Assign different instructors/rooms as needed
- [ ] Generate timetable
- [ ] Verify batch display in section view

---

## Database Models

### Course Model
```python
split_into_batches = BooleanField(default=False)
```

### LabBatchAssignment Model
```python
year = ForeignKey(Year)
section_number = IntegerField(1-3)
course = ForeignKey(Course)
batch = CharField('B1' or 'B2')
day = CharField(DAYS_OF_WEEK)
instructor = ForeignKey(Instructor)
lab_room = ForeignKey(LabRoom)
paired_course = ForeignKey(Course, optional)
```

### TimetableEntry Model
```python
batch = CharField('B1', 'B2', or 'FULL')
```

---

## Support

If you encounter issues:
1. Check Django Admin logs
2. Verify all batch assignments are created correctly
3. Ensure course settings are correct
4. Regenerate timetable after making changes
