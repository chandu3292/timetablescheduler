from django.http.response import HttpResponse
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import *
from .forms import *
from .models import TIME_SLOTS, DAYS_OF_WEEK
from collections import defaultdict
import random
import logging

logger = logging.getLogger(__name__)

# CONSTRAINT-BASED SCHEDULING PARAMETERS (NO MORE GA!)
MAX_ATTEMPTS = 10  # Try building schedule up to 10 times if needed
VARS = {'generationNum': 0,
        'terminateGens': False}


class Population:
    def __init__(self, size):
        self._size = size
        self._data = data
        self._schedules = [Schedule().initialize() for i in range(size)]

    def getSchedules(self):
        return self._schedules


class Data:
    def __init__(self, year=None):
        self.elective_time_tracker = {}
        self._year = year
        if year:
            # Filtered by selected year
            self._meetingTimes = MeetingTime.objects.filter(year=year)
            self._instructors = Instructor.objects.all()
            self._courses = year.courses.all()  # Get courses from year's many-to-many relationship
            self._rooms = LabRoom.objects.all()  # Lab rooms are shared across all years
            self._sections = [1, 2, 3]  # Fixed 3 sections per year
        else:
            # Default (if no year selected)
            self._meetingTimes = MeetingTime.objects.all()
            self._instructors = Instructor.objects.all()
            self._courses = Course.objects.all()
            self._rooms = LabRoom.objects.all()
            self._sections = [1, 2, 3]  # Fixed 3 sections

    def get_rooms(self):
        return self._rooms

    def get_instructors(self):
        return self._instructors

    def get_courses(self):
        return self._courses

    def get_meetingTimes(self):
        return self._meetingTimes

    def get_sections(self):
        return self._sections
    
    def get_year(self):
        return self._year



class Class:
    def __init__(self, year, section_number, course, batch='FULL', is_evaluator=False):
        self.year = year
        self.course = course
        self.instructor = None
        self.meeting_time = None
        self.room = None
        self.section_number = section_number
        self.batch = batch  # B1, B2, or FULL (for non-split courses)
        self.is_evaluator = is_evaluator  # True if this instructor is an evaluator, False if main instructor

    def get_id(self):
        return self.section_number

    def get_year(self):
        return self.year


    def get_course(self):
        return self.course

    def get_instructor(self):
        return self.instructor

    def get_meetingTime(self):
        return self.meeting_time

    def get_room(self):
        return self.room

    def set_instructor(self, instructor):
        self.instructor = instructor

    def set_meetingTime(self, meetingTime):
        self.meeting_time = meetingTime

    def set_room(self, room):
        self.room = room


