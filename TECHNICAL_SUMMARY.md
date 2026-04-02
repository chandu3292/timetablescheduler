# TIMETABLE SCHEDULER - TECHNICAL ARCHITECTURE SUMMARY

## 📋 PROJECT OVERVIEW

This is a **Django-based Educational Timetable Scheduling System** that automatically generates conflict-free class schedules for academic institutions using an evolved **Constraint-Based Scheduling approach** (previously used Genetic Algorithm, now migrated to deterministic constraint solving).

**Technology Stack:**
- **Framework:** Django 3.2.25 (Web application server)
- **Rendering:** xhtml2pdf 0.2.16 (PDF generation for timetables)
- **Database:** SQLite (Django ORM)
- **Algorithm Approach:** Constraint-Based Scheduling with Validation + Heuristics
- **Language:** Python 3.x

---

## 🎯 CORE TECHNICAL APPROACH

### PRIMARY METHODOLOGY: Constraint-Based Scheduling

**NOT Genetic Algorithm** - The codebase has evolved from GA to a **constraint-based approach** with:

1. **Hard Constraints** (MUST NOT be violated):
   - No instructor double-booking at same time
   - No section scheduling conflicts (same section at same time)
   - Labs MUST be continuous time blocks (cannot split)
   - Theory courses with continuous requirements (TP courses) MUST be on single day in continuous slots
   - Electives MUST sync to same times across all sections
   - Lunch break blocked (12:15-1:05)

2. **Soft Constraints** (optimization goals):
   - Theory subject distribution across days (avoid bunching)
   - Minimize gaps between daily classes
   - Fill timetable completely (maximize utilization)
   - Honor instructor time preferences
   - Even workload distribution per week

3. **Validation Strategy**:
   - Pre-validation before accepting schedules (`validate_continuous_theory_strict()`)
   - Fitness-based rejection for schedules violating hard constraints
   - Multi-attempt approach (MAX_ATTEMPTS = 30) to find feasible schedules

### Algorithm Flow

```
INITIALIZATION (Schedule Building)
    ↓
[PHASE 1] LAB COURSES (Highest Priority)
    - Continuous blocks mandatory
    - Batch assignments with rotations
    - Cannot cross lunch break
    ↓
[PHASE 2] ELECTIVE COURSES (Parallel Section Rule)
    - Must sync same times across sections
    - Continuous blocks if specified
    ↓
[PHASE 3] CONTINUOUS THEORY COURSES (TP Courses)
    - 2+ continuous hours required
    - must be on single day
    - Examples: 23TP9102, 23TP9103
    ↓
[PHASE 4] REGULAR THEORY COURSES
    - 1 hour per slot (no continuity requirement)
    - Distributed across days
    - Fills remaining gaps
    ↓
FITNESS CALCULATION (Multi-constraint Evaluation)
    - Hard constraint penalties (10,000 or 100 each)
    - Soft constraint penalties (20-80 points each)
    ↓
VALIDATION GATES
    - validate_continuous_theory_strict() → Reject if failed
    - validate_full_course_allocation() → Reject if incomplete
    ↓
ACCEPTANCE/RETRY
    - Accepted: Save to database
    - Rejected: Retry (up to 30 attempts)
```

---

## 🏗️ DATABASE SCHEMA

### Core Entities

| Entity | Purpose | Key Fields |
|--------|---------|-----------|
| **Year** | Academic year level | year_name, lunch_period, courses (M2M) |
| **Course** | Subject class | course_number (PK), course_type (THEORY/LAB/ELECTIVE), hours_per_week, max_continuous_hours, priority, split_into_batches |
| **Instructor** | Faculty member | uid, name, email, department, designation (PROF/ASSOC_PROF/ASST_PROF), user (auth) |
| **InstructorPriority** | Teaching time preferences | instructor (FK), day, period_1_priority...period_7_priority (1-7 scale) |
| **MeetingTime** | Scheduled time slot | pid (PK), day (Mon-Sat), time (8 slots/day), year (FK) |
| **LabRoom** | Physical lab space | lab_name, seating_capacity |
| **CourseInstructorAssignment** | Section-specific instructor mapping | year, section_number, course, main_instructor, instructors (M2M) |
| **LabBatchAssignment** | Batch rotation setup (B1/B2) | year, section_number, course, batch, session_number, instructors, lab_room, paired_course |
| **GeneratedTimetable** | Result storage | year (O2O), fitness_score, generation_count |
| **TimetableEntry** | Individual class entry | year, section, course, instructor, meeting_time, room, day, time |

