# TIMETABLE SCHEDULING SYSTEM - COMPLETE ARCHITECTURE

## Project Overview
This is a **Timetable Scheduling System** using a **Genetic Algorithm** to automatically generate conflict-free class schedules. It's a Django-based web application that manages educational institutions' class scheduling.

---

## DATABASE ENTITIES & RELATIONSHIPS

### 1. **ROOM** 
**What it represents:** Physical classroom/lecture halls where classes will be held

**Fields:**
- `r_number` (String, max 6 chars) → Room identifier (e.g., "A101", "B205")
- `seating_capacity` (Integer) → How many students can sit in this room

**Example Data:**
```
Room A101 - Capacity: 50 students
Room A102 - Capacity: 40 students
Room B205 - Capacity: 60 students
```

---

### 2. **INSTRUCTOR**
**What it represents:** Teachers/Professors who teach courses

**Fields:**
- `uid` (String, max 6 chars) → Unique instructor ID (e.g., "INS001")
- `name` (String, max 25 chars) → Instructor's name (e.g., "Dr. Ahmed")

**Example Data:**
```
ID: INS001, Name: Dr. Ahmed
ID: INS002, Name: Mrs. Fatima
ID: INS003, Name: Prof. Hassan
```

---

### 3. **MEETING TIME**
**What it represents:** When classes happen (day + time slot combination)

**Fields:**
- `pid` (String, max 4 chars, PRIMARY KEY) → Period ID (e.g., "MWF1")
- `day` (String) → Day of week → Choose from: Monday, Tuesday, Wednesday, Thursday, Friday
- `time` (String) → Time slot → Choose from:
  - 8:45 - 9:45
  - 10:00 - 11:00
  - 11:00 - 12:00
  - 1:00 - 2:00
  - 2:15 - 3:15

**Example Data:**
```
Period ID: P001 → Monday, 8:45-9:45
Period ID: P002 → Monday, 10:00-11:00
Period ID: P003 → Tuesday, 8:45-9:45
Period ID: P004 → Wednesday, 1:00-2:00
Period ID: P005 → Friday, 2:15-3:15
```

---

### 4. **COURSE**
**What it represents:** A subject/class that students take (e.g., Mathematics, Physics)

**Fields:**
- `course_number` (String, max 5 chars, PRIMARY KEY) → Course code (e.g., "CS101")
- `course_name` (String, max 40 chars) → Course title (e.g., "Introduction to Programming")
- `max_numb_students` (String) → Maximum enrollment capacity
- `instructors` (Many-to-Many) → One course can have multiple instructors

**Example Data:**
```
Code: CS101, Name: "Introduction to Programming", Max Students: 50
Instructors: [INS001, INS002]

Code: MTH201, Name: "Calculus II", Max Students: 40
Instructors: [INS003]

Code: PHY101, Name: "Physics I", Max Students: 60
Instructors: [INS001, INS004]
```

---

### 5. **DEPARTMENT**
**What it represents:** Academic department (e.g., Computer Science, Mathematics)

**Fields:**
- `dept_name` (String, max 50 chars) → Department name (e.g., "Computer Science Department")
- `courses` (Many-to-Many) → Courses offered by this department

**Example Data:**
```
Department: Computer Science
Courses: [CS101, CS201, CS301]

Department: Mathematics  
Courses: [MTH101, MTH201, MTH301]

Department: Physics
Courses: [PHY101, PHY201]
```

---

### 6. **SECTION**
**What it represents:** A specific group of students in a year (e.g., Section A of 1st year CS)

**Fields:**
- `section_id` (String, max 25 chars, PRIMARY KEY) → Section identifier (e.g., "CS-1A")
- `department` (Foreign Key) → Which department this section belongs to
- `num_class_in_week` (Integer) → How many classes this section needs per week
- `course` (Foreign Key, optional) → Currently assigned course
- `meeting_time` (Foreign Key, optional) → Currently assigned meeting time
- `room` (Foreign Key, optional) → Currently assigned room
- `instructor` (Foreign Key, optional) → Currently assigned instructor