class Schedule:
    def __init__(self):
        self._data = None  # Will be set by caller
        self._classes = []
        self._numberOfConflicts = 0
        self._fitness = -1
        self._isFitnessChanged = True
        self.course_day_tracker = {} 
        


    def getClasses(self):
        self._isFitnessChanged = True
        return self._classes

    def getNumbOfConflicts(self):
        return self._numberOfConflicts

    def getFitness(self):
        if self._isFitnessChanged:
            self._fitness = self.calculateFitness()
            self._isFitnessChanged = False
        return self._fitness

    def addCourse(self, data, course, courses, year, section_number):

        newClass = Class(year, section_number, course, batch='FULL')

        meeting_times = list(data.get_meetingTimes())

        # --- DISTRIBUTE ACROSS WEEK for full timetable coverage ---
        # Try to spread classes across different days to fill the timetable evenly
        used_days = self.course_day_tracker.get((section_number, course.course_number), set())
        
        # Prefer NEW days to distribute workload across the week
        if used_days:
            # 70% chance to prefer NEW days (better distribution)
            # 30% chance to allow same day (if needed)
            if random.random() < 0.7:
                # Prefer days NOT yet used for this course
                all_days = set(mt.day for mt in meeting_times)
                unused_days = all_days - used_days
                if unused_days:
                    preferred_mt = [mt for mt in meeting_times if mt.day in unused_days]
                    available_mt = preferred_mt if preferred_mt else meeting_times
                else:
                    available_mt = meeting_times
            else:
                available_mt = meeting_times
        else:
            available_mt = meeting_times

        # NOTE: No section-busy filtering - GA handles conflicts through evolution
        
        # ELECTIVE → same time for all sections (MUST use pre-allocated time)
        if course.course_type == 'ELECTIVE':
            single_key = f"{course.course_number}_single"
            index_key = f"{course.course_number}_single_index"
            
            if single_key in data.elective_time_tracker:
                # Get the list of pre-allocated times
                time_list = data.elective_time_tracker[single_key]
                
                # Get or initialize the index for this section
                if index_key not in data.elective_time_tracker:
                    data.elective_time_tracker[index_key] = {}
                
                if section_number not in data.elective_time_tracker[index_key]:
                    data.elective_time_tracker[index_key][section_number] = 0
                
                # Get the current index for this section
                idx = data.elective_time_tracker[index_key][section_number]
                
                if isinstance(time_list, list) and len(time_list) > 0:
                    # Use modulo to cycle through times (prevents out of range error)
                    selected_mt = time_list[idx % len(time_list)]
                    # Increment index for next call
                    data.elective_time_tracker[index_key][section_number] += 1
                else:
                    selected_mt = random.choice(meeting_times)  # Fallback
            else:
                # Fallback if pre-allocation didn't work
                selected_mt = random.choice(meeting_times)
        else:
            # LIGHT EARLY-BIASED SELECTION: Prefer distributing across all slots
            # 30% chance to use early bias, 70% pure random for better distribution
            if available_mt and random.random() < 0.3:
                slot_order = [t[0] for t in TIME_SLOTS]
                available_mt_sorted = sorted(available_mt, 
                                            key=lambda mt: slot_order.index(mt.time) if mt.time in slot_order else 999)
                
                # Gentle weights: early slots 2-3x more likely than late slots (not 8x)
                n = len(available_mt_sorted)
                if n > 1:
                    # Linear decay instead of exponential - much gentler
                    weights = [1.0 + (n - i) / n for i in range(n)]  # Range: 2.0 to 1.0
                    selected_mt = random.choices(available_mt_sorted, weights=weights, k=1)[0]
                elif n == 1:
                    selected_mt = available_mt_sorted[0]
                else:
                    selected_mt = random.choice(meeting_times) if meeting_times else None
            elif available_mt:
                # Pure random selection for diversity
                selected_mt = random.choice(available_mt)
            else:
                # Fallback if no available times
                selected_mt = random.choice(meeting_times) if meeting_times else None
        
        if selected_mt is None:
            return  # Skip this class - no available time slots


        newClass.set_meetingTime(selected_mt)

        # mark day used
        used_days.add(selected_mt.day)
        self.course_day_tracker[(section_number, course.course_number)] = used_days

        # Room - For LAB courses, randomly select from assigned lab rooms
        if course.course_type == 'LAB':
            available_labs = list(course.lab_rooms.all())
            if available_labs:
                newClass.set_room(random.choice(available_labs))
            else:
                newClass.set_room(None)
        else:
            newClass.set_room(None)

        # Instructor
        assigned = CourseInstructorAssignment.objects.filter(
            year=year,
            section_number=section_number,
            course=course
        )

        if assigned.exists():
            # Get all instructors for this section, pick randomly if multiple
            assigned_instructors = list(assigned.first().instructors.all())
            if assigned_instructors:
                newClass.set_instructor(random.choice(assigned_instructors))
        else:
        # fallback random (if not assigned)
            crs_inst = list(course.instructors.all())
            if crs_inst:
                newClass.set_instructor(random.choice(crs_inst))
        self._classes.append(newClass)

    def isSectionBusy(self, section_number, meeting_time):
        """Check if section already has a class at this time"""
        for cls in self._classes:
            if cls.section_number == section_number and cls.meeting_time == meeting_time:
                return True
        return False
    
    def isInstructorBusy(self, instructor, meeting_time):
        """Check if instructor already has a class at this time"""
        if instructor is None:
            return False
        for cls in self._classes:
            if cls.instructor == instructor and cls.meeting_time == meeting_time:
                return True
        return False
        
    def addContinuousCourse(self, data, course, year, section_number):

        meeting_times = list(data.get_meetingTimes())

        # group by day
        day_groups = {}
        for mt in meeting_times:
            day_groups.setdefault(mt.day, []).append(mt)

        # sort times
        for day in day_groups:
            day_groups[day].sort(key=lambda x: TIME_SLOTS.index((x.time, x.time)))

        valid_blocks = []

        for day, times in day_groups.items():
            for i in range(len(times) - course.max_continuous_hours + 1):

                block = times[i:i + course.max_continuous_hours]

                # ❌ CRITICAL: Skip blocks that include or cross lunch break
                # Check 1: Lunch is in the block
                if any(t.time == "12:15 - 1:05" for t in block):
                    continue
                
                # Check 2: Block crosses lunch (times before 12:15 AND after 1:05)
                slot_order = [t[0] for t in TIME_SLOTS]
                lunch_index = slot_order.index("12:15 - 1:05") if "12:15 - 1:05" in slot_order else -1
                
                if lunch_index != -1:
                    block_indices = [slot_order.index(t.time) for t in block if t.time in slot_order]
                    if block_indices:
                        # Check if block spans across lunch (some before, some after)
                        has_before_lunch = any(idx < lunch_index for idx in block_indices)
                        has_after_lunch = any(idx > lunch_index for idx in block_indices)
                        if has_before_lunch and has_after_lunch:
                            continue  # Block crosses lunch - skip it

                # ⭐ ENHANCED: Check for conflicts to prefer conflict-free blocks
                # Check if section or instructor is busy during this block
                has_conflict = False
                for mt in block:
                    if self.isSectionBusy(section_number, mt):
                        has_conflict = True
                        break
                    # Check instructor conflict (need to get instructor first)
                    assigned = CourseInstructorAssignment.objects.filter(
                        year=year,
                        section_number=section_number,
                        course=course
                    )
                    if assigned.exists():
                        assigned_instructors = list(assigned.first().instructors.all())
                        if assigned_instructors:
                            instructor = assigned_instructors[0]  # Use main instructor for checking
                            if self.isInstructorBusy(instructor, mt):
                                has_conflict = True
                                break
                
                # Add block with conflict flag (prefer conflict-free but allow conflicted as fallback)
                valid_blocks.append((block, has_conflict))

        if not valid_blocks:
            logger.warning(f"CONTINUOUS BLOCK FAILED: {course.course_number} ({course.course_type}) Section {section_number} - No valid continuous time slots found!")
            return

        # ⭐ SMART BLOCK SELECTION: Prefer conflict-free blocks over conflicted ones
        conflict_free_blocks = [block for block, has_conflict in valid_blocks if not has_conflict]
        conflicted_blocks = [block for block, has_conflict in valid_blocks if has_conflict]
        
        # Use conflict-free blocks if available, otherwise use conflicted blocks as fallback
        blocks_to_use = conflict_free_blocks if conflict_free_blocks else conflicted_blocks
        
        if not blocks_to_use:
            logger.warning(f"CONTINUOUS BLOCK FAILED: {course.course_number} Section {section_number} - No usable blocks!")
            return

        # ELECTIVE → Use ONLY pre-allocated time block (MANDATORY)
        if course.course_type == 'ELECTIVE':
            block_key = f"{course.course_number}_continuous"
            if block_key in data.elective_time_tracker:
                selected_block = data.elective_time_tracker[block_key]
            else:
                # Fallback - but this violates synchronization
                selected_block = random.choice(blocks_to_use)
                data.elective_time_tracker[block_key] = selected_block
        else:
            # GENTLE EARLY-BIASED SELECTION: Soft preference for earlier blocks
            # 70% chance to use early bias, 30% pure random for genetic diversity
            if blocks_to_use and random.random() < 0.7:
                slot_order = [t[0] for t in TIME_SLOTS]
                blocks_sorted = sorted(blocks_to_use, 
                                      key=lambda block: slot_order.index(block[0].time) if block[0].time in slot_order else 999)
                
                # Gentle weights: early blocks 2-3x more likely (not 8x)
                n = len(blocks_sorted)
                if n > 1:
                    # Linear decay instead of exponential
                    weights = [1.0 + (n - i) / n for i in range(n)]
                    selected_block = random.choices(blocks_sorted, weights=weights, k=1)[0]
                elif n == 1:
                    selected_block = blocks_sorted[0]
                else:
                    return  # No valid blocks
            elif blocks_to_use:
                # Pure random for diversity
                selected_block = random.choice(blocks_to_use)
            else:
                return  # No valid blocks available

        # ⭐ mark day reserved for this course
        used_days = self.course_day_tracker.get((section_number, course.course_number), set())
        used_days.add(selected_block[0].day)
        self.course_day_tracker[(section_number, course.course_number)] = used_days

        # instructor
        assigned = CourseInstructorAssignment.objects.filter(
            year=year,
            section_number=section_number,
            course=course
        )
        if assigned.exists():
            # Get all instructors for this section, pick randomly if multiple
            assigned_instructors = list(assigned.first().instructors.all())
            instructor = random.choice(assigned_instructors) if assigned_instructors else None
        else:
            instructors = list(course.instructors.all())
            instructor = random.choice(instructors) if instructors else None

        # Room - For LAB courses, randomly select from assigned lab rooms
        if course.course_type == 'LAB':
            available_labs = list(course.lab_rooms.all())
            if available_labs:
                room = random.choice(available_labs)
            else:
                room = None
        else:
            room = None

        # create classes
        for mt in selected_block:
            newClass = Class(year, section_number, course, batch='FULL')
            newClass.set_meetingTime(mt)
            newClass.set_room(room)
            newClass.set_instructor(instructor)
            self._classes.append(newClass)


    def initialize(self):
        sections = self._data.get_sections()  # Returns [1, 2, 3]
        year = self._data.get_year()  # Get year from Data
        
        # Reset elective single time indices for this schedule
        # Each schedule needs to use the same sequence for all sections
        for key in list(self._data.elective_time_tracker.keys()):
            if key.endswith('_single_index'):
                self._data.elective_time_tracker[key] = {}

        all_courses = year.courses.all()
        
        # Separate courses by type and sort by priority
        lab_courses = list(all_courses.filter(course_type='LAB').order_by('-priority'))
        elective_courses = list(all_courses.filter(course_type='ELECTIVE').order_by('-priority'))
        
        # Split THEORY courses into two groups
        all_theory = all_courses.filter(course_type='THEORY').order_by('-priority')
        continuous_theory_courses = list(all_theory.filter(max_continuous_hours__gt=1))  # TP courses (need 2+ continuous hours)
        regular_theory_courses = list(all_theory.filter(max_continuous_hours=1))  # Regular theory (1 hour each)
        
        # ========================================================================
        # PHASE 1: Schedule ALL LAB courses (HIGHEST PRIORITY)
        # ========================================================================
        # Labs need continuous time blocks and specific lab rooms
        # Labs MUST be scheduled with 100% hours - no reduction allowed
        # Labs cannot cross lunch break
        
        phase1_classes_before = len(self._classes)
        for section_number in sections:
            for course in lab_courses:
                remaining_hours = course.hours_per_week
                
                # Labs must be continuous (STRICT requirement)
                if course.max_continuous_hours > 1:
                    block_start_len = len(self._classes)
                    self.addContinuousCourse(self._data, course, year, section_number)
                    
                    # BUGFIX: Count hours actually scheduled
                    hours_actually_scheduled = len(self._classes) - block_start_len
                    remaining_hours -= hours_actually_scheduled
                    
                    # Log only failures (these cause high conflicts)
                    if hours_actually_scheduled < course.hours_per_week:
                        logger.warning(f"❌ {course.course_number} Section {section_number}: Scheduled {hours_actually_scheduled}/{course.hours_per_week} hours (CONTINUOUS BLOCK FAILED)")
                
                # ❌ CRITICAL: Labs MUST be continuous - DO NOT schedule remaining hours separately
                # If continuous block failed, it will be penalized in fitness
        
        # ========================================================================
        # PHASE 2: Schedule ELECTIVE courses (PARALLEL SECTION RULE)
        # ========================================================================
        # Electives MUST occur at the same time for all sections
        # Students from multiple sections attend together
        # Schedule electives BEFORE theory so they lock specific time slots
        
        phase2_classes_before = len(self._classes)
        for section_number in sections:
            for course in elective_courses:
                remaining_hours = course.hours_per_week
                
                # Continuous block if specified
                if course.max_continuous_hours > 1:
                    block_start_len = len(self._classes)
                    self.addContinuousCourse(self._data, course, year, section_number)
                    
                    # BUGFIX: Count hours actually scheduled
                    hours_actually_scheduled = len(self._classes) - block_start_len
                    remaining_hours -= hours_actually_scheduled
                    
                    # Log if continuous block failed for elective
                    if hours_actually_scheduled == 0:
                        logger.warning(f"ELECTIVE CONTINUOUS BLOCK FAILED: {course.course_number} Section {section_number} - No valid continuous time slots found")
                
                # Remaining single periods (synchronized across sections)
                for i in range(remaining_hours):
                    self.addCourse(self._data, course, all_courses, year, section_number)
        
        # ========================================================================
        # PHASE 3: Schedule CONTINUOUS THEORY courses (e.g., TP courses)
        # ========================================================================
        # Schedule THEORY courses that need multiple continuous hours (e.g., TP courses with 2 continuous hours)
        # These MUST be scheduled BEFORE regular theory to ensure continuous slots are available
        # Examples: TP courses (23TP9102, 23TP9103, etc.) with hours_per_week=2, max_continuous_hours=2
        
        phase3_classes_before = len(self._classes)
        for section_number in sections:
            for course in continuous_theory_courses:
                remaining_hours = course.hours_per_week
                
                # These courses need continuous blocks - schedule them first
                if course.max_continuous_hours > 1 and remaining_hours >= course.max_continuous_hours:
                    block_start_len = len(self._classes)
                    self.addContinuousCourse(self._data, course, year, section_number)
                    
                    # Track hours actually scheduled
                    hours_actually_scheduled = len(self._classes) - block_start_len
                    remaining_hours -= hours_actually_scheduled
                    
                    # Log if continuous block failed
                    if hours_actually_scheduled == 0:
                        logger.warning(f"CONTINUOUS THEORY BLOCK FAILED: {course.course_number} Section {section_number} - No valid continuous time slots found")
                
                # ⭐ CRITICAL FIX FOR TP COURSES:
                # Only schedule remaining hours separately if the course ALLOWS partial continuity
                # For TP courses where hours_per_week == max_continuous_hours (e.g., 2==2),
                # ALL hours MUST be continuous - do NOT fall back to separate scheduling
                # This ensures TP courses are NEVER split into non-continuous periods
                if course.hours_per_week > course.max_continuous_hours:
                    # Course allows some hours to be separate (e.g., 4 hrs/week, 2 max continuous)
                    # Schedule remaining hours separately
                    attempts = 0
                    max_attempts = remaining_hours * 50
                    
                    while remaining_hours > 0 and attempts < max_attempts:
                        attempts += 1
                        self.addCourse(self._data, course, all_courses, year, section_number)
                        remaining_hours -= 1
        
        phase3_classes_added = len(self._classes) - phase3_classes_before
        logger.info(f"   PHASE 3 (Continuous THEORY): Scheduled {len(continuous_theory_courses)} continuous theory courses → {phase3_classes_added} class periods added")
        
        # ========================================================================
        # PHASE 4: Schedule REGULAR THEORY courses (FILL REMAINING SLOTS)
        # ========================================================================
        # Regular theory courses (1 hour each) fill the remaining empty slots
        # CRITICAL RULE: Theory subjects must be DISTRIBUTED across multiple days
        # Example: 4 hrs/week, max_continuous=1 → Schedule on 4 different days if possible
        
        phase4_classes_before = len(self._classes)
        for section_number in sections:
            for course in regular_theory_courses:
                # Track hours scheduled per day for this course-section combination
                hours_per_day = {}  # {day: count}
                
                remaining_hours = course.hours_per_week
                
                # Regular theory courses are scheduled 1 hour at a time, distributed across days
                # CRITICAL: Each hour should go to a DIFFERENT day (avoid bunching)
                attempts = 0
                max_attempts = remaining_hours * 50  # Safety limit
                
                while remaining_hours > 0 and attempts < max_attempts:
                    attempts += 1
                    
                    # Get available meeting times for this section
                    meeting_times = list(self._data.get_meetingTimes())
                    
                    # Get instructors from CourseInstructorAssignment (respects section-specific assignments)
                    assigned = CourseInstructorAssignment.objects.filter(
                        year=year,
                        section_number=section_number,
                        course=course
                    )
                    
                    if assigned.exists():
                        course_instructors = list(assigned.first().instructors.all())
                    else:
                        # Fallback to course instructors if no assignment exists
                        course_instructors = list(course.instructors.all())
                    
                    if not course_instructors:
                        logger.warning(f"No instructors available for {course.course_number} Section {section_number}")
                        break
                    
                    # Try to find a slot on a day with FEWER hours of this course
                    # Sort days by hours already scheduled (ascending)
                    all_days = set(mt.day for mt in meeting_times)
                    days_sorted = sorted(all_days, key=lambda d: hours_per_day.get(d, 0))
                    
                    # Try days with fewest hours first
                    slot_found = False
                    for preferred_day in days_sorted:
                        # Limit: Don't exceed max_continuous_hours on any single day
                        if hours_per_day.get(preferred_day, 0) >= course.max_continuous_hours:
                            continue  # Skip this day - already at limit
                        
                        # Get meeting times for this preferred day
                        day_meeting_times = [mt for mt in meeting_times if mt.day == preferred_day]
                        
                        # Try each time slot on this day
                        for mt in day_meeting_times:
                            # Check if this slot is available (no conflicts)
                            conflict = False
                            
                            # Check instructor availability
                            for inst in course_instructors:
                                for cls in self._classes:
                                    if cls.instructor == inst and cls.meeting_time == mt and cls.section_number != section_number:
                                        conflict = True
                                        break
                                if conflict:
                                    break
                            
                            # Check section availability
                            if not conflict:
                                for cls in self._classes:
                                    if cls.section_number == section_number and cls.meeting_time == mt:
                                        conflict = True
                                        break
                            
                            # If no conflict, assign this slot
                            if not conflict:
                                instructor = random.choice(course_instructors)
                                
                                newClass = Class(year, section_number, course, batch='FULL')
                                newClass.set_meetingTime(mt)
                                newClass.set_room(None)  # Theory courses don't need specific rooms
                                newClass.set_instructor(instructor)
                                self._classes.append(newClass)
                                
                                # Track this hour on this day
                                hours_per_day[preferred_day] = hours_per_day.get(preferred_day, 0) + 1
                                remaining_hours -= 1
                                slot_found = True
                                break
                        
                        if slot_found:
                            break
                    
                    # If no slot found after trying all days, break to avoid infinite loop
                    if not slot_found:
                        break
                
                # Do NOT log here - this runs for every schedule (150+ times during population creation)
                # Missing hours are penalized in fitness calculation

        return self

    def validate_continuous_theory_strict(self):
        """
        ⭐ STRICT VALIDATION for TP courses and other continuous theory courses
        Returns True only if ALL courses with hours_per_week == max_continuous_hours > 1
        are scheduled as continuous blocks on the same day.
        
        This is called BEFORE accepting a schedule - violations mean REJECT the entire schedule.
        """
        classes = self.getClasses()
        
        # Group by section and course
        theory_by_section_course = {}
        
        for c in classes:
            if c.course.course_type != 'THEORY':
                continue
            
            # Only check courses that MUST be continuous
            if c.course.max_continuous_hours <= 1:
                continue
            
            # TP courses: hours_per_week == max_continuous_hours
            if c.course.hours_per_week != c.course.max_continuous_hours:
                continue
            
            key = (c.section_number, c.course)
            if key not in theory_by_section_course:
                theory_by_section_course[key] = []
            theory_by_section_course[key].append((c.meeting_time.day, c.meeting_time.time))
        
        # Validate each course
        slot_order = [t[0] for t in TIME_SLOTS]
        
        for (section, course), day_time_pairs in theory_by_section_course.items():
            required = course.max_continuous_hours
            
            # Group by day
            days = {}
            for day, time in day_time_pairs:
                if day not in days:
                    days[day] = []
                days[day].append(time)
            
            # REJECT: Split across multiple days
            if len(days) > 1:
                logger.warning(f"⭐ STRICT REJECT: {course.course_number} Sec {section} split across {len(days)} days")
                return False
            
            # REJECT: Not enough hours
            if len(days) == 0:
                logger.warning(f"⭐ STRICT REJECT: {course.course_number} Sec {section} has no hours scheduled")
                return False
            
            day = list(days.keys())[0]
            times = days[day]
            
            if len(times) < required:
                logger.warning(f"⭐ STRICT REJECT: {course.course_number} Sec {section} has only {len(times)}/{required} hours")
                return False
            
            # Check continuity
            indexes = sorted([slot_order.index(t) for t in times])
            continuous_found = False
            
            for i in range(len(indexes) - required + 1):
                if indexes[i:i+required] == list(range(indexes[i], indexes[i] + required)):
                    continuous_found = True
                    break
            
            # REJECT: Not continuous
            if not continuous_found:
                logger.warning(f"⭐ STRICT REJECT: {course.course_number} Sec {section} NOT continuous: {times}")
                return False
        
        # All checks passed
        return True

    def calculateFitness(self):

        self._numberOfConflicts = 0
        classes = self.getClasses()

        # ------------------------------
        # Hard Constraints
        # ------------------------------
        for i in range(len(classes)):

            # Room capacity constraint - DISABLED (rooms assigned manually)
            # Rooms are not auto-assigned, so no capacity check needed

            for j in range(i + 1, len(classes)):

                # HARD CONSTRAINT: Instructor clash - same instructor teaching different sections at same time
                if (classes[i].section_number != classes[j].section_number and
                    classes[i].meeting_time == classes[j].meeting_time and
                    classes[i].instructor == classes[j].instructor):
                    self._numberOfConflicts += 100  # CRITICAL violation

                # HARD CONSTRAINT: Section clash - same section at same time
                if (classes[i].section_number == classes[j].section_number and
                    classes[i].meeting_time == classes[j].meeting_time):
                    self._numberOfConflicts += 100  # CRITICAL violation
                
                # Room clash - DISABLED (rooms assigned manually)
                # No automatic room assignment, so no room conflict check needed

        # ------------------------------
        # LAB CONTINUITY CONSTRAINT (NEW)
        # ------------------------------
        grouped = {}

        for c in classes:
            if c.course.course_type != 'LAB':
                continue

            key = (c.section_number, c.course, c.meeting_time.day)

            if key not in grouped:
                grouped[key] = []
            grouped[key].append(c.meeting_time.time)

        slot_order = [t[0] for t in TIME_SLOTS]

        for key, times in grouped.items():

            course = key[1]
            required = course.max_continuous_hours

            if len(times) < required:
                self._numberOfConflicts += 100  # CRITICAL: Missing lab hours
                continue

            # convert to ordered indexes
            indexes = sorted([slot_order.index(t) for t in times])

            # check continuous block exists
            continuous_found = False
            for i in range(len(indexes) - required + 1):
                if indexes[i:i+required] == list(range(indexes[i], indexes[i] + required)):
                    continuous_found = True
                    break

            if not continuous_found:
                self._numberOfConflicts += 100  # CRITICAL: Non-continuous lab

        # ------------------------------
        # THEORY CONTINUITY CONSTRAINT - STRICT (for TP courses and other continuous theory)
        # ------------------------------
        # ⭐ STRICT CONSTRAINT: THEORY courses where hours_per_week == max_continuous_hours > 1
        # MUST have ALL hours as a continuous block on one day (e.g., TP courses with 2 continuous hours)
        # This is NON-NEGOTIABLE - violations get MASSIVE penalty (10000) to force rejection
        theory_by_section_course = {}  # {(section, course): [(day, time), ...]}

        for c in classes:
            if c.course.course_type != 'THEORY':
                continue
            
            # Only check courses that need continuous scheduling
            if c.course.max_continuous_hours <= 1:
                continue
            
            # ⭐ STRICT: Only check courses where ALL weekly hours should be continuous
            # This targets TP courses: hours_per_week == max_continuous_hours (e.g., 2 == 2)
            if c.course.hours_per_week != c.course.max_continuous_hours:
                continue

            key = (c.section_number, c.course)
            if key not in theory_by_section_course:
                theory_by_section_course[key] = []
            theory_by_section_course[key].append((c.meeting_time.day, c.meeting_time.time))

        slot_order = [t[0] for t in TIME_SLOTS]

        for (section, course), day_time_pairs in theory_by_section_course.items():
            required = course.max_continuous_hours
            
            # Group by day
            days = {}
            for day, time in day_time_pairs:
                if day not in days:
                    days[day] = []
                days[day].append(time)
            
            # ⭐ STRICT VIOLATION: Hours split across multiple days - UNACCEPTABLE
            if len(days) > 1:
                self._numberOfConflicts += 10000  # MASSIVE penalty - forces rejection
                logger.error(f"STRICT VIOLATION: {course.course_number} Section {section} split across {len(days)} days (Must be on ONE day)")
                continue
            
            # Check if the hours on the single day are continuous
            if len(days) == 1:
                day = list(days.keys())[0]
                times = days[day]
                
                # ⭐ STRICT VIOLATION: Missing hours
                if len(times) < required:
                    self._numberOfConflicts += 10000  # MASSIVE penalty
                    logger.error(f"STRICT VIOLATION: {course.course_number} Section {section} has only {len(times)}/{required} hours")
                    continue
                
                # convert to ordered indexes
                indexes = sorted([slot_order.index(t) for t in times])

                # check continuous block exists
                continuous_found = False
                for i in range(len(indexes) - required + 1):
                    if indexes[i:i+required] == list(range(indexes[i], indexes[i] + required)):
                        continuous_found = True
                        break

                # ⭐ STRICT VIOLATION: Hours NOT continuous (e.g., 9:45-10:35 and 1:05-1:55)
                if not continuous_found:
                    self._numberOfConflicts += 10000  # MASSIVE penalty - forces rejection
                    logger.error(f"STRICT VIOLATION: {course.course_number} Section {section} has {len(times)} hours but NOT continuous on {day}")

        # ------------------------------
        # ELECTIVE SYNCHRONIZATION CHECK
        # ------------------------------
        # Verify electives are scheduled at same times across all sections
        elective_schedule = {}  # {course_number: {section: [(day, time), ...]}}
        
        for c in classes:
            if c.course.course_type == 'ELECTIVE':
                course_num = c.course.course_number
                section_id = c.section_number
                
                if course_num not in elective_schedule:
                    elective_schedule[course_num] = {}
                if section_id not in elective_schedule[course_num]:
                    elective_schedule[course_num][section_id] = []
                
                elective_schedule[course_num][section_id].append((c.meeting_time.day, c.meeting_time.time))
        
        # Check if all sections have identical schedules for each elective
        for course_num, section_schedules in elective_schedule.items():
            if len(section_schedules) > 1:
                # Get the set of times from first section
                first_section = list(section_schedules.keys())[0]
                first_schedule = sorted(section_schedules[first_section])
                
                # Compare with all other sections
                for section_id, schedule in section_schedules.items():
                    if sorted(schedule) != first_schedule:
                        self._numberOfConflicts += 100  # CRITICAL: Elective not synchronized

        # ------------------------------
        # THEORY SUBJECT DISTRIBUTION PENALTY
        # ------------------------------
        # CRITICAL: Theory subjects must NOT have all weekly hours on one day
        # Also penalize exceeding max_continuous_hours on any single day
        day_course_tracker = {}  # {(section, course, day): count}
        course_total_hours = {}  # {(section, course): total_weekly_hours}
        
        for c in classes:
            if c.course.course_type == 'THEORY':  # Only check THEORY courses
                key = (c.section_number, c.course.course_number, c.meeting_time.day)
                total_key = (c.section_number, c.course.course_number)
                
                day_course_tracker[key] = day_course_tracker.get(key, 0) + 1
                course_total_hours[total_key] = course_total_hours.get(total_key, 0) + 1
        
        # Check for violations
        for (section, course_num, day), day_count in day_course_tracker.items():
            total_key = (section, course_num)
            total_hours = course_total_hours.get(total_key, 0)
            
            # Find the course object to get max_continuous_hours
            course_obj = None
            for c in classes:
                if c.section_number == section and c.course.course_number == course_num:
                    course_obj = c.course
                    break
            
            if course_obj:
                # CRITICAL: All weekly hours on one day (unrealistic)
                if day_count >= total_hours and total_hours > 1:
                    self._numberOfConflicts += 80  # Major penalty
                
                # CRITICAL: Exceeds max_continuous_hours on one day
                if day_count > course_obj.max_continuous_hours:
                    self._numberOfConflicts += 80  # Major penalty

        # ------------------------------
        # GAP PENALTY (NEW - CRITICAL FOR COMPACTNESS)
        # ------------------------------
        # Penalize gaps between classes in daily schedules
        # This makes timetables compact like manual ones
        slot_order = [t[0] for t in TIME_SLOTS]
        
        # Group classes by section and day
        section_day_classes = {}
        for c in classes:
            key = (c.section_number, c.meeting_time.day)
            if key not in section_day_classes:
                section_day_classes[key] = []
            section_day_classes[key].append(c.meeting_time.time)
        
        # Calculate gaps for each section-day combination
        for key, times in section_day_classes.items():
            if len(times) < 2:
                continue  # No gaps possible with 0 or 1 class
            
            # Convert times to slot indexes (deduplicate to avoid negative gaps from conflicts)
            indexes = sorted(list(set([slot_order.index(t) for t in times])))
            
            # SMART GAP DETECTION: Split by morning/afternoon (lunch break is OK)
            # Find lunch break index
            lunch_index = slot_order.index("12:15 - 1:05") if "12:15 - 1:05" in slot_order else -1
            
            # Separate morning and afternoon classes
            morning_indexes = [idx for idx in indexes if lunch_index == -1 or idx < lunch_index]
            afternoon_indexes = [idx for idx in indexes if lunch_index != -1 and idx > lunch_index]
            
            # Count gaps in morning block
            if len(morning_indexes) >= 2:
                morning_span = morning_indexes[-1] - morning_indexes[0] + 1
                morning_gaps = morning_span - len(morning_indexes)
                self._numberOfConflicts += 20 * morning_gaps  # Balanced penalty for gaps
            
            # Count gaps in afternoon block  
            if len(afternoon_indexes) >= 2:
                afternoon_span = afternoon_indexes[-1] - afternoon_indexes[0] + 1
                afternoon_gaps = afternoon_span - len(afternoon_indexes)
                self._numberOfConflicts += 20 * afternoon_gaps  # Balanced penalty for gaps

        # ------------------------------
        # EMPTY SLOT PENALTY (TIMETABLE COMPLETENESS)
        # ------------------------------
        # Penalize incomplete timetables - we want fully filled schedules
        # Calculate expected vs actual classes scheduled
        year = self._data.get_year()
        sections = self._data.get_sections()
        all_courses = year.courses.all()
        
        # Calculate total expected classes
        expected_total = 0
        for course in all_courses:
            if course.course_type in ['LAB', 'THEORY']:
                # Each section gets full hours
                expected_total += course.hours_per_week * len(sections)
            elif course.course_type == 'ELECTIVE':
                # Electives are shared, count once
                expected_total += course.hours_per_week
        
        actual_total = len(classes)
        missing_classes = max(0, expected_total - actual_total)
        
        # Heavy penalty for missing classes (incomplete timetable)
        self._numberOfConflicts += 20 * missing_classes

        # Safety check: ensure conflicts is non-negative
        if self._numberOfConflicts < 0:
            logger.error(f"CRITICAL: numberOfConflicts is negative ({self._numberOfConflicts})! Resetting to 0")
            self._numberOfConflicts = 0
        
        # Prevent division by zero
        denominator = self._numberOfConflicts + 1
        if denominator == 0:
            logger.error(f"CRITICAL: denominator is zero! numberOfConflicts={self._numberOfConflicts}")
            return 0.0001  # Very low fitness instead of crashing
        
        return 1 / denominator