### Relationships
```
Year ─────M2M────→ Course ←──M2M── Instructor
  │                   │
  ├→ MeetingTime       ├→ LabRoom
  └→ GeneratedTimetable   └→ InstructorPriority
                          └→ CourseInstructorAssignment
                             └→ LabBatchAssignment
```

### Time Slots Configuration (8 periods/day)
```
Period 1: 8:45 - 9:45
Period 2: 9:45 - 10:35
Period 3: 10:35 - 11:25
Period 4: 11:25 - 12:15
[LUNCH BREAK: 12:15 - 1:05]  ← Variable by year
Period 5: 1:05 - 1:55
Period 6: 1:55 - 2:45
Period 7: 2:45 - 3:35
```

---

## 📊 SCHEDULING PHASES BREAKDOWN

### Phase 1: Lab Courses (Critical Path)
**Priority:** HIGHEST - Run first because labs have most constraints

- **Requirements:**
  - Continuous time blocks (2+ consecutive periods)
  - Cannot cross lunch break
  - Specific lab room with batch rotation
  - May split sections into B1/B2 rotations
  
- **Algorithm:**
  - Find all valid continuous blocks on each day
  - Filter out blocks crossing/containing lunch
  - Prefer conflict-free blocks over conflicted ones (fallback)
  - Assign room from CourseInstructorAssignment

- **Example:**
  ```
  Course: IoT Lab (Sec 1) 
    - Hours/week: 2, Max continuous: 2
    → Assign: Wednesday 10:35-11:25 + 11:25-12:15 (2 consecutive)
    → Room: Lab-1
    → Instructors: Prof A, Prof B
  ```

### Phase 2: Elective Courses (Synchronization)
**Priority:** HIGH - Must run before theory to lock specific times

- **Key Rule:** All sections attend SAME time (synchronized)
  - Students from Sec1, Sec2, Sec3 all in same class
  - No duplicate instructor assignments
  
- **Algorithm:**
  - Pre-allocate single time slots (`elective_time_tracker`)
  - All sections cycle through pre-allocated times in order
  - Continuous blocks use unified time block
  
- **Example:**
  ```
  Course: General Studies (ELECTIVE)
    - Hours/week: 2, Max continuous: 1
    → Time Pool: [Mon 10:00, Tue 2:15]
    → Sec1: Mon 10:00, Sec2: Tue 2:15, Sec3: Mon 10:00
    → All attend together at allocated times
  ```

### Phase 3: Continuous Theory Courses (TP Courses)
**Priority:** MEDIUM-HIGH - Strict continuity requirement

- **Target:** Theory courses with max_continuous_hours > 1
- **Constraint:** hours_per_week == max_continuous_hours (e.g., 2==2, 3==3)
  - MUST be all continuous on ONE day
  - CANNOT split across days
  - Hard rejection if violated (penalty: 10,000)
  
- **Example:**
  ```
  Course: 23TP9102 (Theory - TP module)
    - Hours/week: 2, Max continuous: 2
    → MUST schedule as: Friday 8:45-9:45 + 9:45-10:35 (consecutive)
    → NOT acceptable: Friday 8:45 + Monday 10:35
  ```

- **Validation:**
  - `validate_continuous_theory_strict()` checks:
    - Single day only: len(days) == 1 ✓
    - Full hours: len(times) >= max_continuous ✓
    - Consecutive indices in slot_order ✓