**Example Data:**
```
Section ID: CS-1A
Department: Computer Science
Classes per week: 12
(Will be assigned 12 class slots from CS department's courses)

Section ID: CS-2B
Department: Computer Science
Classes per week: 10

Section ID: MTH-1A
Department: Mathematics
Classes per week: 8
```

---

## ENTITY RELATIONSHIPS (Database Schema)

```
┌─────────────────┐
│   DEPARTMENT    │
│─────────────────│
│ dept_name (PK)  │
└────────┬────────┘
         │ (1 to Many)
         │
    ┌────▼────┐
    │ SECTION │
    ├─────────┤
    │section_ │
    │id (PK)  │
    │num_class│
    └────┬────┘
         │
    ┌────┴─────────┐
    │              │
    │        (Many-to-Many for assignment)
    │
┌───▼────────┐  ┌─────────────────┐
│   COURSE   │  │   MEETING TIME  │
├────────────┤  ├─────────────────┤
│course_     │  │ pid (PK)        │
│number (PK) │  │ day             │
│course_name │  │ time            │
└────┬───────┘  └─────────────────┘
     │
     │ (Many-to-Many)
     │
┌────▼───────┐   ┌──────────┐
│ INSTRUCTOR │   │   ROOM   │
├────────────┤   ├──────────┤
│ uid        │   │r_number  │
│ name       │   │seating_  │
└────────────┘   │capacity  │
                 └──────────┘
```

---

## APPLICATION WORKFLOW

### **Step 1: Setup Phase (Admin)**
User adds basic data to the system:

1. **Add Rooms** (Physical Classrooms)
   - Input: Room number, seating capacity
   - Example: Room A101 with 50 seats

2. **Add Instructors** (Teachers)
   - Input: Instructor ID, name
   - Example: INS001 - Dr. Ahmed

3. **Add Meeting Times** (Schedule Slots)
   - Input: Period ID, day, time
   - Example: P001 on Monday 8:45-9:45

4. **Add Courses** (Subjects)
   - Input: Course number, name, max students, instructors
   - Example: CS101 with max 50 students taught by INS001, INS002

5. **Add Departments** (Academic Units)
   - Input: Department name, courses
   - Example: CS Dept with [CS101, CS201, CS301]

6. **Add Sections** (Student Groups)
   - Input: Section ID, department, classes per week
   - Example: CS-1A needs 12 classes per week

---

### **Step 2: Timetable Generation Phase (Genetic Algorithm)**

When user clicks "Generate Timetable":

#### **Step 2A: Data Collection**
The system loads all data from database:
- All Rooms (10 rooms)
- All Meeting Times (25 time slots)
- All Instructors (15 instructors)
- All Courses (50 courses)
- All Departments (5 departments)
- All Sections (20 sections)

#### **Step 2B: Initial Population Creation**
Creates 30 random schedules (POPULATION_SIZE = 30)

**For each section (e.g., CS-1A):**
- Calculate how many classes needed: 12 classes
- Get department's courses: [CS101, CS201, CS301]
- Distribute courses among 12 slots:
  - Each course appears 12÷3 = 4 times
  - Excess 0 times randomly distributed

**For each class, randomly assign:**
- Meeting Time: Pick random from 25 available times
- Room: Pick random from 10 available rooms
- Instructor: Pick random from course's instructors

**Example Initial Schedule:**
```
Section CS-1A Classes:
1. CS101 | Monday 8:45 | Room A101 | Dr. Ahmed
2. CS201 | Tuesday 10:00 | Room B205 | Prof. Hassan
3. CS301 | Wednesday 1:00 | Room A102 | Dr. Fatima
... (12 total for CS-1A)

Section CS-2B Classes:
1. CS101 | Thursday 2:15 | Room B205 | Dr. Ahmed
... (10 total for CS-2B)
```

#### **Step 2C: Evaluate Schedules (Calculate Fitness)**
For each schedule, count conflicts:

**Conflict Rules:**
1. **Room Capacity Conflict**
   - If room capacity < course max students → conflict++
   - Example: Course CS101 has 60 students but assigned to Room A101 (50 capacity)