class ConstraintScheduler:
    """Constraint-based scheduler - builds valid timetables systematically"""
    
    def _sort_meeting_times_chronologically(self, meeting_times):
        """Sort meeting times to eliminate gaps - prefer earlier slots"""
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        time_order = [t[0] for t in TIME_SLOTS]
        
        return sorted(meeting_times, key=lambda mt: (
            day_order.index(mt.day) if mt.day in day_order else 999,
            time_order.index(mt.time) if mt.time in time_order else 999
        ))
    
    def build_schedule(self, data, selected_year):
        """Build a conflict-free schedule using constraint satisfaction"""
        schedule = Schedule()
        schedule._data = data
        schedule._classes = []
        schedule.course_day_tracker = {}
        
        all_courses = selected_year.courses.all()
        sections = data.get_sections()
        
        # Priority order: LABs first (hardest), then continuous theory (TP), then regular theory
        lab_courses = sorted([c for c in all_courses if c.course_type == 'LAB'], 
                            key=lambda x: -x.max_continuous_hours)  # Longer labs first
        elective_courses = [c for c in all_courses if c.course_type == 'ELECTIVE']
        
        # Split THEORY courses into continuous (TP courses) and regular
        all_theory = all_courses.filter(course_type='THEORY')
        continuous_theory_courses = [c for c in all_theory if c.max_continuous_hours > 1]
        regular_theory_courses = [c for c in all_theory if c.max_continuous_hours == 1]
        
        logger.info(f"?? Scheduling {len(lab_courses)} LABs, {len(elective_courses)} ELECTIVEs, {len(continuous_theory_courses)} continuous THEORY, {len(regular_theory_courses)} regular THEORY courses")
        
        # === PHASE 1: Schedule LABs (need continuous blocks) ===
        for course in lab_courses:
            logger.info(f"  ====> Processing LAB course: {course.course_number}")
            for section in sections:
                logger.info(f"    ====> Section {section}")
                if not self._schedule_lab_course(schedule, data, course, selected_year, section):
                    logger.warning(f"Failed to schedule LAB {course.course_number} for section {section}")
                    # Don't fail completely - continue to try other courses
                    # Some labs might not be schedulable due to conflicts, but we can still try others
        
        # === PHASE 2: Schedule ELECTIVEs (same time for all sections) ===
        for course in elective_courses:
            if not self._schedule_elective_course(schedule, data, course, selected_year, sections):
                logger.warning(f"Failed to schedule ELECTIVE {course.course_number}")
                # Don't fail completely - continue with other courses
        
        # === PHASE 3: Schedule CONTINUOUS THEORY courses (e.g., TP courses) ===
        # These courses prefer continuous blocks but can fall back to separate periods if needed
        for course in continuous_theory_courses:
            logger.info(f"  ====> Processing CONTINUOUS THEORY course: {course.course_number}")
            for section in sections:
                if not self._schedule_theory_course(schedule, data, course, selected_year, section):
                    logger.warning(f"Failed to schedule CONTINUOUS THEORY {course.course_number} for section {section}")
                    # Don't fail completely - try to continue with other courses
                    # return None
        
        # === PHASE 4: Schedule REGULAR THEORY courses ===
        for course in regular_theory_courses:
            for section in sections:
                if not self._schedule_theory_course(schedule, data, course, selected_year, section):
                    logger.warning(f"Failed to schedule REGULAR THEORY {course.course_number} for section {section}")
                    # Don't fail completely - partial schedules are acceptable
        
        # === PHASE 5: Schedule Special Periods (Counseling, Training, Sports/Library) ===
        logger.info("?? Starting special periods scheduling...")
        if not self._schedule_special_periods(schedule, data, selected_year, sections):
            logger.warning("Failed to schedule some special periods (continuing anyway)")
        
        logger.info(f"Successfully scheduled {len(schedule._classes)} classes")
        return schedule
    
    def _schedule_lab_course(self, schedule, data, course, year, section):
        """Schedule a LAB course (needs continuous time blocks)"""
        from .models import LabBatchAssignment
        
        # Check if this course uses batch splitting
        if course.split_into_batches:
            logger.info(f"  Scheduling SPLIT LAB {course.course_number} (Sec {section}) with batch rotation")
            return self._schedule_split_lab_course(schedule, data, course, year, section)
        
        # Regular lab scheduling (full section)
        hours_needed = course.max_continuous_hours
        hours_per_week = course.hours_per_week  # Total hours per week
        classes_needed = hours_per_week // hours_needed
        
        logger.info(f"  Scheduling REGULAR LAB {course.course_number} (Sec {section}): {classes_needed} blocks of {hours_needed}hr each")
        
        # Get main instructor (for availability checking)
        main_instructor = self._get_main_instructor(course, year, section)
        
        logger.info(f"    Main instructor: {main_instructor.name if main_instructor else 'None'}")
        
        if not main_instructor:
            logger.error(f"    ERROR: No main instructor available for {course.course_number} Sec {section}!")
            return False
        
        # Get lab room FIRST (CRITICAL: must check conflicts with actual room that will be used)
        lab_room = self._get_lab_room(course)
        if lab_room:
            logger.info(f"    Lab room: {lab_room.lab_name}")
        else:
            logger.info(f"    No lab room assigned (classroom-based lab)")
        
        available_blocks = self._find_continuous_blocks(data, hours_needed)
        logger.info(f"    Found {len(available_blocks)} continuous {hours_needed}-hour blocks total")
        
        # Filter blocks that don't conflict - check ONLY main instructor
        valid_blocks = []
        for block in available_blocks:
            # Block is valid if MAIN instructor is free
            if self._can_schedule_block(schedule, section, course, block, main_instructor, year, lab_room):
                valid_blocks.append(block)
        
        logger.info(f"    After conflict checking: {len(valid_blocks)} valid blocks available")
        
        if len(valid_blocks) < classes_needed:
            logger.error(f"    ERROR: Need {classes_needed} blocks but only {len(valid_blocks)} available!")
            return False  # Can't fit all required LAB sessions
        
        # Schedule the required number of LAB sessions
        for i in range(classes_needed):
            block = valid_blocks[i]
            
            # Determine number of evaluators based on year
            # 1st Year: NO evaluators (main instructor only)
            # 2nd-4th Year: 1-2 evaluators from same department
            if year.year_name == '1st Year':
                evaluators = []
                logger.info(f"    Block {i+1}: 1st Year - main instructor only (no evaluators)")
            else:
                # Auto-select evaluators from same department who are free during this block
                evaluators = self._get_available_evaluators(schedule, block, course, main_instructor, year=year, max_evaluators=2)
                logger.info(f"    Block {i+1}: {year.year_name} - {len(evaluators)+1} instructors (1 main + {len(evaluators)} evaluators)")
            
            # Create entry for MAIN instructor
            for mt in block:
                new_class = Class(year, section, course, batch='FULL', is_evaluator=False)
                new_class.set_meetingTime(mt)
                new_class.set_instructor(main_instructor)
                new_class.set_room(lab_room)
                schedule._classes.append(new_class)
            
            # Create entries for EVALUATORS (if any)
            for evaluator in evaluators:
                for mt in block:
                    new_class = Class(year, section, course, batch='FULL', is_evaluator=True)
                    new_class.set_meetingTime(mt)
                    new_class.set_instructor(evaluator)
                    new_class.set_room(lab_room)
                    schedule._classes.append(new_class)
        
        return True
    
    def _schedule_split_lab_course(self, schedule, data, course, year, section):
        """
        Schedule a LAB course with batch splitting (B1 and B2).
        Uses LabBatchAssignment to determine which batch gets which instructor/lab.
        Scheduler AUTOMATICALLY finds available time slots based on batch assignments.
        
        Example:
        Session 1 (auto-scheduled): B1 -> IoT Lab (Instructor A), B2 -> Cryptography Lab (Instructor B)
        Session 2 (auto-scheduled): B1 -> Cryptography Lab (Instructor C), B2 -> IoT Lab (Instructor D)
        """
        from .models import LabBatchAssignment
        
        logger.info(f"    DEBUG _schedule_split_lab: {course.course_number} Sec {section}")
        
        # Get batch assignments for this course and section (grouped by session)
        batch_assignments = LabBatchAssignment.objects.filter(
            year=year,
            section_number=section,
            course=course
        ).order_by('session_number', 'batch')
        
        logger.info(f"    DEBUG: Query found {batch_assignments.count()} assignments")
        
        if not batch_assignments.exists():
            logger.warning(f"    No LabBatchAssignment found for {course.course_number} Sec {section}. Skipping batch scheduling.")
            return True  # Don't fail, just skip this course
        
        logger.info(f"    Found {batch_assignments.count()} batch assignments")
        
        # Group assignments by session number
        from collections import defaultdict
        session_batches = defaultdict(list)
        for assignment in batch_assignments:
            session_batches[assignment.session_number].append(assignment)
        
        hours_per_block = course.max_continuous_hours
        meeting_times = list(data.get_meetingTimes())
        
        # For each session, find an available time slot and schedule both batches
        for session_num, assignments in sorted(session_batches.items()):
            logger.info(f"    Scheduling Session {session_num}: {len(assignments)} batches")
            logger.info(f"    DEBUG: Session {session_num} has {len(assignments)} batches")
            
            # Find continuous blocks that work for ALL batches in this session
            available_blocks = self._find_continuous_blocks(data, hours_per_block)
            
            logger.info(f"    DEBUG: Found {len(available_blocks)} continuous blocks")
            
            if not available_blocks:
                logger.error(f"      ERROR: No continuous {hours_per_block}-hour blocks available")
                logger.info(f"    DEBUG: RETURNING FALSE - no continuous blocks")
                return False
            
            # Try each available block until we find one that works for all batches
            scheduled = False
            for block in available_blocks:
                # Check if this block works for ALL assignments in this session
                can_schedule_all = True
                
                for assignment in assignments:
                    # Get main instructor for availability check (evaluators can overlap)
                    main_instructor = assignment.main_instructor
                    if not main_instructor:
                        # Fallback to first instructor if no main instructor set
                        assignment_instructors = list(assignment.instructors.all())
                        main_instructor = assignment_instructors[0] if assignment_instructors else None
                    
                    if not main_instructor:
                        logger.error(f"      ERROR: No main instructor for {assignment.batch}")
                        can_schedule_all = False
                        break
                    
                    # Check conflicts for this batch with ONLY main instructor
                    for mt in block:
                        # Check if main instructor, room, or section is busy at this time
                        for existing_class in schedule._classes:
                            if existing_class.meeting_time.pid == mt.pid:
                                # CRITICAL: Skip co-teaching entries (same course, same batch, same section)
                                if (existing_class.course == course and
                                    existing_class.section_number == section and
                                    existing_class.batch == assignment.batch):
                                    continue  # This is a co-teaching entry, not a conflict
                                
                                # Check if MAIN instructor conflicts (evaluators can overlap)
                                if existing_class.instructor == main_instructor:
                                    can_schedule_all = False
                                    break
                                    
                                # Same lab room conflict
                                if existing_class.room == assignment.lab_room:
                                    can_schedule_all = False
                                    break
                                # Same section conflict (but different batch is OK)
                                if (existing_class.section_number == section and 
                                    existing_class.year == year and
                                    existing_class.batch == assignment.batch):
                                    can_schedule_all = False
                                    break
                        if not can_schedule_all:
                            break
                    if not can_schedule_all:
                        break
                
                if can_schedule_all:
                    # Schedule ALL batches for this session at this time
                    for assignment in assignments:
                        day_name = block[0].day
                        time_range = f"{block[0].time} to {block[-1].time}"
                        
                        # Get main instructor for this batch
                        main_instructor_for_batch = assignment.main_instructor
                        if not main_instructor_for_batch:
                            # Fallback to first instructor if no main set
                            assignment_instructors = list(assignment.instructors.all())
                            main_instructor_for_batch = assignment_instructors[0] if assignment_instructors else None
                        
                        if main_instructor_for_batch:
                            # Auto-select evaluators from same department who are free
                            evaluators = self._get_available_evaluators(schedule, block, course, main_instructor_for_batch, year=year, max_evaluators=2)
                            
                            # Instructors for this batch = main + auto-selected evaluators
                            batch_instructors = [main_instructor_for_batch] + evaluators
                            instructor_names = ", ".join([inst.name for inst in batch_instructors])
                            
                            logger.info(f"      Session {session_num} {assignment.batch}: {course.course_number} @ {day_name} {time_range}")
                            logger.info(f"        {len(batch_instructors)} instructors: {instructor_names} - {assignment.lab_room}")
                            
                            # Create entries for each instructor
                            for instructor in batch_instructors:
                                for mt in block:
                                    new_class = Class(year, section, course, batch=assignment.batch)
                                    new_class.set_meetingTime(mt)
                                    new_class.set_instructor(instructor)
                                    new_class.set_room(assignment.lab_room)
                                    schedule._classes.append(new_class)
                        else:
                            logger.warning(f"        WARNING: No main instructor for {assignment.batch}")
                    
                    scheduled = True
                    break
            
            logger.info(f"    DEBUG: Session {session_num} scheduled={scheduled}")
            if not scheduled:
                logger.error(f"      ERROR: Could not schedule Session {session_num} for {course.course_number}")
                logger.info(f"    DEBUG: RETURNING FALSE - could not schedule session {session_num}")
                return False
        
        logger.info(f"    DEBUG: All sessions scheduled successfully")
        return True
    
    def _schedule_elective_course(self, schedule, data, course, year, sections):
        """Schedule ELECTIVE (same time for all sections, spread across days AND time slots)"""
        hours_per_week = course.hours_per_week
        max_continuous = course.max_continuous_hours if course.max_continuous_hours > 0 else hours_per_week
        meeting_times = list(data.get_meetingTimes())
        
        # Track hours per day AND time slot usage for spreading
        from collections import defaultdict
        day_hours = defaultdict(int)
        time_slot_usage = defaultdict(int)
        
        # Find times that work for ALL sections
        for _ in range(hours_per_week):
            best_time = None
            min_conflicts = float('inf')
            
            # Sort to prefer days AND time slots with less usage
            def sort_key(mt):
                day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
                time_order = [t[0] for t in TIME_SLOTS]
                return (
                    day_hours[mt.day],  # Prefer days with fewer hours (primary)
                    time_slot_usage[mt.time],  # Prefer time slots not yet used (secondary)
                    day_order.index(mt.day) if mt.day in day_order else 999,
                    time_order.index(mt.time) if mt.time in time_order else 999
                )
            
            sorted_times = sorted(meeting_times, key=sort_key)
            
            for mt in sorted_times:
                conflicts = 0
                exceeds_consecutive = False
                
                # Check each section
                for section in sections:
                    if not self._can_schedule_single(schedule, section, course, mt, year=year):
                        conflicts += 1
                        continue
                    
                    # Check if scheduling here would exceed max_continuous consecutive periods
                    consecutive_before = self._count_consecutive_before(schedule, section, course, mt)
                    consecutive_after = self._count_consecutive_after(schedule, section, course, mt)
                    total_consecutive = consecutive_before + consecutive_after + 1
                    
                    if total_consecutive > max_continuous:
                        exceeds_consecutive = True
                        break
                
                # Skip this time if it exceeds consecutive limit for any section
                if exceeds_consecutive:
                    continue
                
                if conflicts < min_conflicts:
                    min_conflicts = conflicts
                    best_time = mt
                
                # If we found a slot with no conflicts, use it immediately
                if min_conflicts == 0:
                    break
            
            if best_time is None or min_conflicts > 0:
                return False  # Can't find common time for all sections
            
            # Schedule for all sections at the same time
            for section in sections:
                instructors = self._get_instructors(course, year, section)
                instructor = instructors[0] if instructors else None  # Use first instructor
                new_class = Class(year, section, course, batch='FULL')
                new_class.set_meetingTime(best_time)
                new_class.set_instructor(instructor)
                new_class.set_room(None)
                schedule._classes.append(new_class)
            
            day_hours[best_time.day] += 1
            time_slot_usage[best_time.time] += 1
        
        return True
    
    def _schedule_theory_course(self, schedule, data, course, year, section):
        """Schedule a THEORY course (spread across days AND time slots)"""
        hours_per_week = course.hours_per_week
        max_continuous = course.max_continuous_hours if course.max_continuous_hours > 0 else hours_per_week
        meeting_times = list(data.get_meetingTimes())
        
        # Get instructor FIRST (section-specific)
        instructors = self._get_instructors(course, year, section)
        if not instructors:
            logger.warning(f"    No instructors for {course.course_number} Sec {section}")
            return False
        instructor = instructors[0]  # Use first instructor
        
        # ⭐ CRITICAL FIX FOR TP COURSES:
        # If hours_per_week == max_continuous_hours > 1, ALL hours MUST be continuous
        # Example: TP courses with 2hrs/week and max_continuous=2
        # These MUST be scheduled as ONE 2-hour block, NOT as separate 1-hour periods
        if hours_per_week == max_continuous and max_continuous > 1:
            logger.info(f"    {course.course_number} Sec{section}: Scheduling as {max_continuous}-hour continuous block (TP course)")
            
            # Find continuous blocks
            available_blocks = self._find_continuous_blocks(data, max_continuous)
            logger.info(f"      Found {len(available_blocks)} continuous {max_continuous}-hour blocks")
            
            # Filter blocks without conflicts
            valid_blocks = []
            for block in available_blocks:
                can_schedule = True
                for mt in block:
                    if not self._can_schedule_single(schedule, section, course, mt, instructor, year):
                        can_schedule = False
                        break
                if can_schedule:
                    valid_blocks.append(block)
            
            logger.info(f"      {len(valid_blocks)} conflict-free blocks available")
            
            if valid_blocks:
                # SUCCESS: Schedule the first valid continuous block
                selected_block = valid_blocks[0]
                logger.info(f"      [OK] Scheduling continuous block: {selected_block[0].day} {[mt.time for mt in selected_block]}")
                
                for mt in selected_block:
                    new_class = Class(year, section, course, batch='FULL')
                    new_class.set_meetingTime(mt)
                    new_class.set_instructor(instructor)
                    new_class.set_room(None)  # Theory courses don't use lab rooms
                    schedule._classes.append(new_class)
                
                return True
            else:
                # FALLBACK: No continuous blocks available, try to schedule as separate periods
                # This is not ideal but allows the schedule to be created
                # The fitness function will penalize this heavily, but won't fail completely
                logger.warning(f"      ⚠ No continuous blocks available for {course.course_number} Sec{section}")
                logger.warning(f"      → Falling back to separate period scheduling (will be penalized in fitness)")
                # Continue to regular scheduling below instead of returning False
        
        # ⭐ REGULAR THEORY SCHEDULING (for courses that can be spread across days)
        # This is the existing code for regular theory courses
        scheduled_count = 0
        attempts = 0
        max_attempts = len(meeting_times) * 10
        
        # Track hours per day AND time slot usage for better spreading
        from collections import defaultdict
        day_hours = defaultdict(int)
        time_slot_usage = defaultdict(int)  # Track how many times each time slot is used
        
        # Use day-spreading preference for first 60% of attempts, then relax
        use_spreading = True
        spreading_threshold = max_attempts * 0.6
        
        while scheduled_count < hours_per_week and attempts < max_attempts:
            attempts += 1
            
            # After many failed attempts, switch from spreading to chronological
            if attempts > spreading_threshold and use_spreading:
                use_spreading = False
                logger.debug(f"      {course.course_number} Sec{section}: Relaxing spreading constraint (attempt {attempts})")
            
            # Sort times: spread across BOTH days AND time slots
            if use_spreading:
                def sort_key(mt):
                    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
                    time_order = [t[0] for t in TIME_SLOTS]
                    return (
                        day_hours[mt.day],  # Prefer days with fewer hours (primary)
                        time_slot_usage[mt.time],  # Prefer time slots not yet used (secondary)
                        day_order.index(mt.day) if mt.day in day_order else 999,
                        time_order.index(mt.time) if mt.time in time_order else 999
                    )
                sorted_times = sorted(meeting_times, key=sort_key)
            else:
                # Fall back to chronological only
                sorted_times = self._sort_meeting_times_chronologically(meeting_times)
            
            # Find available time slot
            for mt in sorted_times:
                # Check if we can schedule here without exceeding consecutive limit
                if not self._can_schedule_single(schedule, section, course, mt, instructor, year):
                    continue
                
                # Count consecutive hours already scheduled for this course on this day
                consecutive_before = self._count_consecutive_before(schedule, section, course, mt)
                consecutive_after = self._count_consecutive_after(schedule, section, course, mt)
                total_consecutive = consecutive_before + consecutive_after + 1
                
                # Skip if adding this would exceed max_continuous_hours
                if total_consecutive > max_continuous:
                    continue
                
                # Schedule it
                new_class = Class(year, section, course, batch='FULL')
                new_class.set_meetingTime(mt)
                new_class.set_instructor(instructor)
                new_class.set_room(None)
                schedule._classes.append(new_class)
                scheduled_count += 1
                day_hours[mt.day] += 1
                time_slot_usage[mt.time] += 1
                logger.debug(f"      {course.course_number} Sec{section}: {mt.day} {mt.time} (day: {day_hours[mt.day]}, time used: {time_slot_usage[mt.time]}x, consecutive: {total_consecutive}/{max_continuous})")
                break
        
        if scheduled_count < hours_per_week:
            logger.warning(f"    {course.course_number} Sec{section}: Only scheduled {scheduled_count}/{hours_per_week} hours")
        
        return scheduled_count == hours_per_week
    
    def _count_consecutive_before(self, schedule, section, course, meeting_time):
        """Count consecutive periods before this time slot for the same course"""
        count = 0
        time_order = [t[0] for t in TIME_SLOTS]
        
        try:
            current_idx = time_order.index(meeting_time.time)
        except ValueError:
            return 0
        
        # Check preceding time slots on the same day
        for i in range(current_idx - 1, -1, -1):
            prev_time = time_order[i]
            
            # Check if there's a class at this time
            found = False
            for cls in schedule._classes:
                if (cls.section_number == section and 
                    cls.course == course and
                    cls.meeting_time.day == meeting_time.day and
                    cls.meeting_time.time == prev_time):
                    found = True
                    count += 1
                    break
            
            if not found:
                break  # No more consecutive periods
        
        return count
    
    def _count_consecutive_after(self, schedule, section, course, meeting_time):
        """Count consecutive periods after this time slot for the same course"""
        count = 0
        time_order = [t[0] for t in TIME_SLOTS]
        
        try:
            current_idx = time_order.index(meeting_time.time)
        except ValueError:
            return 0
        
        # Check following time slots on the same day
        for i in range(current_idx + 1, len(time_order)):
            next_time = time_order[i]
            
            # Check if there's a class at this time
            found = False
            for cls in schedule._classes:
                if (cls.section_number == section and 
                    cls.course == course and
                    cls.meeting_time.day == meeting_time.day and
                    cls.meeting_time.time == next_time):
                    found = True
                    count += 1
                    break
            
            if not found:
                break  # No more consecutive periods
        
        return count
    
    def _find_continuous_blocks(self, data, hours_needed):
        """Find all continuous time blocks of given length"""
        meeting_times = list(data.get_meetingTimes())
        day_groups = {}
        
        # Group by day
        for mt in meeting_times:
            if mt.day not in day_groups:
                day_groups[mt.day] = []
            day_groups[mt.day].append(mt)
        
        # Sort each day by time
        time_order = [t[0] for t in TIME_SLOTS]
        for day in day_groups:
            day_groups[day].sort(key=lambda mt: time_order.index(mt.time) if mt.time in time_order else 999)
        
        # Find continuous blocks
        blocks = []
        for day, times in day_groups.items():
            for i in range(len(times) - hours_needed + 1):
                block = times[i:i+hours_needed]
                # Verify continuity (no lunch break in middle)
                if self._is_continuous_block(block):
                    blocks.append(block)
        
        return blocks
    
    def _is_continuous_block(self, block):
        """Check if time block is continuous (no lunch break)"""
        time_order = [t[0] for t in TIME_SLOTS]
        for i in range(len(block) - 1):
            idx1 = time_order.index(block[i].time)
            idx2 = time_order.index(block[i+1].time)
            if idx2 != idx1 + 1:  # Not consecutive
                return False
            # Check for lunch break
            if '12:15' in [block[i].time, block[i+1].time]:
                return False
        return True
    
    def _can_schedule_block(self, schedule, section, course, block, instructor, year, room=None):
        """Check if a continuous block can be scheduled without conflicts"""
        for mt in block:
            if not self._can_schedule_single(schedule, section, course, mt, instructor, year, room):
                return False
        return True
    
    def _can_schedule_single(self, schedule, section, course, meeting_time, instructor=None, year=None, room=None):
        """Check if a single class can be scheduled"""
        # Check section conflicts (within current schedule, same year only)
        for cls in schedule._classes:
            if cls.section_number == section and cls.year == year and cls.meeting_time.pid == meeting_time.pid:
                # CRITICAL: Skip if this is a co-teaching entry (same course, same section)
                if cls.course == course:
                    continue  # Co-teaching (same course, different instructor), not a conflict
                # Different course - this IS a conflict
                return False
        
        # === Check instructor conflicts (CROSS-YEAR via database) ===
        if instructor:
            # 1. Check within current schedule
            for cls in schedule._classes:
                if cls.instructor == instructor and cls.meeting_time.pid == meeting_time.pid:
                    # CRITICAL: Skip co-teaching entries (same course, same section, same instructor)
                    if cls.course == course and cls.section_number == section:
                        continue  # Co-teaching, not a conflict
                    # Different course or section - this IS an instructor conflict
                    return False
            
            # 2. Check database for cross-year instructor conflicts (by day+time)
            existing_entries = TimetableEntry.objects.filter(
                instructor=instructor,
                meeting_time__day=meeting_time.day,
                meeting_time__time=meeting_time.time
            ).exists()
            
            if existing_entries:
                logger.debug(f"Instructor conflict: {instructor.uid} already teaching at {meeting_time.day} {meeting_time.time}")
                return False
        else:
            # Fallback: get instructors from database (for THEORY/ELECTIVE)
            instructors = self._get_instructors(course, year, section)
            if instructors:
                inst = instructors[0]  # Check first instructor
                for cls in schedule._classes:
                    if cls.instructor == inst and cls.meeting_time.pid == meeting_time.pid:
                        return False
                
                # Check database too
                existing_entries = TimetableEntry.objects.filter(
                    instructor=inst,
                    meeting_time__day=meeting_time.day,
                    meeting_time__time=meeting_time.time
                ).exists()
                
                if existing_entries:
                    return False
        
        # === CRITICAL: Check room conflicts across ALL years (by day+time, not FK) ===
        if room:  # Room was explicitly provided (from LAB scheduling)
            # 1. Check within current schedule
            for cls in schedule._classes:
                if cls.room == room and cls.meeting_time.pid == meeting_time.pid:
                    logger.debug(f"Room conflict in schedule: {room.lab_name} occupied at {meeting_time.day} {meeting_time.time}")
                    return False
            
            # 2. Check database for existing timetables (BY DAY+TIME, not FK - cross-year!)
            # CRITICAL: MeetingTime PIDs differ across years (1st Year=1, 2nd Year=1000)
            # So we MUST filter by day+time, not by meeting_time FK
            existing_entries = TimetableEntry.objects.filter(
                lab_room=room,
                meeting_time__day=meeting_time.day,
                meeting_time__time=meeting_time.time
            ).exists()
            
            if existing_entries:
                logger.debug(f"Room conflict in database: {room.lab_name} already scheduled at {meeting_time.day} {meeting_time.time}")
                return False
                
        elif course.course_type == 'LAB':
            # Fallback: if no room provided but it's a LAB, randomly check (legacy)
            # This shouldn't happen with new code, but kept for safety
            test_room = self._get_lab_room(course)
            if test_room:
                for cls in schedule._classes:
                    if cls.room == test_room and cls.meeting_time.pid == meeting_time.pid:
                        return False
        
        return True
    
    def _schedule_special_periods(self, schedule, data, year, sections):
        """Schedule special periods (Counseling, Training, Sports/Library) - applies to all sections"""
        from .models import SpecialPeriod
        
        # Get all special periods configured for this year
        special_periods = SpecialPeriod.objects.filter(year=year)
        
        if not special_periods.exists():
            logger.info("  No special periods configured for this year")
            return True
        
        logger.info(f"  Found {special_periods.count()} special period type(s) to schedule for all {len(sections)} sections")
        
        # Create pseudo-courses for special periods if they don't exist
        special_courses = {}
        for period_type in ['Counseling', 'Training', 'Sports/Library']:
            course, created = Course.objects.get_or_create(
                course_number=period_type.upper().replace('/', '_'),
                defaults={
                    'course_name': period_type,
                    'max_numb_students': '60',
                    'course_type': 'THEORY',
                    'hours_per_week': 1,
                    'max_continuous_hours': 1,
                    'priority': 0
                }
            )
            special_courses[period_type] = course
        
        # Schedule each special period for ALL sections
        success_count = 0
        total_needed = special_periods.count() * len(sections)
        
        for sp in special_periods:
            course = special_courses[sp.period_type]
            
            # Schedule for each section
            for section in sections:
                # Determine if this is a continuous block requirement (Training = 2 hours)
                if sp.continuous_hours > 1:
                    # Need continuous block
                    if self._schedule_special_continuous(schedule, data, sp, course, year, section):
                        success_count += 1
                        logger.info(f"    [OK] {sp.period_type} Sec {section}: {sp.continuous_hours}hr block")
                    else:
                        logger.warning(f"    [SKIP] Failed to schedule {sp.period_type} Sec {section}")
                else:
                    # Single period
                    if self._schedule_special_single(schedule, data, sp, course, year, section):
                        success_count += 1
                        logger.info(f"    [OK] {sp.period_type} Sec {section}: 1hr")
                    else:
                        logger.warning(f"    [SKIP] Failed to schedule {sp.period_type} Sec {section}")
        
        logger.info(f"  Special periods: {success_count}/{total_needed} scheduled successfully")
        return success_count == total_needed
    
    def _schedule_special_continuous(self, schedule, data, special_period, course, year, section):
        """Schedule a special period that requires continuous hours (e.g., Training)"""
        hours_needed = special_period.continuous_hours
        instructor = special_period.instructor
        
        # Find continuous blocks
        available_blocks = self._find_continuous_blocks(data, hours_needed)
        
        # Filter blocks that don't conflict
        for block in available_blocks:
            if self._can_schedule_block(schedule, section, course, block, instructor, year, None):
                # Schedule the block
                for mt in block:
                    new_class = Class(year, section, course, batch='FULL')
                    new_class.set_meetingTime(mt)
                    new_class.set_instructor(instructor)
                    new_class.set_room(None)
                    schedule._classes.append(new_class)
                return True
        
        return False
    
    def _schedule_special_single(self, schedule, data, special_period, course, year, section):
        """Schedule a single-hour special period (e.g., Counseling, Sports/Library)"""
        instructor = special_period.instructor
        meeting_times = list(data.get_meetingTimes())
        
        # Try to find an available slot (prefer later periods for special periods)
        sorted_times = self._sort_meeting_times_chronologically(meeting_times)
        sorted_times.reverse()  # Prefer later time slots for special periods
        
        for mt in sorted_times:
            if self._can_schedule_single(schedule, section, course, mt, instructor, year):
                new_class = Class(year, section, course, batch='FULL')
                new_class.set_meetingTime(mt)
                new_class.set_instructor(instructor)
                new_class.set_room(None)
                schedule._classes.append(new_class)
                return True
        
        return False
    
    def _get_instructors(self, course, year, section):
        """Get instructors for this course/section"""
        if year and section:
            assigned = CourseInstructorAssignment.objects.filter(
                year=year, section_number=section, course=course
            )
            if assigned.exists():
                return list(assigned.first().instructors.all())
        
        # Fallback to course instructors
        return list(course.instructors.all())
    
    def _get_main_instructor(self, course, year, section):
        """Get the main instructor for this course/section (whose availability determines scheduling)"""
        if year and section:
            assigned = CourseInstructorAssignment.objects.filter(
                year=year, section_number=section, course=course
            )
            if assigned.exists() and assigned.first().main_instructor:
                return assigned.first().main_instructor
        
        # If no main instructor set, fallback to first instructor
        all_instructors = self._get_instructors(course, year, section)
        return all_instructors[0] if all_instructors else None
    
    def _get_department_from_course(self, course):
        """Extract department code from course number (e.g., '23IT4218' -> 'IT')"""
        course_number = course.course_number
        # Extract letters between first numbers and last numbers
        # 23IT4218 -> IT, 23ME3205 -> ME, 23PY1102 -> PY
        import re
        match = re.search(r'\d+([A-Z]+)\d+', course_number)
        if match:
            return match.group(1)
        return None
    
    def _get_available_evaluators(self, schedule, block, course, main_instructor, year=None, max_evaluators=2):
        """
        Auto-select available evaluators from the same department.
        Returns list of instructors who are free during the given time block.
        Tries to get max_evaluators, but returns fewer if not enough are available.
        Checks BOTH current schedule AND existing database entries (for single-year regeneration).
        """
        from .models import Instructor, TimetableEntry
        
        # Get department code from course
        dept_code = course.dept_code
        if not dept_code:
            logger.warning(f"    No department code for {course.course_number}")
            return []
        
        # Get main instructors for ALL sections of this course (to avoid using them as evaluators)
        excluded_instructors = set([main_instructor])  # Always exclude current main instructor
        if year:
            other_main_instructors = CourseInstructorAssignment.objects.filter(
                year=year,
                course=course
            ).exclude(main_instructor__isnull=True)
            
            for assignment in other_main_instructors:
                if assignment.main_instructor:
                    excluded_instructors.add(assignment.main_instructor)
        
        # Get all instructors from this department (using department field)
        dept_instructors = list(Instructor.objects.filter(department=dept_code))
        
        if not dept_instructors:
            logger.warning(f"    No instructors found for department {dept_code}")
            return []
        
        # Randomize order to distribute evaluators more evenly across different labs
        random.shuffle(dept_instructors)
        
        # Filter to find who's available during this block
        available = []
        for instructor in dept_instructors:
            # Skip if this instructor is a main instructor for any section of this course
            if instructor in excluded_instructors:
                continue
            
            # Check if instructor is free during ALL time slots in the block
            is_free = True
            for mt in block:
                # Check current schedule (classes being generated now)
                for existing_class in schedule._classes:
                    if existing_class.meeting_time.pid == mt.pid and existing_class.instructor == instructor:
                        is_free = False
                        break
                
                # CRITICAL: Also check existing database entries (for single-year regeneration)
                # This ensures we don't assign evaluators who are teaching other years
                if is_free:
                    existing_entries = TimetableEntry.objects.filter(
                        instructor=instructor,
                        meeting_time__day=mt.day,
                        meeting_time__time=mt.time
                    )
                    if existing_entries.exists():
                        is_free = False
                
                if not is_free:
                    break
            
            if is_free:
                available.append(instructor)
                if len(available) >= max_evaluators:
                    break  # Got enough evaluators
        
        # Return what we found (might be fewer than max_evaluators, which is OK)
        if len(available) < max_evaluators:
            logger.info(f"    Auto-selected {len(available)}/{max_evaluators} evaluators: {[i.name for i in available]}")
        else:
            logger.info(f"    Auto-selected {len(available)} evaluators: {[i.name for i in available]}")
        return available
    
    def _get_lab_room(self, course):
        """Get available lab room for this course"""
        labs = list(course.lab_rooms.all())
        return random.choice(labs) if labs else None