### Phase 4: Regular Theory Courses (Gap Filling)
**Priority:** LOWEST - Fill remaining slots with distribution

- **Target:** Theory with max_continuous_hours == 1
- **Distribution Rule:** Spread 1-hour classes across DIFFERENT days
  - Avoid all hours on single day
  - Respect max_continuous_hours limit per day
  
- **Algorithm (slot selection):**
  1. Sort all days by hours already scheduled (ascending)
  2. Try days with fewest hours first
  3. Skip if day already has max_continuous_hours hours
  4. Find first available slot on preferred day
  5. If no slot found on preferred day, try other days
  6. Fall back to pure random if structured search fails
  
- **Example:**
  ```
  Course: CS101 (Regular Theory)
    - Hours/week: 4, Max continuous: 1
    → Distribution attempt:
      Day Mon: 1 hour (10:00-11:00) ✓
      Day Tue: 1 hour (8:45-9:45) ✓
      Day Wed: 1 hour (2:15-3:15) ✓
      Day Fri: 1 hour (11:00-12:00) ✓
    → NOT all on Monday!
  ```

---

## ⚙️ FITNESS CALCULATION (Constraint Evaluation)

### Conflict Scoring System

```python
fitness = 1 / (numberOfConflicts + 1)
```

**Perfect schedule:** fitness = 1.0 (0 conflicts)
**Poor schedule:** fitness = 0.01 (99 conflicts)

### Penalty Structure

| Category | Constraint | Penalty | Type |
|----------|-----------|---------|------|
| **HARD** | Instructor double-booking | +100 | HARD |
| **HARD** | Section time conflict | +100 | HARD |
| **HARD** | Lab non-continuous | +100 | HARD |
| **HARD** | TP course split across days | +10,000 | HARD |
| **HARD** | Elective not synchronized | +100 | HARD |
| **HARD** | Missing hours (incomplete) | +20 per hour | HARD |
| **SOFT** | All theory hours on one day | +80 | SOFT |
| **SOFT** | Exceeding max_continuous/day | +80 | SOFT |
| **SOFT** | Morning gap (-) | +20 per gap | SOFT |
| **SOFT** | Afternoon gap (-) | +20 per gap | SOFT |

**Gap Calculation:** Smart lunch-aware gap detection
```
Morning (before 12:15):   gaps = span - unique_slots
Afternoon (after 1:05):   gaps = span - unique_slots
Lunch break not considered a gap
```

### Example Constraint Evaluation

```
Schedule for CS-1A Section:
├─ CS101 (THEORY, 4 hrs/week): Mon 10:00, Tue 8:45, Wed 2:15, Fri 11:00
│   ├─ Distribution: 4 days ✓
│   ├─ Gap on Mon: 0 (single class)
│   ├─ Conflicts: 0
│
├─ 23TP9102 (TP THEORY, 2 hrs/week, continuous): Fri 8:45-9:45, 9:45-10:35
│   ├─ Same day: ✓
│   ├─ Continuous: ✓
│   ├─ Conflicts: 0
│
├─ IoT LAB (LAB, 2 hrs/week): Wed 10:35-11:25, 11:25-12:15
│   ├─ Continuous: ✓
│   ├─ No lunch crossing: ✓ (before lunch)
│   ├─ Conflicts: 0
│
└─ General Studies (ELECTIVE): Mon 10:00 (shared with Sec2, Sec3)
    └─ Synchronized: ✓

TOTAL CONFLICTS: 0 ✓
FITNESS: 1.0 ✓ (Perfect)
```

---

## 🔑 KEY DATA FLOW & ALGORITHMS

### Class Representation
```python
Class:
  - year: Year
  - section_number: 1, 2, or 3
  - course: Course object
  - instructor: Assigned instructor
  - meeting_time: MeetingTime slot
  - room: LabRoom (labs only) or None (theory)
  - batch: 'B1', 'B2', or 'FULL'
  - is_evaluator: Boolean (evaluator role tracking)
```

### Schedule Initialization Algorithm