2. **Duplicate Course on Same Day**
   - Same course can't be scheduled twice on same day
   - Example: CS101 at Monday 8:45 AND Monday 10:00 → conflict

3. **Instructor Double Booking**
   - Same instructor can't teach different sections at same time
   - Example: Dr. Ahmed teaching CS-1A at Monday 8:45 AND CS-2B at Monday 8:45

4. **Section Time Conflict**
   - Same section can't have 2 classes at same time
   - Example: CS-1A at Monday 8:45 in Room A101 AND Monday 8:45 in Room B205

**Fitness Score:**
```
Fitness = 1 / (Total Conflicts + 1)

Example:
- If 0 conflicts → Fitness = 1 / (0 + 1) = 1.0 (Perfect!)
- If 5 conflicts → Fitness = 1 / (5 + 1) = 0.167
- If 10 conflicts → Fitness = 1 / (10 + 1) = 0.091
```

#### **Step 2D: Genetic Algorithm Evolution (Up to 100 generations)**

**Generation Loop:**
Each generation improves the best schedule.

**Elite Selection:**
- Top 2 best schedules automatically pass to next generation (no changes)

**Crossover (Create new schedules):**
1. Select random 8 schedules from current population
2. Pick best from those 8 as "Parent X"
3. Repeat: Pick best from different random 8 as "Parent Y"
4. Combine genes:
   - For each class slot: 50% take from Parent X, 50% from Parent Y
   - Creates child schedule

**Mutation (Random changes):**
- For each child schedule (not elite ones)
- For each class: 5% chance to re-randomize that assignment
- Prevents getting stuck in local optimum

**Example Evolution:**
```
Generation 0: Best Fitness = 0.50 (10 conflicts)
Generation 1: Best Fitness = 0.60 (5 conflicts) ✓ Better!
Generation 2: Best Fitness = 0.67 (4 conflicts) ✓ Better!
...
Generation 15: Best Fitness = 1.0 (0 conflicts) ✓ PERFECT! Stop.
```

#### **Step 2E: Display Results**
Once perfect schedule found (or 100 generations reached), show:
- All class assignments with:
  - Section
  - Department
  - Course (name + number + max students)
  - Room (number + capacity)
  - Instructor (name + ID)
  - Meeting Time (day + time)

---

## CODE COMPONENTS BREAKDOWN

### **Classes in views.py**

#### **1. Data Class**
**Purpose:** Central access point to database
**Loads:** Rooms, Meeting Times, Instructors, Courses, Departments, Sections
```python
data = Data()
data.get_rooms()      # Returns all 10 rooms
data.get_courses()    # Returns all 50 courses
```

#### **2. Class Class**
**Purpose:** Represents a single scheduled class
**Contains:**
- Department
- Section
- Course
- Instructor (assigned)
- Meeting Time (assigned)
- Room (assigned)

#### **3. Schedule Class**
**Purpose:** Complete timetable (collection of classes for all sections)
**Methods:**
- `initialize()` → Creates random schedule
- `calculateFitness()` → Counts conflicts
- `getFitness()` → Returns fitness score (0-1)

#### **4. Population Class**
**Purpose:** Collection of 30 different schedules
**Contains:** 30 Schedule objects

#### **5. GeneticAlgorithm Class**
**Purpose:** Improves schedules over generations
**Methods:**
- `evolve()` → Create next generation
- `_crossoverPopulation()` → Combine best schedules
- `_mutatePopulation()` → Add random changes
- `_tournamentPopulation()` → Tournament selection

---

## USER INTERFACE FLOW

### **Admin Pages:**
1. **instructorAdd.html** → Add new instructor
2. **instructorEdit.html** → View/delete instructors
3. **roomAdd.html** → Add new room
4. **roomEdit.html** → View/delete rooms
5. **meetingTimeAdd.html** → Add meeting times
6. **meetingTimeEdit.html** → View/delete times
7. **courseAdd.html** → Add courses
8. **courseEdit.html** → View/delete courses
9. **departmentAdd.html** → Add departments
10. **departmentEdit.html** → View/delete departments
11. **sectionAdd.html** → Add sections
12. **sectionEdit.html** → View/delete sections