# REMOVE OLD GA CLASS - NOT NEEDED!
class GeneticAlgorithm:
    """DEPRECATED - Using constraint-based scheduling instead"""
    pass



def context_manager(schedule):
    classes = schedule.getClasses()
    context = []
    for i in range(len(classes)):
        clas = {}
        clas['section'] = classes[i].section_number
        clas['year'] = classes[i].year.year_name
        clas['course'] = f'{classes[i].course.course_name} ({classes[i].course.course_number} {classes[i].course.max_numb_students})'
        clas['room'] = 'Manual Assignment'
        clas['instructor'] = f'{classes[i].instructor.name} ({classes[i].instructor.uid})'
        clas['meeting_time'] = [
            classes[i].meeting_time.pid,
            classes[i].meeting_time.day,
            classes[i].meeting_time.time
        ]
        context.append(clas)
    return context


def apiGenNum(request):
    return JsonResponse({'genNum': VARS['generationNum']})

def apiterminateGens(request):
    VARS['terminateGens'] = True
    return redirect('home')



@login_required
def timetable(request):
    global data
    
    year_id = request.GET.get('year')
    regenerate = request.GET.get('regenerate', 'false') == 'true'

    logger.info("="*80)
    logger.info("TIMETABLE GENERATION - 4-PHASE ALGORITHM (LAB > ELECTIVE > CONTINUOUS THEORY (TP) > REGULAR THEORY)")
    logger.info("="*80)
    
    if not year_id:
        years = Year.objects.all()
        return render(request, 'timetableSelect.html', {'years': years})

    selected_year = Year.objects.get(id=year_id)
    logger.info(f">>> Selected year: {selected_year.year_name} (ID: {year_id})")

    # Check if timetable already exists
    existing_timetable = GeneratedTimetable.objects.filter(year=selected_year).first()
    
    if existing_timetable and not regenerate:
        # Load existing timetable from database
        entries = TimetableEntry.objects.filter(timetable=existing_timetable)
        
        # CRITICAL: Deduplicate entries for multi-instructor labs (but NOT for batch-split labs)
        # Key: (section, course, day, time, batch) → entry
        seen = {}
        unique_entries = []
        for entry in entries:
            # Include batch in the key to keep B1 and B2 separate
            key = (entry.section_number, entry.course_id, entry.meeting_time.day, entry.meeting_time.time, entry.batch)
            if key not in seen:
                seen[key] = entry
                unique_entries.append(entry)
        
        # Convert to class objects for template compatibility
        classes = []
        for entry in unique_entries:
            cls = Class(entry.year, entry.section_number, entry.course, batch=entry.batch)
            cls.set_instructor(entry.instructor)
            cls.set_meetingTime(entry.meeting_time)
            cls.room = entry.lab_room  # Only lab rooms are stored
            classes.append(cls)
        
        data = Data(selected_year)
        
        return render(request, 'timetable.html', {
            'schedule': classes,
            'sections': data.get_sections(),
            'times': data.get_meetingTimes(),
            'timeSlots': TIME_SLOTS,
            'weekDays': DAYS_OF_WEEK,
            'selected_year': selected_year,
            'fitness_score': existing_timetable.fitness_score,
            'generation_count': existing_timetable.generation_count,
            'generated_at': existing_timetable.generated_at,
            'from_database': True
        })
    
    # Generate new timetable
    data = Data(selected_year)
    data.elective_time_tracker = {}
    
    # PRE-ALLOCATE elective times BEFORE creating population
    # This ensures ALL schedules use the same times for electives
    all_courses = selected_year.courses.all()
    elective_courses = all_courses.filter(course_type='ELECTIVE')
    meeting_times = list(MeetingTime.objects.filter(year=selected_year))
    
    logger.info(f"Pre-allocating times for {elective_courses.count()} elective courses...")
    
    if meeting_times:
        for course in elective_courses:
            # Calculate how many hours need single periods vs continuous
            total_hours = course.hours_per_week
            continuous_hours = course.max_continuous_hours if course.max_continuous_hours > 1 else 0
            single_hours = total_hours - continuous_hours
            
            # Track times used for continuous blocks to avoid overlap
            used_times = []
            
            # FIRST: Pre-allocate continuous block(s) if needed
            if continuous_hours > 0:
                # Group meeting times by day and find valid continuous blocks
                day_groups = {}
                for mt in meeting_times:
                    day_groups.setdefault(mt.day, []).append(mt)
                
                for day in day_groups:
                    day_groups[day].sort(key=lambda x: TIME_SLOTS.index((x.time, x.time)))
                
                valid_blocks = []
                for day, times in day_groups.items():
                    for i in range(len(times) - course.max_continuous_hours + 1):
                        block = times[i:i + course.max_continuous_hours]
                        if not any(t.time == "12:15 - 1:05" for t in block):
                            valid_blocks.append(block)
                
                if valid_blocks:
                    block_key = f"{course.course_number}_continuous"
                    selected_block = random.choice(valid_blocks)
                    data.elective_time_tracker[block_key] = selected_block
                    logger.info(f"  {course.course_number} continuous: {selected_block[0].day} {[mt.time for mt in selected_block]}")
                    # Track these times as used to avoid overlap
                    used_times.extend(selected_block)
            
            # SECOND: Pre-allocate single period times from REMAINING times (exclude continuous block times)
            if single_hours > 0:
                available_times = [mt for mt in meeting_times if mt not in used_times]
                if len(available_times) >= single_hours:
                    single_key = f"{course.course_number}_single"
                    # Allocate MULTIPLE times for multiple addCourse() calls
                    # All sections will use these SAME times in the SAME order
                    selected_times = random.sample(available_times, single_hours)
                    data.elective_time_tracker[single_key] = selected_times  # Store as LIST
                    logger.info(f"  {course.course_number} single ({single_hours} periods): {[(t.day, t.time) for t in selected_times]}")
                    
                    # Also create index tracker for each section
                    index_key = f"{course.course_number}_single_index"
                    data.elective_time_tracker[index_key] = {}

    # Log courses ONCE before scheduling
    all_courses = selected_year.courses.all()
    lab_courses = list(all_courses.filter(course_type='LAB').order_by('-priority'))
    elective_courses = list(all_courses.filter(course_type='ELECTIVE').order_by('-priority'))
    all_theory = all_courses.filter(course_type='THEORY').order_by('-priority')
    continuous_theory_courses = list(all_theory.filter(max_continuous_hours__gt=1))
    regular_theory_courses = list(all_theory.filter(max_continuous_hours=1))
    
    logger.info("=== COURSES TO BE SCHEDULED ===")
    logger.info(f"LAB ({len(lab_courses)}): {[c.course_number for c in lab_courses]}")
    logger.info(f"ELECTIVE ({len(elective_courses)}): {[c.course_number for c in elective_courses]}")
    logger.info(f"CONTINUOUS THEORY ({len(continuous_theory_courses)}): {[c.course_number for c in continuous_theory_courses]} (TP courses needing 2+ continuous hours)")
    logger.info(f"REGULAR THEORY ({len(regular_theory_courses)}): {[c.course_number for c in regular_theory_courses]}")

    # === NEW: CONSTRAINT-BASED SCHEDULING (NO MORE GA!) ===
    logger.info(">>> Starting CONSTRAINT-BASED scheduling (guaranteed conflict-free!)")
    scheduler = ConstraintScheduler()
    schedule = None
    
    # Try up to MAX_ATTEMPTS times
    for attempt in range(1, MAX_ATTEMPTS + 1):
        logger.info(f"Attempt {attempt}/{MAX_ATTEMPTS}...")
        schedule = scheduler.build_schedule(data, selected_year)
        
        if schedule:
            # SUCCESS: Schedule was created (even if not perfect)
            # The fitness score will reflect quality issues like non-continuous TP courses
            conflicts = schedule.getNumbOfConflicts()
            fitness = schedule.getFitness()
            
            # Optional: Check if TP courses are continuous (soft check, doesn't reject)
            tp_continuous = schedule.validate_continuous_theory_strict()
            if not tp_continuous:
                logger.warning(f"[WARN] Attempt {attempt}: TP courses not all continuous (fitness: {fitness:.2%}, conflicts: {conflicts})")
            else:
                logger.info(f"[OK] Attempt {attempt}: TP courses are continuous (fitness: {fitness:.2%}, conflicts: {conflicts})")
            
            # Accept any schedule that was successfully created
            # Prefer schedules with better fitness, but don't reject imperfect ones
            logger.info(f"SUCCESS on attempt {attempt}! Schedule created with {len(schedule.getClasses())} classes")
            break
        else:
            logger.warning(f"✗ Attempt {attempt} failed, retrying...")
    
    if not schedule:
        logger.error(f"FAILED to create schedule after {MAX_ATTEMPTS} attempts")
        
        # Fall back to existing timetable if available
        if existing_timetable:
            entries = TimetableEntry.objects.filter(timetable=existing_timetable)
            
            # Deduplicate entries for multi-instructor labs
            seen = {}
            unique_entries = []
            for entry in entries:
                key = (entry.section_number, entry.course_id, entry.meeting_time.day, entry.meeting_time.time)
                if key not in seen:
                    seen[key] = entry
                    unique_entries.append(entry)
            
            classes = []
            for entry in unique_entries:
                cls = Class(entry.year, entry.section_number, entry.course)
                cls.set_instructor(entry.instructor)
                cls.set_meetingTime(entry.meeting_time)
                cls.room = entry.lab_room  # Only lab rooms are stored
                classes.append(cls)
            
            return render(request, 'timetable.html', {
                'schedule': classes,
                'sections': data.get_sections(),
                'times': data.get_meetingTimes(),
                'timeSlots': TIME_SLOTS,
                'weekDays': DAYS_OF_WEEK,
                'selected_year': selected_year,
                'fitness_score': existing_timetable.fitness_score,
                'generation_count': existing_timetable.generation_count,
                'generated_at': existing_timetable.generated_at,
                'from_database': True,
                'generation_failed': True,
                'error_message': 'Constraint-based scheduling failed. Showing previous timetable instead.'
            })
        else:
            # No existing timetable to fall back to
            return render(request, 'timetable.html', {
                'schedule': [],
                'sections': data.get_sections(),
                'times': data.get_meetingTimes(),
                'timeSlots': TIME_SLOTS,
                'weekDays': DAYS_OF_WEEK,
                'selected_year': selected_year,
                'fitness_score': 0,
                'generation_count': 0,
                'from_database': False,
                'generation_failed': True,
                'error_message': f'Constraint-based scheduling failed after {MAX_ATTEMPTS} attempts. Please check your data.'
            })
    
    # === SUCCESS: Save the conflict-free schedule to database ===
    logger.info(">>> Saving conflict-free schedule to database...")
    
    if existing_timetable:
        # Delete old entries
        TimetableEntry.objects.filter(timetable=existing_timetable).delete()
        timetable_obj = existing_timetable
    else:
        timetable_obj = GeneratedTimetable.objects.create(year=selected_year)
    
    # Calculate actual fitness based on conflicts (constraint-based should have minimal conflicts)
    schedule_fitness = schedule.getFitness()
    schedule_conflicts = schedule.getNumbOfConflicts()
    
    timetable_obj.fitness_score = schedule_fitness
    timetable_obj.generation_count = attempt  # Number of attempts it took
    timetable_obj.save()
    
    logger.info(f">>> Schedule quality: {schedule_fitness:.2%} fitness, {schedule_conflicts} conflicts")
    
    # Save all class entries
    for cls in schedule.getClasses():
        # For LAB courses with batch splitting, save batch info and create entries for all instructors
        if cls.course.split_into_batches and cls.batch != 'FULL':
            from .models import LabBatchAssignment
            
            # Get the batch assignment to find all instructors
            batch_assignment = LabBatchAssignment.objects.filter(
                year=selected_year,
                section_number=cls.section_number,
                course=cls.course,
                batch=cls.batch
            ).first()
            
            if batch_assignment and batch_assignment.instructors.exists():
                # Create entry for EACH instructor assigned to this batch
                for instructor in batch_assignment.instructors.all():
                    TimetableEntry.objects.get_or_create(
                        timetable=timetable_obj,
                        year=selected_year,
                        section_number=cls.section_number,
                        course=cls.course,
                        instructor=instructor,
                        lab_room=cls.room,
                        meeting_time=cls.meeting_time,
                        batch=cls.batch,  # B1 or B2
                        is_evaluator=False  # Batch split instructors are not evaluators
                    )
            else:
                # Fallback: use the instructor from the class
                TimetableEntry.objects.get_or_create(
                    timetable=timetable_obj,
                    year=selected_year,
                    section_number=cls.section_number,
                    course=cls.course,
                    instructor=cls.instructor,
                    lab_room=cls.room,
                    meeting_time=cls.meeting_time,
                    batch=cls.batch,  # B1 or B2
                    is_evaluator=False  # Batch split instructors are not evaluators
                )
        # For LAB courses with multiple instructors (non-split), create entry for EACH instructor
        elif cls.course.course_type == 'LAB':
            # Use the is_evaluator flag from the Class object
            # Debug: Log what we're saving
            logger.info(f"DEBUG-SAVE: {cls.course.course_number} Sec{cls.section_number}, {cls.instructor.name if cls.instructor else 'N/A'}, is_evaluator={cls.is_evaluator}")
            
            # Use update_or_create to ensure is_evaluator is set correctly
            TimetableEntry.objects.update_or_create(
                timetable=timetable_obj,
                year=selected_year,
                section_number=cls.section_number,
                course=cls.course,
                instructor=cls.instructor,
                meeting_time=cls.meeting_time,
                defaults={
                    'lab_room': cls.room,
                    'batch': 'FULL',
                    'is_evaluator': cls.is_evaluator  # Mark evaluators vs main instructor
                }
            )
        else:
            # For THEORY/ELECTIVE courses: single instructor entry
            TimetableEntry.objects.get_or_create(
                timetable=timetable_obj,
                year=selected_year,
                section_number=cls.section_number,
                course=cls.course,
                instructor=cls.instructor,
                lab_room=None,
                meeting_time=cls.meeting_time,
                batch='FULL',
                is_evaluator=False  # Theory/elective instructors are not evaluators
            )

    # ========================================================================
    # ADD COUNSELLING AND SPORTS PERIODS (POST-PROCESSING)
    # ========================================================================
    # After main timetable is generated, add 1 counselling + 1 sports period per section
    # Requirements:
    # - Prefer last periods (late in day)
    # - Counselling and sports on DIFFERENT days
    # - 1 hour each per week, separate for each section
    
    logger.info("Adding counselling and sports periods...")
    
    slot_order = [t[0] for t in TIME_SLOTS]
    all_meeting_times = list(data.get_meetingTimes())
    
    # Create pseudo-courses for counselling and sports (for display purposes)
    # These won't be actual Course objects, just for the timetable display
    from collections import namedtuple
    PseudoCourse = namedtuple('PseudoCourse', ['course_number', 'course_name', 'course_type'])
    counselling_course = PseudoCourse('COUNS', 'Counselling', 'SPECIAL')
    sports_course = PseudoCourse('SPORT', 'Sports', 'SPECIAL')
    
    # Get or create placeholder course objects (if they don't exist)
    counselling_obj, _ = Course.objects.get_or_create(
        course_number='COUNS',
        defaults={
            'course_name': 'Counselling',
            'max_numb_students': '60',
            'course_type': 'THEORY',  # Use THEORY as base type
            'hours_per_week': 1,
            'max_continuous_hours': 1,
            'priority': 0
        }
    )
    
    sports_obj, _ = Course.objects.get_or_create(
        course_number='SPORT',
        defaults={
            'course_name': 'Sports',
            'max_numb_students': '60',
            'course_type': 'THEORY',
            'hours_per_week': 1,
            'max_continuous_hours': 1,
            'priority': 0
        }
    )
    
    # Get or create a default instructor for activity periods
    activity_instructor, _ = Instructor.objects.get_or_create(
        name='Activity Coordinator',
        defaults={'uid': 'ACTIVITY001'}
    )
    
    for section_number in data.get_sections():
        # Get existing classes for this section
        existing_slots = set()
        for cls in schedule.getClasses():
            if cls.section_number == section_number:
                existing_slots.add((cls.meeting_time.day, cls.meeting_time.time))
        
        # Find available slots, preferring late periods
        available_by_day = {}
        for mt in all_meeting_times:
            if (mt.day, mt.time) not in existing_slots:
                if mt.day not in available_by_day:
                    available_by_day[mt.day] = []
                available_by_day[mt.day].append(mt)
        
        # Sort each day's slots by time (latest first for preference)
        for day in available_by_day:
            available_by_day[day].sort(key=lambda mt: slot_order.index(mt.time), reverse=True)
        
        # Get days with available slots
        available_days = [day for day in available_by_day if available_by_day[day]]
        
        if len(available_days) >= 2:
            # Randomly select 2 different days
            selected_days = random.sample(available_days, 2)
            counselling_day = selected_days[0]
            sports_day = selected_days[1]
            
            # Get the latest available slot on each day
            counselling_mt = available_by_day[counselling_day][0]  # First item (latest due to reverse sort)
            sports_mt = available_by_day[sports_day][0]
            
            # Add counselling period (use get_or_create to prevent duplicates)
            TimetableEntry.objects.get_or_create(
                timetable=timetable_obj,
                year=selected_year,
                section_number=section_number,
                course=counselling_obj,
                instructor=activity_instructor,  # Default activity coordinator
                lab_room=None,
                meeting_time=counselling_mt
            )
            
            # Add sports period (use get_or_create to prevent duplicates)
            TimetableEntry.objects.get_or_create(
                timetable=timetable_obj,
                year=selected_year,
                section_number=section_number,
                course=sports_obj,
                instructor=activity_instructor,  # Default activity coordinator
                lab_room=None,
                meeting_time=sports_mt
            )
            
            logger.info(f"Section {section_number}: Added Counselling on {counselling_mt.day} {counselling_mt.time}, Sports on {sports_mt.day} {sports_mt.time}")
        else:
            logger.warning(f"Section {section_number}: Not enough available days for counselling and sports")

    return render(request, 'timetable.html', {
        'schedule': schedule.getClasses(),
        'sections': data.get_sections(),
        'times': data.get_meetingTimes(),
        'timeSlots': TIME_SLOTS,
        'weekDays': DAYS_OF_WEEK,
        'selected_year': selected_year,
        'fitness_score': schedule.getFitness(),
        'generation_count': VARS['generationNum'],
        'from_database': False
    })