```python
class Schedule:
  
  initialize():
    # Categorize courses
    lab_courses = courses.filter(type='LAB') sorted by priority DESC
    elective_courses = courses.filter(alignment_needed=True)
    continuous_theory = courses.filter(type='THEORY', max_continuous > 1)
    regular_theory = courses.filter(type='THEORY', max_continuous == 1)
    
    # Phase 1: Add all lab classes
    for section in [1,2,3]:
      for course in lab_courses:
        addContinuousCourse(course, section)
    
    # Phase 2: Add elective classes
    for section in [1,2,3]:
      for course in elective_courses:
        addContinuousCourse(course, section) if continuous
        addCourse(course, section) for remaining_hours
    
    # Phase 3: Add continuous theory
    for section in [1,2,3]:
      for course in continuous_theory:
        addContinuousCourse(course, section)
    
    # Phase 4: Add regular theory
    for section in [1,2,3]:
      for course in regular_theory:
        for hour in range(course.hours_per_week):
          addCourse(course, section)  # With day distribution
  
  addContinuousCourse(course, section):
    - Group meeting_times by day
    - Find all valid continuous blocks [i:i+max_continuous]
    - Filter out blocks containing/crossing lunch (12:15-1:05)
    - Separate into conflict-free and conflicted blocks
    - Prefer conflict-free blocks
    - Assign same room to all periods in block
    - Assign same instructor to all periods in block
  
  addCourse(course, section):
    - Select meeting_time based on:
      * Elective: Use pre-allocated time from tracker
      * Theory: 30% early-bias selection, 70% random
      * Distribution across days for regular theory
    - Assign instructor from CourseInstructorAssignment
    - Assign room for LAB courses only
    - Track day usage per course-section pair
```

### Meeting Time Selection Strategy
```python
# For ELECTIVE courses (synchronized):
if course in electives:
    mt = elective_time_tracker[course_number][section_index]
    # Cycle through pre-allocated times

# For THEORY courses (hierarchical):
if random.random() < 0.3:  # 30% chance
    # EARLY-BIAS: Prefer morning slots
    slot_order = [slots in chronological order]
    available_sorted = sort by slot_order
    weights = linear_decay([2.0, 1.8, 1.6, ...])  # Gentle bias
    mt = random.choices(available_sorted, weights)
else:
    # PURE RANDOM: Diversity
    mt = random.choice(available_meeting_times)
```

---

## 📈 GENERATION & VALIDATION FLOW

### Main Generation Entry Point
```
generate_timetable(year_id):
  1. Load year data (courses, sections, meeting times)
  2. Pre-allocate elective times (synchronization)
  3. ATTEMPT LOOP (MAX_ATTEMPTS = 30):
     a. Create new Schedule
     b. Call schedule.initialize()
     c. Validate: validate_full_course_allocation()
     d. Validate: validate_continuous_theory_strict()
     e. Calculate fitness
     f. If fitness == 1.0 OR all hours allocated:
        - Save to GeneratedTimetable
        - Save individual TimetableEntry records
        - Return SUCCESS
     g. Else: Retry from step 3a
  4. If all attempts fail:
     - Return error with best attempt's report
```

### Validation Functions

| Function | Purpose | Rejection Trigger |
|----------|---------|-------------------|
| `validate_full_course_allocation()` | Ensures all weekly hours scheduled | Any course has hours < hours_per_week |
| `validate_continuous_theory_strict()` | TP course integrity check | TP course split or non-continuous |
| `get_allocation_report()` | Diagnostic info | Returns detailed incomplete list |

### Retry Mechanism
- **Attempts:** 30 max
- **On Failure:** Log warning with allocation report
- **Best Effort:** Save best-attempt timetable if all fail
- **Rationale:** Constraint satisfaction is non-trivial; stochasticity helps exploration

---

## 🎭 COURSE TYPE DETAILS

### THEORY Courses (23IT5xxx, 23IT6xxx, Regular)
- **No room assignment** (classroom location flexible)
- **Instructor per section** (section-specific assignment)
- **Distribution:** Avoid bunching on single day
- **Examples:** CS101, Advanced Algorithms, Calculus

