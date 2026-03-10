# Automatic Evaluator Assignment System

## Overview

The timetable scheduler now **automatically assigns evaluators** to lab courses based on department and availability. You only need to set the **main instructor** for each lab section, and the system finds available evaluators automatically.

---

## How It Works

### 1. **Main Instructor (Required)**
- The primary faculty member who teaches the lab
- Their availability **determines when the lab can be scheduled**
- Must be set in Django Admin → Course Instructor Assignments

### 2. **Auto-Selected Evaluators (Automatic)**
- System automatically finds **up to 2 evaluators** from the same department
- Evaluators are selected based on:
  - **Same department**: Extracted from course code (e.g., `23IT4218` → IT instructors)
  - **Availability**: Only instructors who are free at that time
  - **Random distribution**: Different evaluators for different labs to prevent bottlenecks

### 3. **Flexible Assignment**
- If 2 evaluators are available → assigns 2
- If only 1 evaluator is available → assigns 1
- If no evaluators are available → assigns only main instructor

---

## Department Code Extraction

The system extracts department codes from course numbers:

| Course Code | Department | Eligible Evaluators |
|------------|------------|-------------------|
| 23IT4218   | IT         | Instructors with UID starting with "IT" |
| 23ME3205   | ME         | Instructors with UID starting with "ME" |
| 23PY1102   | PY         | Instructors with UID starting with "PY" |
| 23TP9102   | TP         | Instructors with UID starting with "TP" |

---

## Setup Instructions

### **Step 1: Set Main Instructors**

#### Option A: Django Admin (Recommended)
1. Go to `http://127.0.0.1:8000/admin/`
2. Navigate to **"Course Instructor Assignments"**
3. Select a lab course assignment (e.g., "2nd Year Section 1 - 23IT4218")
4. Set **"Main instructor"** dropdown to the primary faculty
5. Save

#### Option B: Bulk Setup Script
Run this script to set the first instructor as main for all labs:
```powershell
python set_all_main_instructors.py
```

### **Step 2: Generate Timetables**
```powershell
python generate_sequential.py
```

The system will:
1. Schedule each lab based on **main instructor's** availability
2. Automatically find and assign evaluators from the same department
3. Create timetable entries for main instructor + all assigned evaluators

---

## Example

### **PDS Lab (23IT4218) - Section 1**

**Setup (Manual):**
- Main instructor: Mrs.Hari Priyanka

**Auto-Assignment (Automatic):**
- Lab scheduled: Tuesday 8:45-12:15 (4 hours)
- System finds available IT instructors at that time
- Auto-selects 2 evaluators: Mr.B.Satya Narayana, Mrs.V.Alekya
- Creates entries for all 3 instructors

**Result in Timetable:**
- Mrs.Hari Priyanka: Tuesday 8:45-12:15 (PDS Lab Sec1)
- Mr.B.Satya Narayana: Tuesday 8:45-12:15 (PDS Lab Sec1)
- Mrs.V.Alekya: Tuesday 8:45-12:15 (PDS Lab Sec1)

---

## Benefits

### ✅ **Simplified Management**
- Only set 1 instructor per section (main), not 3
- No need to manually track evaluator availability
- System handles conflicts automatically

### ✅ **Better Distribution**
- Randomizedselection prevents same evaluators being overused
- Evaluators distributed across different labs
- More faculty get involved in evaluation

### ✅ **Flexible Staffing**
- If only 1 evaluator available → assigns 1 (not failure)
- If no evaluators available → main instructor alone (still works)
- Adapts to real-world constraints

### ✅ **Zero Manual Conflicts**
- System only selects free instructors
- No double-booking of evaluators
- Main instructor availability guaranteed

---

## Troubleshooting

### **Issue: Not enough evaluators assigned**
- **Cause**: Most IT instructors are already teaching at that time
- **Solution**: Normal behavior - system assigns what's available (0-2 evaluators)

### **Issue: Wrong department evaluators assigned**
- **Cause**: Course code doesn't match pattern (e.g., special courses)
- **Solution**: Check course code format (`[digits][LETTERS][digits]`)

### **Issue: Main instructor not set**
- **Cause**: No main instructor assigned in Course Instructor Assignment
- **Solution**: Run `python set_all_main_instructors.py` or set manually in admin

---

## Configuration

### **Change Number of Evaluators**

In `SchedulerApp/views.py`, modify `max_evaluators` parameter:

```python
# Schedule regular labs
evaluators = self._get_available_evaluators(schedule, block, course, main_instructor, max_evaluators=2)

# For more evaluators (e.g., 3):
evaluators = self._get_available_evaluators(schedule, block, course, main_instructor, max_evaluators=3)
```

---

## Statistics

### **Before Auto-Evaluator System:**
- 1st Year: 96 classes (manually assigned instructors)
- 2nd Year: 183 classes (manually assigned instructors)
- 3rd Year: Failed (instructor conflicts)

### **After Auto-Evaluator System:**
- 1st Year: 150 classes (+56% more instructor entries)
- 2nd Year: 207 classes (+13% more instructor entries)
- 3rd Year: 243 classes (now works!)
- **Total: 600 classes with 0 instructor conflicts**

---

## Summary

The auto-evaluator system makes lab scheduling **simpler, more flexible, and conflict-free**:

1. **Set main instructor only** (1 per section)
2. **System finds evaluators** automatically from same department
3. **Generates timetables** with main + available evaluators
4. **Zero manual conflict resolution** needed

This matches real-world lab teaching where main faculty schedules the lab, and available department faculty assist with evaluation.