@login_required
def instructor_timetable_select(request):
    """Show instructor selection page"""
    instructors = Instructor.objects.all().order_by('name')
    return render(request, 'instructor_timetable_select.html', {
        'instructors': instructors
    })


@login_required
def instructor_timetable(request):
    """Show individual instructor's timetable across all years"""
    
    instructor_id = request.GET.get('instructor')
    
    # If no instructor selected, redirect to selection page
    if not instructor_id:
        return instructor_timetable_select(request)
    
    try:
        selected_instructor = Instructor.objects.get(id=instructor_id)
    except Instructor.DoesNotExist:
        return instructor_timetable_select(request)
    
    # Get all timetable entries for this instructor
    entries = TimetableEntry.objects.filter(instructor=selected_instructor).select_related(
        'course', 'year', 'meeting_time', 'lab_room'
    )
    
    # Deduplicate entries to prevent overlaps in display
    # Key: (year, section, course, day, time, room) → entry
    seen = {}
    unique_entries = []
    
    for entry in entries:
        key = (
            entry.year_id,
            entry.section_number,
            entry.course_id,
            entry.meeting_time.day,
            entry.meeting_time.time,
            entry.lab_room_id if entry.lab_room else None
        )
        if key not in seen:
            seen[key] = entry
            unique_entries.append(entry)
    
    # Convert to class objects for template compatibility
    classes = []
    for entry in unique_entries:
        cls = Class(entry.year, entry.section_number, entry.course)
        cls.set_instructor(entry.instructor)
        cls.set_meetingTime(entry.meeting_time)
        cls.room = entry.lab_room
        classes.append(cls)
    
    return render(request, 'instructor_timetable.html', {
        'schedule': classes,
        'instructor': selected_instructor,
        'timeSlots': TIME_SLOTS,
        'weekDays': DAYS_OF_WEEK,
        'total_classes': len(classes)
    })