### **Main Page:**
13. **index.html** → Home/navigation
14. **timetable.html** → Display final schedule

---

## EXAMPLE SCENARIO - COMPLETE FLOW

### **Input Setup:**
```
ROOMS:
- A101 (50 seats)
- A102 (40 seats)
- B205 (60 seats)

INSTRUCTORS:
- INS001: Dr. Ahmed
- INS002: Mrs. Fatima

MEETING TIMES:
- P001: Monday 8:45-9:45
- P002: Monday 10:00-11:00
- P003: Tuesday 8:45-9:45
- P004: Wednesday 1:00-2:00

COURSES:
- CS101: Intro to Programming (Max 50, taught by INS001, INS002)
- CS201: Data Structures (Max 40, taught by INS002)

DEPARTMENT:
- Computer Science: [CS101, CS201]

SECTIONS:
- CS-1A: Needs 4 classes per week
- CS-2B: Needs 4 classes per week
```

### **Initial Schedule (Random):**
```
CS-1A Classes:
1. CS101 | Monday 8:45 | A101 | Dr. Ahmed
2. CS201 | Monday 10:00 | A102 | Mrs. Fatima
3. CS101 | Tuesday 8:45 | B205 | Mrs. Fatima
4. CS201 | Wednesday 1:00 | A101 | Mrs. Fatima

CS-2B Classes:
1. CS101 | Monday 8:45 | B205 | Dr. Ahmed (CONFLICT! Same time as CS-1A CS101)
2. CS201 | Monday 10:00 | A101 | Mrs. Fatima (CONFLICT! Same time as CS-1A CS201)
3. CS101 | Tuesday 8:45 | A102 | Dr. Ahmed
4. CS201 | Wednesday 1:00 | B205 | Mrs. Fatima (CONFLICT! Same time as CS-1A CS201)

Fitness = 1 / (3 + 1) = 0.25 (Poor!)
```

### **After Evolution (Generation 5):**
```
CS-1A Classes:
1. CS101 | Monday 8:45 | A101 | Dr. Ahmed
2. CS201 | Monday 10:00 | A102 | Mrs. Fatima
3. CS101 | Tuesday 8:45 | B205 | Mrs. Fatima
4. CS201 | Wednesday 1:00 | A101 | Mrs. Fatima

CS-2B Classes:
1. CS101 | Tuesday 10:00 | B205 | Dr. Ahmed (No conflict!)
2. CS201 | Wednesday 8:45 | A102 | Mrs. Fatima (No conflict!)
3. CS101 | Thursday 1:00 | A101 | Dr. Ahmed (No conflict!)
4. CS201 | Friday 8:45 | B205 | Mrs. Fatima (No conflict!)

Fitness = 1 / (0 + 1) = 1.0 (PERFECT!)
```

---

## CONSTRAINTS & RULES

The system ensures:
1. ✅ No room is over-booked (capacity check)
2. ✅ No instructor teaches two classes at same time
3. ✅ No section has overlapping classes
4. ✅ Each section gets required number of classes per week
5. ✅ Each section's classes use only their department's courses
6. ✅ Courses are evenly distributed across sections

---

## GENETIC ALGORITHM PARAMETERS

```python
POPULATION_SIZE = 30                    # 30 schedules per generation
NUMB_OF_ELITE_SCHEDULES = 2             # 2 best schedules always survive
TOURNAMENT_SELECTION_SIZE = 8           # Pick best from random 8
MUTATION_RATE = 0.05                    # 5% chance of random change
MAX_GENERATIONS = 100                   # Stop after 100 generations
IDEAL_FITNESS = 1.0                     # Perfect score (no conflicts)
```

---

## KEY INSIGHT

**The system automatically finds the BEST possible timetable by:**
1. Starting with random schedules
2. Keeping the best ones each generation
3. Mixing good schedules together (crossover)
4. Making small random improvements (mutation)
5. Repeating until perfect or giving up after 100 tries

It's like "natural selection" for timetables! 🧬📅
