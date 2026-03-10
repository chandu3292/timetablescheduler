# View Timetable Feature Documentation

## Overview
The View Timetable feature provides a comprehensive interface for viewing timetables with multiple filtering options. This allows users to view schedules from different perspectives based on their needs.

## Accessing the Feature

### From Navigation Menu
Click on **"View Timetable"** in the top navigation menu.

### From Home Page
Click the **"View Timetable"** button (green button) on the home page.

### Direct URL
Navigate to: `http://localhost:8000/timetable/view/`

## View Types

### 1. Section-wise View
**Purpose**: View the timetable for a specific section in a specific year.

**How to use**:
1. Click the "Section-wise" tab
2. Select a **Year** (e.g., "1st Year", "2nd Year")
3. Select a **Section** (1, 2, or 3)
4. Click "View Timetable"

**What you see**: A weekly timetable grid showing all classes for that section, including:
- Course codes
- Instructor names
- Room assignments (for labs)
- Time slots arranged by day and period

### 2. Year-wise View
**Purpose**: View the complete timetable for all sections in a year.

**How to use**:
1. Click the "Year-wise" tab
2. Select a **Year**
3. Click "View Timetable"

**What you see**: A combined timetable showing all classes across all sections for that year. Each class card shows:
- Course code
- Instructor name
- Year and section information
- Room assignment (if applicable)

### 3. Faculty-wise View
**Purpose**: View an individual faculty member's teaching schedule or all faculty schedules.

**How to use**:
**For a single faculty**:
1. Click the "Faculty-wise" tab
2. Select a **Faculty** from the dropdown
3. Click "View Timetable"

**For all faculties**:
1. Click the "Faculty-wise" tab
2. Check the box **"View All Faculties"**
3. Click "View Timetable"

**What you see**: 
- For single faculty: Their complete teaching schedule across all years and sections
- For all faculties: Combined view of all instructor assignments

### 4. Lab-wise View
**Purpose**: View lab room utilization schedules.

**How to use**:
**For a single lab**:
1. Click the "Lab-wise" tab
2. Select a **Lab** from the dropdown
3. Click "View Timetable"

**For all labs**:
1. Click the "Lab-wise" tab
2. Check the box **"View All Labs"**
3. Click "View Timetable"

**What you see**:
- For single lab: All classes scheduled in that lab throughout the week
- For all labs: Complete lab utilization schedule

### 5. Period-wise View (Faculty Availability)
**Purpose**: Find which faculty members are free at a specific time slot.

**How to use**:
1. Click the "Period-wise" tab
2. Select a **Day** (Monday through Saturday)
3. Select a **Time Period** (e.g., "8:45 - 9:45")
4. Click "Find Free Faculty"

**What you see**:
- **Free Faculty Section (Green)**: List of instructors who have no classes at that time
  - Faculty name
  - Faculty ID
  - Availability status
  
- **Busy Faculty Section (Red)**: List of instructors teaching at that time
  - Faculty name
  - Course they're teaching
  - Which year and section
  
- **Summary Counter**: Shows total count of free vs. busy faculty

## Features

### Visual Indicators
- **Regular Classes**: Light gradient background (teal/pink)
- **Lab Classes**: Yellow/orange gradient background
- **Elective Classes**: Purple gradient background

### Information Display
Each class card shows:
- **Course Code**: e.g., "IT211", "IT112"
- **Instructor Name**: Teaching faculty
- **Room**: Lab room name (for lab courses)
- **Section Info**: Year and section number (in combined views)

### Responsive Design
- Scrollable timetable grids for better mobile viewing
- Clean, modern interface with gradient styling
- Tab-based navigation for easy switching between view types

## Use Cases

### For Students
- **Section-wise**: View your section's complete weekly schedule
- **Year-wise**: See all sections in your year to compare schedules

### For Faculty
- **Faculty-wise**: Check your teaching schedule
- **Period-wise**: Find colleagues who are free for meetings or collaboration

### For Administration
- **Lab-wise**: Monitor lab utilization and avoid double-booking
- **Period-wise**: Schedule meetings, assign substitute teachers, or plan events
- **All views**: Generate reports, analyze workload distribution

### For Scheduling Coordinators
- **Section-wise**: Verify individual section schedules
- **Year-wise**: Ensure all sections have complete schedules
- **Faculty-wise**: Check instructor workload distribution
- **Lab-wise**: Verify labs are properly utilized
- **Period-wise**: Identify time slots for special events or makeup classes

## Tips

1. **Reset Filters**: Click the "Reset Filters" button to start over with a fresh view
2. **Print/Export**: Use your browser's print function (Ctrl+P) to save timetables as PDF
3. **Quick Navigation**: Use the tab buttons to quickly switch between different view types without reloading
4. **Checkboxes**: When viewing "All Faculties" or "All Labs", the individual selection dropdown is automatically disabled

## Technical Details

### URL Parameters
- `view_type`: Type of view (section, year, faculty, lab, period)
- `year`: Year ID
- `section`: Section number
- `faculty`: Instructor ID
- `all_faculties`: Boolean for viewing all faculties
- `lab`: Lab room ID
- `all_labs`: Boolean for viewing all labs
- `day`: Day of week
- `time`: Time slot

### Example URLs
```
# Section-wise view
/timetable/view/?view_type=section&year=11&section=1

# Faculty-wise view (all faculties)
/timetable/view/?view_type=faculty&all_faculties=true

# Period-wise view
/timetable/view/?view_type=period&day=Monday&time=8:45 - 9:45
```

## Troubleshooting

### "No classes found"
- Ensure timetables have been generated for the selected year
- Check that you have data for the selected filters

### "No faculty are free"
- This is normal during peak class hours
- Try different time slots

### Empty timetable grid
- Verify that the timetable has been generated (use Generate Timetable feature)
- Check that courses and instructors are properly assigned

## Future Enhancements
- Export to Excel/CSV
- Email schedules to faculty
- Calendar integration
- Mobile app with push notifications
- Department-wise filtering
- Custom time range selection
- Comparison view (compare multiple sections side-by-side)

## Support
For issues or questions, contact the system administrator.

---
**Last Updated**: March 2026  
**Version**: 1.0