@login_required
def lab_timetable(request):
    """Show lab room usage schedule from all stored timetables"""
    
    # Get all lab entries
    lab_entries = TimetableEntry.objects.filter(lab_room__isnull=False).select_related(
        'lab_room', 'year', 'course', 'meeting_time'
    )
    
    # Deduplicate entries for multi-instructor labs
    seen = {}
    unique_lab_entries = []
    for entry in lab_entries:
        key = (entry.year_id, entry.section_number, entry.course_id, entry.meeting_time.day, entry.meeting_time.time, entry.lab_room_id)
        if key not in seen:
            seen[key] = entry
            unique_lab_entries.append(entry)
    
    # Convert to class objects for template compatibility
    classes = []
    for entry in unique_lab_entries:
        cls = Class(entry.year, entry.section_number, entry.course)
        cls.set_instructor(entry.instructor)
        cls.set_meetingTime(entry.meeting_time)
        cls.room = entry.lab_room
        classes.append(cls)
    
    return render(request, 'lab_timetable.html', {
        'schedule': classes,
        'labs': LabRoom.objects.all(),
        'timeSlots': TIME_SLOTS,
        'weekDays': DAYS_OF_WEEK
    })


@login_required
def view_timetable(request):
    """
    Unified view for displaying timetables with multiple filtering options:
    - Section-wise: View specific section or all sections
    - Year-wise: View specific year
    - Department-wise: View specific department (if implemented)
    - Faculty-wise: View single faculty or all faculties
    - Lab-wise: View single lab or all labs
    - Period-wise: View who's FREE at a specific day/time
    """
    
    view_type = request.GET.get('view_type', '')
    
    # Prepare context with all possible filter options
    context = {
        'view_type': view_type,
        'years': Year.objects.all().order_by('year_name'),
        'instructors': Instructor.objects.all().order_by('name'),
        'labs': LabRoom.objects.all().order_by('lab_name'),
        'sections': [1, 2, 3],
        'timeSlots': [slot[0] for slot in TIME_SLOTS],  # Extract values from tuples
        'weekDays': [day[0] for day in DAYS_OF_WEEK],    # Extract values from tuples
        'schedule': [],
        'total_classes': 0
    }
    
    # If no view type selected, just show the filter form
    if not view_type:
        return render(request, 'view_timetable.html', context)
    
    # SECTION-WISE
    if view_type == 'section':
        year_id = request.GET.get('year')
        section_num = request.GET.get('section')
        
        if year_id and section_num:
            entries = TimetableEntry.objects.filter(
                year_id=year_id,
                section_number=section_num
            ).select_related('course', 'instructor', 'meeting_time', 'lab_room', 'year')
            
            context['selected_year'] = Year.objects.get(id=year_id)
            context['selected_section'] = section_num
            context['schedule'] = _convert_entries_to_classes(entries)
            context['total_classes'] = len(context['schedule'])
    
    # YEAR-WISE (all sections in a year)
    elif view_type == 'year':
        year_id = request.GET.get('year')
        
        if year_id:
            selected_year = Year.objects.get(id=year_id)
            context['selected_year'] = selected_year
            
            # Group schedules by section
            sections_data = []
            for section_num in [1, 2, 3]:
                entries = TimetableEntry.objects.filter(
                    year_id=year_id,
                    section_number=section_num
                ).select_related('course', 'instructor', 'meeting_time', 'lab_room', 'year')
                
                if entries.exists():
                    sections_data.append({
                        'section_number': section_num,
                        'schedule': _convert_entries_to_classes(entries),
                        'total_classes': entries.count()
                    })
            
            context['sections_data'] = sections_data
            context['total_classes'] = sum(s['total_classes'] for s in sections_data)
    
    # FACULTY-WISE
    elif view_type == 'faculty':
        faculty_id = request.GET.get('faculty')
        all_faculties = request.GET.get('all_faculties') == 'true'
        
        if all_faculties:
            # Show all faculties' schedules separately
            faculties_data = []
            instructors = Instructor.objects.all().order_by('name')
            
            for instructor in instructors:
                entries = TimetableEntry.objects.filter(
                    instructor=instructor
                ).select_related('course', 'instructor', 'meeting_time', 'lab_room', 'year')
                
                if entries.exists():
                    faculties_data.append({
                        'instructor': instructor,
                        'schedule': _convert_entries_to_classes(entries),
                        'total_classes': entries.count()
                    })
            
            context['all_faculties_view'] = True
            context['faculties_data'] = faculties_data
            context['total_classes'] = sum(f['total_classes'] for f in faculties_data)
            
        elif faculty_id:
            # Show single faculty schedule
            entries = TimetableEntry.objects.filter(
                instructor_id=faculty_id
            ).select_related('course', 'instructor', 'meeting_time', 'lab_room', 'year')
            
            context['selected_faculty'] = Instructor.objects.get(id=faculty_id)
            context['schedule'] = _convert_entries_to_classes(entries)
            context['total_classes'] = len(context['schedule'])
    
    # LAB-WISE
    elif view_type == 'lab':
        lab_id = request.GET.get('lab')
        all_labs = request.GET.get('all_labs') == 'true'
        
        if all_labs:
            # Show all labs' schedules separately
            labs_data = []
            lab_rooms = LabRoom.objects.all().order_by('lab_name')
            
            for lab in lab_rooms:
                entries = TimetableEntry.objects.filter(
                    lab_room=lab
                ).select_related('course', 'instructor', 'meeting_time', 'lab_room', 'year')
                
                if entries.exists():
                    labs_data.append({
                        'lab': lab,
                        'schedule': _convert_entries_to_classes(entries),
                        'total_classes': entries.count()
                    })
            
            context['all_labs_view'] = True
            context['labs_data'] = labs_data
            context['total_classes'] = sum(l['total_classes'] for l in labs_data)
            
        elif lab_id:
            # Show single lab schedule
            entries = TimetableEntry.objects.filter(
                lab_room_id=lab_id
            ).select_related('course', 'instructor', 'meeting_time', 'lab_room', 'year')
            
            context['selected_lab'] = LabRoom.objects.get(id=lab_id)
            context['schedule'] = _convert_entries_to_classes(entries)
            context['total_classes'] = len(context['schedule'])
    
    # PERIOD-WISE (Show who's FREE at a specific time)
    elif view_type == 'period':
        day = request.GET.get('day')
        time_slot = request.GET.get('time')
        
        if day and time_slot:
            # Get all faculty teaching at this time
            busy_faculty = TimetableEntry.objects.filter(
                meeting_time__day=day,
                meeting_time__time=time_slot,
                instructor__isnull=False
            ).values_list('instructor_id', flat=True).distinct()
            
            # Get free faculty
            all_faculty = Instructor.objects.all()
            free_faculty = all_faculty.exclude(id__in=busy_faculty)
            
            # Get busy faculty details
            busy_entries = TimetableEntry.objects.filter(
                meeting_time__day=day,
                meeting_time__time=time_slot,
                instructor__isnull=False
            ).select_related('course', 'instructor', 'meeting_time', 'year')
            
            context['selected_day'] = day
            context['selected_time'] = time_slot
            context['free_faculty'] = free_faculty
            context['busy_faculty'] = busy_entries
            context['total_free'] = free_faculty.count()
            context['total_busy'] = busy_entries.count()
    
    return render(request, 'view_timetable.html', context)


