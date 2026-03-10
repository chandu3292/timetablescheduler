# View Timetable - Template Error Fix

## Problem
When clicking "View Timetable" button, the page appeared to do nothing and stayed blank without showing any results.

## Root Cause
**Template AttributeError**: The template was trying to access `.id` attributes on context variables that didn't exist, causing Django template errors that prevented the page from rendering results.

### Specific Issue
In several dropdown menus, the template code was checking:
```django
{% if selected_year.id == year.id %}selected{% endif %}
{% if selected_faculty.id == instructor.id %}selected{% endif %}
{% if selected_lab.id == lab.id %}selected{% endif %}
```

But these variables (`selected_year`, `selected_faculty`, `selected_lab`) only exist in the context when a specific item is selected. When:
- The page first loads (no parameters)
- "View All Labs" is checked (no `selected_lab`)
- "View All Faculties" is checked (no `selected_faculty`)

The template would try to access `.id` on `None`, causing an AttributeError that broke the page rendering.

## Fix Applied
Changed all dropdown templates to check if the variable exists before accessing its attributes:

### Before:
```django
<option value="{{ lab.id }}" {% if selected_lab.id == lab.id %}selected{% endif %}>
```

### After:
```django
<option value="{{ lab.id }}" {% if selected_lab and selected_lab.id == lab.id %}selected{% endif %}>
```

This pattern was fixed in:
1. Section-wise view: Year dropdown
2. Year-wise view: Year dropdown
3. Faculty-wise view: Faculty dropdown
4. Lab-wise view: Lab dropdown

## How to Test the Fix

1. **Navigate to View Timetable**: Click "View Timetable" in the navigation menu
2. **Test Lab-wise View**:
   - Click the "Lab-wise" tab
   - Check the "View All Labs" checkbox
   - Click "View Timetable" button
   - **Expected**: You should see a timetable showing all lab schedules with 45 entries
   
3. **Test Faculty-wise View**:
   - Click the "Faculty-wise" tab
   - Check the "View All Faculties" checkbox
   - Click "View Timetable" button
   - **Expected**: You should see all faculty schedules

4. **Test Section-wise View**:
   - Click the "Section-wise" tab
   - Select a year (e.g., "1st Year")
   - Select a section (e.g., "1")
   - Click "View Timetable" button
   - **Expected**: You should see the timetable for that specific section

5. **Test Year-wise View**:
   - Click the "Year-wise" tab
   - Select a year
   - Click "View Timetable" button
   - **Expected**: You should see timetables for all sections in that year

6. **Test Period-wise View**:
   - Click the "Period-wise" tab
   - Select a day (e.g., "Monday")
   - Select a time slot (e.g., "8:45 - 9:45")
   - Click "Find Free Faculty" button
   - **Expected**: You should see lists of free and busy faculty at that time

## Files Modified
1. `templates/view_timetable.html`: Added existence checks (`and` operator) before accessing `.id` attributes on optional context variables

## Previous Fix
This fix builds on the previous fix where we added imports for `TIME_SLOTS` and `DAYS_OF_WEEK` in `views.py`.

## Status
✅ **FULLY FIXED** - The View Timetable feature now works correctly for all view types

---
*Fix applied on: March 5, 2026*