### LAB Courses (23IT5xxx Lab, etc.)
- **Strict continuity:** max_continuous_hours blocks
- **Lab room required:** Assigned from LabRoom pool
- **Batch rotation:** Optional B1/B2 split with session rotation
- **Cannot cross lunch**
- **Examples:** IoT Lab, Cryptography Lab

### ELECTIVE Courses (23IT6xxx, 23IT7xxx, Professional Electives)
- **Synchronized scheduling:** Same time for all sections
- **Multiple students together** across sections
- **No section separation** (students mix)
- **Continuous if applicable:**
- **Examples:** Open Electives, Professional Electives

---

## 🚀 ADVANCED FEATURES

### Instructor Priority System
- **7-period preference scale** (1=highest, 7=lowest)
- **Per-day settings** (Mon-Sat independent)
- **Priority mapping:** Maps timetable slots to teaching periods
- **Fallback integration:** Used in `ConstraintScheduler` (see views.py line 1100+)

### Elective Synchronization Mechanism
```python
elective_time_tracker = {
    "23IT6001_single": [mt1, mt2, mt3],  # Pre-allocated times
    "23IT6001_single_index": {},         # Current index per section
    "23IT6002_continuous": [block1],     # Continuous block
}
```
- **Single period:** Cycle through pool in order
- **Continuous block:** Use same block for all sections

### Batch Rotation (LabBatchAssignment)
- **Split sections into B1 and B2**
- **Session rotation:** Swap batches and labs each session
- **Paired courses:** B1→Lab1, B2→Lab2 (or vice versa next session)
- **Auto-scheduling:** Scheduler finds available slots

###特别期间 (Special Periods)
- **Counseling, Training, Sports, Library**
- **Apply to all sections** in a year
- **Continuous blocks supported**
- **High priority** (scheduled separately)

---

## 📦 CODE MODULE STRUCTURE

### Views.py (Core Algorithm)
- **Data class:** Database abstraction
- **Class class:** Single scheduled class entity
- **Schedule class:** Full timetable (30 per population)
- **ConstraintScheduler:** Advanced priority-based scheduler
- **Population class:** Legacy GA reference (deprecated)

### Models.py (Database)
- **Course:** Subject definition with constraints
- **Year:** Academic year + lunch config
- **Instructor:** Faculty with priorities
- **CourseInstructorAssignment:** Section-specific instructor mapping
- **LabBatchAssignment:** Batch rotation setup
- **GeneratedTimetable:** Result storage
- **TimetableEntry:** Individual class records

### Forms.py
- Course, Year, Instructor, Room forms
- Assignment forms for instructor-course mapping

### Admin.py
- Django admin interface for data entry
- Bulk operations for setup

---

## 🔬 DEPENDENCY ANALYSIS

### External Libraries
```
Django==3.2.25
  - ORM for database abstraction
  - Web framework and routing
  - Admin interface
  - User authentication
  - Migrations system

xhtml2pdf==0.2.16
  - PDF generation for timetable export
  - Converts HTML→PDF
```

### No AI/ML Libraries Used
- ❌ NumPy/SciPy
- ❌ PyTorch/TensorFlow
- ❌ Scikit-learn
- ❌ Genetic Algorithm libraries (evolved custom)

### Pure Python Standard Library
- `random` — Algorithm randomization
- `logging` — Debug/diagnostic logging
- `collections.defaultdict` — Tracking structures

---

## 💡 METHODOLOGY CLASSIFICATION

| Aspect | Value |
|--------|-------|
| **Algorithm Type** | Constraint-based heuristic search |
| **Constraint Satisfaction** | Hard + soft constraints |
| **Optimization** | Multi-objective (minimize conflicts, maximize distribution) |
| **Determinism** | Stochastic (randomization + retry) |
| **Search Strategy** | Exhaustive generation with validation |
| **Scalability** | O(sections × courses × meeting_times) |
| **Complexity** | NP-hard (educational scheduling is NPC) |