def _convert_entries_to_classes(entries):
    """Helper function to convert TimetableEntry queryset to Class objects"""
    seen = {}
    unique_entries = []
    
    for entry in entries:
        key = (
            entry.year_id,
            entry.section_number,
            entry.course_id,
            entry.meeting_time.day,
            entry.meeting_time.time,
            entry.lab_room_id if entry.lab_room else None
        )
        if key not in seen:
            seen[key] = entry
            unique_entries.append(entry)
    
    classes = []
    for entry in unique_entries:
        cls = Class(entry.year, entry.section_number, entry.course)
        cls.set_instructor(entry.instructor)
        cls.set_meetingTime(entry.meeting_time)
        cls.room = entry.lab_room
        classes.append(cls)
    
    return classes


'''
Page Views
'''

def home(request):
    return render(request, 'index.html', {})


@login_required
def data_check(request):
    """Diagnostic view to check what data exists for timetable generation"""
    year_id = request.GET.get('year')
    
    if not year_id:
        years = Year.objects.all()
        return render(request, 'data_check_select.html', {'years': years})
    
    selected_year = Year.objects.get(id=year_id)
    
    # Gather all data statistics
    data_info = {
        'year': selected_year,
        'total_lab_rooms': LabRoom.objects.count(),
        'total_instructors': Instructor.objects.count(),
        'year_courses': selected_year.courses.all(),
        'year_meeting_times': MeetingTime.objects.filter(year=selected_year),
        'year_sections': [1, 2, 3],  # Fixed 3 sections per year
        'all_assignments': CourseInstructorAssignment.objects.filter(
            year=selected_year
        ),
    }
    
    # Check for issues
    issues = []
    
    if data_info['year_courses'].count() == 0:
        issues.append(f"⚠️ No courses linked to {selected_year.year_name}! Edit year at /yearEdit/ and select courses")
    
    if data_info['year_meeting_times'].count() == 0:
        issues.append(f"⚠️ No meeting times for {selected_year.year_name}! Add time slots at /meetingTimeAdd/ and select this year")
    
    # Check for lab courses without lab rooms
    lab_courses = data_info['year_courses'].filter(course_type='LAB')
    if lab_courses.exists() and data_info['total_lab_rooms'] == 0:
        issues.append("⚠️ Lab courses exist but no lab rooms! Add lab rooms at /labRoomAdd/")
    
    # Check for courses without instructor assignments
    for section_number in data_info['year_sections']:
        for course in data_info['year_courses']:
            assignment = CourseInstructorAssignment.objects.filter(
                year=selected_year, section_number=section_number, course=course
            ).first()
            if not assignment:
                issues.append(f"⚠️ No instructor assigned for {course.course_number} in section {section_number}")
            elif assignment.instructors.count() == 0:
                issues.append(f"⚠️ No instructors selected for {course.course_number} in section {section_number}")
    
    data_info['issues'] = issues
    data_info['ready'] = len(issues) == 0
    
    return render(request, 'data_check.html', data_info)


@login_required
def instructorAdd(request):
    form = InstructorForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('instructorAdd')
    context = {'form': form}
    return render(request, 'instructorAdd.html', context)


@login_required
def instructorEdit(request):
    context = {'instructors': Instructor.objects.all()}
    return render(request, 'instructorEdit.html', context)


@login_required
def instructorUpdate(request, pk):
    instructor = Instructor.objects.get(pk=pk)
    form = InstructorForm(request.POST or None, instance=instructor)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('instructorEdit')
    context = {
        'instructor': instructor,
        'form': form
    }
    return render(request, 'instructorUpdate.html', context)


@login_required
def instructorDelete(request, pk):
    inst = Instructor.objects.filter(pk=pk)
    if request.method == 'POST':
        inst.delete()
        return redirect('instructorEdit')


@login_required
def labRoomAdd(request):
    form = LabRoomForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('labRoomAdd')
    return render(request, 'labRoomAdd.html', {'form': form})


@login_required
def labRoomEdit(request):
    return render(request, 'labRoomEdit.html', {
        'labs': LabRoom.objects.all()
    })


@login_required
def labRoomUpdate(request, pk):
    lab = LabRoom.objects.get(pk=pk)
    form = LabRoomForm(request.POST or None, instance=lab)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('labRoomEdit')
    return render(request, 'labRoomUpdate.html', {'lab': lab, 'form': form})


@login_required
def labRoomDelete(request, pk):
    lab = LabRoom.objects.filter(pk=pk)
    if request.method == 'POST':
        lab.delete()
        return redirect('labRoomEdit')



@login_required
def meetingTimeAdd(request):
    if request.method == 'POST':
        year_id = request.POST.get('year')
        selected_days = request.POST.getlist('days')
        
        if year_id and selected_days:
            year = Year.objects.get(id=year_id)
            created_count = 0
            
            # Determine lunch break based on year
            # 1st Year has lunch at 11:25-12:15, others at 12:15-1:05
            is_first_year = '1st' in year.year_name.lower() or '1' in year.year_name
            lunch_break = '11:25 - 12:15' if is_first_year else '12:15 - 1:05'
            
            # Get all time slots except lunch break
            time_slots = [slot[0] for slot in TIME_SLOTS if slot[0] != lunch_break]
            
            # Find the highest numeric PID to start from
            all_pids = MeetingTime.objects.all().values_list('pid', flat=True)
            max_pid = 0
            for pid in all_pids:
                try:
                    pid_num = int(pid)
                    if pid_num > max_pid:
                        max_pid = pid_num
                except:
                    pass
            
            current_pid = max_pid
            
            # Create meeting times for each day and time slot
            for day in selected_days:
                for time_slot in time_slots:
                    # Check if this combination already exists
                    if not MeetingTime.objects.filter(year=year, day=day, time=time_slot).exists():
                        current_pid += 1
                        
                        # Create meeting time
                        MeetingTime.objects.create(
                            pid=str(current_pid),
                            year=year,
                            day=day,
                            time=time_slot
                        )
                        created_count += 1
            
            # Redirect with success message
            return redirect('meetingTimeEdit')
    
    context = {
        'years': Year.objects.all(),
        'days': DAYS_OF_WEEK,
        'time_slots': TIME_SLOTS
    }
    return render(request, 'meetingTimeAdd.html', context)


@login_required
def meetingTimeEdit(request):
    context = {'meeting_times': MeetingTime.objects.all()}
    return render(request, 'meetingTimeEdit.html', context)


@login_required
def meetingTimeUpdate(request, pk):
    mt = MeetingTime.objects.get(pk=pk)
    form = MeetingTimeForm(request.POST or None, instance=mt)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('meetingTimeEdit')
    return render(request, 'meetingTimeUpdate.html', {'meeting_time': mt, 'form': form})


@login_required
def meetingTimeDelete(request, pk):
    mt = MeetingTime.objects.filter(pk=pk)
    if request.method == 'POST':
        mt.delete()
        return redirect('meetingTimeEdit')


@login_required
def courseAdd(request):
    form = CourseForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            year = form.cleaned_data.get('year')
            course_type = form.cleaned_data.get('course_type')
            
            # Save the course
            course = form.save(commit=False)
            course.save()
            
            # Save many-to-many relationships (lab_rooms)
            form.save_m2m()
            
            # Add course to the year
            year.courses.add(course)
            
            # Handle instructor assignments based on course type
            if course_type == 'LAB':
                # For LAB courses, use multiple instructors
                instructor_mapping = [
                    form.cleaned_data.get('section_1_lab_instructors'),
                    form.cleaned_data.get('section_2_lab_instructors'),
                    form.cleaned_data.get('section_3_lab_instructors')
                ]
                
                # Create CourseInstructorAssignment for each of the 3 sections
                for section_num in [1, 2, 3]:
                    instructors = instructor_mapping[section_num - 1]  # section_num is 1-indexed
                    
                    # Add all instructors to course's instructors if not already added
                    for instructor in instructors:
                        course.instructors.add(instructor)
                    
                    # Create or get assignment
                    assignment, created = CourseInstructorAssignment.objects.get_or_create(
                        year=year,
                        section_number=section_num,
                        course=course
                    )
                    
                    # Add all instructors to this assignment
                    assignment.instructors.set(instructors)
            else:
                # For THEORY/ELECTIVE courses, use single instructor
                instructor_mapping = [
                    form.cleaned_data.get('section_1_instructor'),
                    form.cleaned_data.get('section_2_instructor'),
                    form.cleaned_data.get('section_3_instructor')
                ]
                
                # Create CourseInstructorAssignment for each of the 3 sections
                for section_num in [1, 2, 3]:
                    instructor = instructor_mapping[section_num - 1]  # section_num is 1-indexed
                    
                    if instructor:
                        # Add instructor to course's instructors if not already added
                        course.instructors.add(instructor)
                        
                        # Create or get assignment
                        assignment, created = CourseInstructorAssignment.objects.get_or_create(
                            year=year,
                            section_number=section_num,
                            course=course
                        )
                        
                        # Add single instructor to this assignment
                        assignment.instructors.set([instructor])
            
            return redirect('courseAdd')
        else:
            logger.warning("Invalid Course form submission by user %s", request.user.username)
    context = {'form': form}
    return render(request, 'courseAdd.html', context)


@login_required
def courseEdit(request):
    instructor = defaultdict(list)
    for course in Course.instructors.through.objects.all():
        course_number = course.course_id
        instructor_name = Instructor.objects.filter(
            id=course.instructor_id).values('name')[0]['name']
        instructor[course_number].append(instructor_name)

    context = {'courses': Course.objects.all(), 'instructor': instructor}
    return render(request, 'courseEdit.html', context)


@login_required
def courseUpdate(request, pk):
    course = Course.objects.get(pk=pk)
    
    # Get existing assignments to pre-populate the form
    initial_data = {}
    
    # Get the year this course belongs to
    year = course.year_set.first()
    if year:
        initial_data['year'] = year
        
        # Get existing assignments for each section
        for section_num in [1, 2, 3]:
            assignment = CourseInstructorAssignment.objects.filter(
                year=year,
                section_number=section_num,
                course=course
            ).first()
            
            if assignment and assignment.instructors.exists():
                if course.course_type == 'LAB':
                    # For lab courses, get all instructors
                    initial_data[f'section_{section_num}_lab_instructors'] = assignment.instructors.all()
                else:
                    # For theory/elective, get first instructor
                    initial_data[f'section_{section_num}_instructor'] = assignment.instructors.first()
    
    form = CourseForm(request.POST or None, instance=course, initial=initial_data)
    
    if request.method == 'POST':
        if form.is_valid():
            year = form.cleaned_data.get('year')
            course_type = form.cleaned_data.get('course_type')
            
            # Save the course
            course = form.save(commit=False)
            course.save()
            
            # Save many-to-many relationships (lab_rooms)
            form.save_m2m()
            
            # Update year association
            if year:
                # Remove from old years and add to new year
                course.year_set.clear()
                year.courses.add(course)
            
            # Handle instructor assignments based on course type
            if course_type == 'LAB':
                # For LAB courses, use multiple instructors
                instructor_mapping = [
                    form.cleaned_data.get('section_1_lab_instructors'),
                    form.cleaned_data.get('section_2_lab_instructors'),
                    form.cleaned_data.get('section_3_lab_instructors')
                ]
                
                # Update CourseInstructorAssignment for each of the 3 sections
                for section_num in [1, 2, 3]:
                    instructors = instructor_mapping[section_num - 1]
                    
                    # Clear and add all instructors to course's instructors
                    for instructor in instructors:
                        course.instructors.add(instructor)
                    
                    # Create or get assignment
                    assignment, created = CourseInstructorAssignment.objects.get_or_create(
                        year=year,
                        section_number=section_num,
                        course=course
                    )
                    
                    # Update instructors for this assignment
                    assignment.instructors.set(instructors)
            else:
                # For THEORY/ELECTIVE courses, use single instructor
                instructor_mapping = [
                    form.cleaned_data.get('section_1_instructor'),
                    form.cleaned_data.get('section_2_instructor'),
                    form.cleaned_data.get('section_3_instructor')
                ]
                
                # Update CourseInstructorAssignment for each of the 3 sections
                for section_num in [1, 2, 3]:
                    instructor = instructor_mapping[section_num - 1]
                    
                    if instructor:
                        # Add instructor to course's instructors if not already added
                        course.instructors.add(instructor)
                        
                        # Create or get assignment
                        assignment, created = CourseInstructorAssignment.objects.get_or_create(
                            year=year,
                            section_number=section_num,
                            course=course
                        )
                        
                        # Update instructor for this assignment
                        assignment.instructors.set([instructor])
                    else:
                        # If no instructor selected, clear the assignment
                        CourseInstructorAssignment.objects.filter(
                            year=year,
                            section_number=section_num,
                            course=course
                        ).delete()
            
            return redirect('courseEdit')
    
    return render(request, 'courseUpdate.html', {'course': course, 'form': form})


@login_required
def courseDelete(request, pk):
    crs = Course.objects.filter(pk=pk)
    if request.method == 'POST':
        crs.delete()
        return redirect('courseEdit')



@login_required
def yearAdd(request):
    form = YearForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('yearAdd')
    return render(request, 'yearAdd.html', {'form': form})


@login_required
def yearEdit(request):
    return render(request, 'yearEdit.html', {
        'years': Year.objects.all()
    })


@login_required
def yearUpdate(request, pk):
    year = Year.objects.get(pk=pk)
    form = YearForm(request.POST or None, instance=year)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('yearEdit')
    return render(request, 'yearUpdate.html', {'year': year, 'form': form})


@login_required
def yearDelete(request, pk):
    yr = Year.objects.filter(pk=pk)
    if request.method == 'POST':
        yr.delete()
        return redirect('yearEdit')



# Section views removed - using fixed 3 sections per year


'''
PDF Download functionality
'''
@login_required
def download_timetable_pdf(request):
    """Generate and download timetable as PDF"""
    from django.http import HttpResponse
    from django.template.loader import render_to_string
    from xhtml2pdf import pisa
    from io import BytesIO
    
    year_id = request.GET.get('year')
    section = request.GET.get('section')  # Optional: specific section
    
    if not year_id:
        return HttpResponse("Year parameter required", status=400)
    
    try:
        selected_year = Year.objects.get(id=year_id)
    except Year.DoesNotExist:
        return HttpResponse("Year not found", status=404)
    
    # Get latest timetable for this year
    timetable_obj = GeneratedTimetable.objects.filter(year=selected_year).order_by('-generated_at').first()
    
    if not timetable_obj:
        return HttpResponse("No timetable found for this year", status=404)
    
    # Get all entries
    entries = TimetableEntry.objects.filter(timetable=timetable_obj).select_related(
        'course', 'instructor', 'meeting_time', 'lab_room'
    )
    
    # Deduplicate entries for multi-instructor labs
    seen = {}
    unique_entries = []
    for entry in entries:
        key = (entry.section_number, entry.course_id, entry.meeting_time.day, entry.meeting_time.time)
        if key not in seen:
            seen[key] = entry
            unique_entries.append(entry)
    
    # Convert to class objects for template
    schedule = []
    for entry in unique_entries:
        cls = Class(entry.year, entry.section_number, entry.course)
        cls.set_instructor(entry.instructor)
        cls.set_meetingTime(entry.meeting_time)
        cls.room = entry.lab_room
        schedule.append(cls)
    
    # Filter by section if specified
    sections = [int(section)] if section else [1, 2, 3]
    
    # Render HTML template with context
    html_string = render_to_string('timetable_pdf.html', {
        'schedule': schedule,
        'sections': sections,
        'timeSlots': TIME_SLOTS,
        'weekDays': DAYS_OF_WEEK,
        'selected_year': selected_year,
        'generated_at': timetable_obj.generated_at,
        'fitness_score': timetable_obj.fitness_score * 100,
    })
    
    # Create PDF
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html_string.encode("UTF-8")), result)
    
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        filename = f'{selected_year.year_name}_Timetable'
        if section:
            filename += f'_Section{section}'
        filename += '.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    
    return HttpResponse('Error generating PDF', status=500)


@login_required
def specialPeriodAdd(request):
    form = SpecialPeriodForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('specialPeriodAdd')
    context = {'form': form}
    return render(request, 'specialPeriodAdd.html', context)


@login_required
def specialPeriodEdit(request):
    context = {'special_periods': SpecialPeriod.objects.all().order_by('year', 'period_type')}
    return render(request, 'specialPeriodEdit.html', context)


@login_required
def specialPeriodUpdate(request, pk):
    sp = SpecialPeriod.objects.get(pk=pk)
    form = SpecialPeriodForm(request.POST or None, instance=sp)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('specialPeriodEdit')
    return render(request, 'specialPeriodUpdate.html', {'special_period': sp, 'form': form})


@login_required
def specialPeriodDelete(request, pk):
    special_period = SpecialPeriod.objects.filter(pk=pk)
    if request.method == 'POST':
        special_period.delete()
        return redirect('specialPeriodEdit')


'''
Error pages
'''

def error_404(request, exception):
    return render(request,'errors/404.html', {})

def error_500(request, *args, **argv):
    return render(request,'errors/500.html', {})