---

## 🎯 PROBLEM CLASSIFICATION

**This is an Educational Timetable Scheduling Problem (ETP):**

1. **Entities:** Courses, Instructors, Rooms, Time Slots, Sections
2. **Constraints:**
   - Resource conflicts (instructor, section, room)
   - Continuity requirements (labs, TP courses)
   - Synchronization (electives across sections)
   - Prefences (instructor time priorities)
3. **Objectives:**
   - Minimize conflicts (hard)
   - Optimize distribution (soft)
4. **Complexity:** NP-complete (exponential search space)

**Approach Chosen:** Constraint-based heuristic with deterministic phases + stochastic search

---

## 📊 Project Status & Evolution

### Architecture Evolution
```
v1: Pure Genetic Algorithm
   └→ Issues: Population needed large sampling
   
v2: GA + Constraint Validation
   └→ Issues: Time-heavy for large datasets
   
v3: Constraint-Based (CURRENT)
   └→ Phased scheduling (labs → electives → theory)
   └→ Hard constraint enforcement
   └→ Multi-attempt retry mechanism
   └→ Instructor priorities integrated
   └→ Elective synchronization improved
```

### Known Limitations
1. Max attempt cap (30) → Some configs may not converge
2. Stochastic approach → Non-deterministic (different runs ≠ same result)
3. No global optimization → Local optimum possible
4. Batch rotation complexity → Some edge cases unhandled

### Recent Improvements (Repository Notes)
- **Priority mapping:** Map time slots to teaching periods (7-period scale)
- **TP continuity:** Hard gate validation (reject if TP split)
- **Lunch-aware:** Skip blocks crossing lunch (12:15-1:05)

---

## 🧪 TESTING & VALIDATION

### Built-in Checks
- `validate_continuous_theory_strict()` → Hard gate
- `validate_full_course_allocation()` → Completeness check
- `get_allocation_report()` → Diagnostic report
- Fitness-based rejection → Soft constraint enforcement

### Test Files Present
```
test_generate.py
test_generate_simple.py
test_tp_continuity.py
verify_requires.py
verify_elective_lab_fix.py
debug_counting_issue.py
...and 30+ analysis scripts
```

### Key Metrics
- **Fitness Score:** 0.0 to 1.0 (1.0 = perfect)
- **Conflicts:** Count of violations
- **Hours Allocated:** Actual vs. required per course
- **Generation Count:** Number of schedules built

---

## 📝 SUMMARY TABLE

| Aspect | Technology |
|--------|-----------|
| **Framework** | Django 3.2.25 |
| **Algorithm** | Constraint-based scheduling with heuristics |
| **Search Strategy** | Multi-phase systematic + stochastic retry |
| **Constraint Handling** | Hard rejections + soft penalties |
| **Data Storage** | SQLite via Django ORM |
| **PDF Export** | xhtml2pdf |
| **Language** | Python 3.x |
| **Concurrency** | Single-threaded |
| **AI/ML Tech** | None (pure algorithmic) |
| **Optimization Method** | Multi-objective penalty-based |
| **Scalability** | Suitable for 100-500 course instances |

---

## 🎓 CONCLUSION

This is a **practical constraint-based scheduler** using sophisticated phased generation and validation strategies. Rather than using traditional AI/ML libraries or genetic algorithms, it employs:

1. **Deterministic Prioritization:** Labs → Electives → Continuous Theory → Regular Theory
2. **Stochastic Slot Filling:** Random + biased selection for diversity
3. **Hard Constraint Enforcement:** Immediate rejection of TP/elective/continuity violations
4. **Soft Constraint Optimization:** Fitness-based penalties for suboptimal distributions
5. **Multi-Attempt Search:** Retry mechanism to find valid configurations

This approach balances **solution quality** (no conflicts) with **computational efficiency** (reasonable generation time), making it suitable for real educational institutions handling 100-300 courses across 3-6 academic years.
