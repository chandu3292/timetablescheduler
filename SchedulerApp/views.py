from django.http.response import HttpResponse
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import *
from .forms import *
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
    def __init__(self, year, section_number, course):
        self.year = year
        self.course = course
        self.instructor = None
        self.meeting_time = None
        self.room = None
        self.section_number = section_number

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
        self._data = data
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

        newClass = Class(year, section_number, course)

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

                # NOTE: No conflict checking - GA handles conflicts through fitness evolution
                valid_blocks.append(block)

        if not valid_blocks:
            logger.warning(f"CONTINUOUS BLOCK FAILED: {course.course_number} ({course.course_type}) Section {section_number} - No valid continuous time slots found!")
            return

        # ELECTIVE → Use ONLY pre-allocated time block (MANDATORY)
        if course.course_type == 'ELECTIVE':
            block_key = f"{course.course_number}_continuous"
            if block_key in data.elective_time_tracker:
                selected_block = data.elective_time_tracker[block_key]
            else:
                # Fallback - but this violates synchronization
                selected_block = random.choice(valid_blocks)
                data.elective_time_tracker[block_key] = selected_block
        else:
            # GENTLE EARLY-BIASED SELECTION: Soft preference for earlier blocks
            # 70% chance to use early bias, 30% pure random for genetic diversity
            if valid_blocks and random.random() < 0.7:
                slot_order = [t[0] for t in TIME_SLOTS]
                valid_blocks_sorted = sorted(valid_blocks, 
                                            key=lambda block: slot_order.index(block[0].time) if block[0].time in slot_order else 999)
                
                # Gentle weights: early blocks 2-3x more likely (not 8x)
                n = len(valid_blocks_sorted)
                if n > 1:
                    # Linear decay instead of exponential
                    weights = [1.0 + (n - i) / n for i in range(n)]
                    selected_block = random.choices(valid_blocks_sorted, weights=weights, k=1)[0]
                elif n == 1:
                    selected_block = valid_blocks_sorted[0]
                else:
                    return  # No valid blocks
            elif valid_blocks:
                # Pure random for diversity
                selected_block = random.choice(valid_blocks)
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
            newClass = Class(year, section_number, course)
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
        theory_courses = list(all_courses.filter(course_type='THEORY').order_by('-priority'))
        elective_courses = list(all_courses.filter(course_type='ELECTIVE').order_by('-priority'))
        
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
        # PHASE 3: Schedule THEORY courses (FILL REMAINING SLOTS)
        # ========================================================================
        # Theory courses fill the remaining empty slots after labs and electives
        # CRITICAL RULE: Theory subjects must be DISTRIBUTED across multiple days
        # Example: 4 hrs/week, max_continuous=2 → Schedule as 2+1+1 on different days
        
        phase3_classes_before = len(self._classes)
        for section_number in sections:
            for course in theory_courses:
                # Track hours scheduled per day for this course-section combination
                hours_per_day = {}  # {day: count}
                
                remaining_hours = course.hours_per_week
                
                # Step 1: Allocate ONE continuous block (if max_continuous_hours > 1)
                if course.max_continuous_hours > 1 and remaining_hours >= course.max_continuous_hours:
                    # Add continuous block - this uses ONE day
                    block_start_len = len(self._classes)
                    self.addContinuousCourse(self._data, course, year, section_number)
                    
                    # Track which day was used for the continuous block AND count hours actually added
                    new_classes = self._classes[block_start_len:]
                    hours_actually_scheduled = len(new_classes)
                    
                    for cls in new_classes:
                        day = cls.meeting_time.day
                        hours_per_day[day] = hours_per_day.get(day, 0) + 1
                    
                    # BUGFIX: Only decrement by hours actually scheduled, not max_continuous_hours
                    # This prevents silent failures when addContinuousCourse returns early
                    remaining_hours -= hours_actually_scheduled
                    
                    # Log if continuous block failed
                    if hours_actually_scheduled == 0:
                        logger.warning(f"CONTINUOUS BLOCK FAILED: {course.course_number} Section {section_number} - No valid continuous time slots found")
                
                # Step 2: Distribute REMAINING hours across DIFFERENT days
                # CRITICAL: Each remaining hour should go to a NEW day (avoid bunching)
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
                                
                                newClass = Class(year, section_number, course)
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
        # ELECTIVE SYNCHRONIZATION CHECK
        # ------------------------------
        # Verify electives are scheduled at same times across all sections
        elective_schedule = {}  # {course_number: {section: [(day, time), ...]}}
        
        for c in classes:
            if c.course.course_type == 'ELECTIVE':
                course_num = c.course.course_number
                section_id = c.section
                
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
    
    def build_schedule(self, data, selected_year):
        """Build a conflict-free schedule using constraint satisfaction"""
        schedule = Schedule()
        schedule._data = data
        schedule._classes = []
        schedule.course_day_tracker = {}
        
        all_courses = selected_year.courses.all()
        sections = data.get_sections()
        
        # Priority order: LABs first (hardest), then THEORY
        lab_courses = sorted([c for c in all_courses if c.course_type == 'LAB'], 
                            key=lambda x: -x.max_continuous_hours)  # Longer labs first
        theory_courses = [c for c in all_courses if c.course_type == 'THEORY']
        elective_courses = [c for c in all_courses if c.course_type == 'ELECTIVE']
        
        logger.info(f"?? Scheduling {len(lab_courses)} LABs, {len(elective_courses)} ELECTIVEs, {len(theory_courses)} THEORY courses")
        
        # === PHASE 1: Schedule LABs (need continuous blocks) ===
        for course in lab_courses:
            for section in sections:
                if not self._schedule_lab_course(schedule, data, course, selected_year, section):
                    logger.warning(f"Failed to schedule LAB {course.course_number} for section {section}")
                    return None  # Fail fast if can't schedule a lab
        
        # === PHASE 2: Schedule ELECTIVEs (same time for all sections) ===
        for course in elective_courses:
            if not self._schedule_elective_course(schedule, data, course, selected_year, sections):
                logger.warning(f"Failed to schedule ELECTIVE {course.course_number}")
                return None
        
        # === PHASE 3: Schedule THEORY courses ===
        for course in theory_courses:
            for section in sections:
                if not self._schedule_theory_course(schedule, data, course, selected_year, section):
                    logger.warning(f"Failed to schedule THEORY {course.course_number} for section {section}")
                    return None
        
        logger.info(f"✓ Successfully scheduled {len(schedule._classes)} classes")
        return schedule
    
    def _schedule_lab_course(self, schedule, data, course, year, section):
        """Schedule a LAB course (needs continuous time blocks)"""
        hours_needed = course.max_continuous_hours
        hours_per_week = course.hours_per_week  # Total hours per week
        classes_needed = hours_per_week // hours_needed
        
        logger.info(f"  Scheduling {course.course_number} (Sec {section}): {classes_needed} blocks of {hours_needed}hr each")
        
        available_blocks = self._find_continuous_blocks(data, hours_needed)
        logger.info(f"    Found {len(available_blocks)} continuous {hours_needed}-hour blocks total")
        
        # Filter blocks that don't conflict
        valid_blocks = []
        for block in available_blocks:
            if self._can_schedule_block(schedule, section, course, block):
                valid_blocks.append(block)
        
        logger.info(f"    After conflict checking: {len(valid_blocks)} valid blocks available")
        
        if len(valid_blocks) < classes_needed:
            logger.error(f"    ERROR: Need {classes_needed} blocks but only {len(valid_blocks)} available!")
            return False  # Can't fit all required LAB sessions
        
        # Schedule the required number of LAB sessions
        for i in range(classes_needed):
            block = valid_blocks[i]
            instructors = self._get_instructors(course, year, section)
            lab_room = self._get_lab_room(course)
            
            # Create class for each hour in the continuous block
            for mt in block:
                new_class = Class(year, section, course)
                new_class.set_meetingTime(mt)
                new_class.set_instructor(random.choice(instructors) if instructors else None)
                new_class.set_room(lab_room)
                schedule._classes.append(new_class)
        
        return True
    
    def _schedule_elective_course(self, schedule, data, course, year, sections):
        """Schedule ELECTIVE (same time for all sections)"""
        hours_per_week = course.hours_per_week
        meeting_times = list(data.get_meetingTimes())
        
        # Find times that work for ALL sections
        for _ in range(hours_per_week):
            best_time = None
            min_conflicts = float('inf')
            
            for mt in meeting_times:
                conflicts = 0
                for section in sections:
                    if not self._can_schedule_single(schedule, section, course, mt):
                        conflicts += 1
                
                if conflicts < min_conflicts:
                    min_conflicts = conflicts
                    best_time = mt
            
            if best_time is None or min_conflicts > 0:
                return False  # Can't find common time for all sections
            
            # Schedule for all sections at the same time
            for section in sections:
                instructors = self._get_instructors(course, year, section)
                new_class = Class(year, section, course)
                new_class.set_meetingTime(best_time)
                new_class.set_instructor(random.choice(instructors) if instructors else None)
                new_class.set_room(None)
                schedule._classes.append(new_class)
        
        return True
    
    def _schedule_theory_course(self, schedule, data, course, year, section):
        """Schedule a THEORY course (find any available slots)"""
        hours_per_week = course.hours_per_week
        meeting_times = list(data.get_meetingTimes())
        
        scheduled_count = 0
        attempts = 0
        max_attempts = len(meeting_times) * 3
        
        while scheduled_count < hours_per_week and attempts < max_attempts:
            attempts += 1
            
            # Find available time slot
            for mt in sorted(meeting_times, key=lambda x: random.random()):  # Randomize to spread
                if self._can_schedule_single(schedule, section, course, mt):
                    instructors = self._get_instructors(course, year, section)
                    new_class = Class(year, section, course)
                    new_class.set_meetingTime(mt)
                    new_class.set_instructor(random.choice(instructors) if instructors else None)
                    new_class.set_room(None)
                    schedule._classes.append(new_class)
                    scheduled_count += 1
                    break
        
        return scheduled_count == hours_per_week
    
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
    
    def _can_schedule_block(self, schedule, section, course, block):
        """Check if a continuous block can be scheduled without conflicts"""
        for mt in block:
            if not self._can_schedule_single(schedule, section, course, mt):
                return False
        return True
    
    def _can_schedule_single(self, schedule, section, course, meeting_time):
        """Check if a single class can be scheduled"""
        # Check section conflicts
        for cls in schedule._classes:
            if cls.section_number == section and cls.meeting_time.pid == meeting_time.pid:
                return False
        
        # Check instructor conflicts
        instructors = self._get_instructors(course, None, section)
        if instructors:
            inst = instructors[0]  # Check first instructor
            for cls in schedule._classes:
                if cls.instructor == inst and cls.meeting_time.pid == meeting_time.pid:
                    return False
        
        # Check room conflicts (for labs)
        if course.course_type == 'LAB':
            room = self._get_lab_room(course)
            if room:
                for cls in schedule._classes:
                    if cls.room == room and cls.meeting_time.pid == meeting_time.pid:
                        return False
        
        return True
    
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
    logger.info("TIMETABLE GENERATION - 3-PHASE ALGORITHM (LAB > ELECTIVE > THEORY)")
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
        
        # CRITICAL: Deduplicate entries for multi-instructor labs
        # Key: (section, course, day, time) → entry
        seen = {}
        unique_entries = []
        for entry in entries:
            key = (entry.section_number, entry.course_id, entry.meeting_time.day, entry.meeting_time.time)
            if key not in seen:
                seen[key] = entry
                unique_entries.append(entry)
        
        # Convert to class objects for template compatibility
        classes = []
        for entry in unique_entries:
            cls = Class(entry.year, entry.section_number, entry.course)
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
            
            # Pre-allocate single period times ONLY if needed (as a LIST for multiple calls)
            if single_hours > 0:
                single_key = f"{course.course_number}_single"
                # Allocate MULTIPLE times for multiple addCourse() calls
                # All sections will use these SAME times in the SAME order
                selected_times = random.sample(meeting_times, min(single_hours, len(meeting_times)))
                data.elective_time_tracker[single_key] = selected_times  # Store as LIST
                logger.info(f"  {course.course_number} single ({single_hours} periods): {[(t.day, t.time) for t in selected_times]}")
                
                # Also create index tracker for each section
                index_key = f"{course.course_number}_single_index"
                data.elective_time_tracker[index_key] = {}
            
            # Pre-allocate continuous block time if needed
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

    # Log courses ONCE before scheduling
    all_courses = selected_year.courses.all()
    lab_courses = list(all_courses.filter(course_type='LAB').order_by('-priority'))
    elective_courses = list(all_courses.filter(course_type='ELECTIVE').order_by('-priority'))
    theory_courses = list(all_courses.filter(course_type='THEORY').order_by('-priority'))
    logger.info("=== COURSES TO BE SCHEDULED ===")
    logger.info(f"LAB ({len(lab_courses)}): {[c.course_number for c in lab_courses]}")
    logger.info(f"ELECTIVE ({len(elective_courses)}): {[c.course_number for c in elective_courses]}")
    logger.info(f"THEORY ({len(theory_courses)}): {[c.course_number for c in theory_courses]}")

    # === NEW: CONSTRAINT-BASED SCHEDULING (NO MORE GA!) ===
    logger.info(">>> Starting CONSTRAINT-BASED scheduling (guaranteed conflict-free!)")
    scheduler = ConstraintScheduler()
    schedule = None
    
    # Try up to MAX_ATTEMPTS times
    for attempt in range(1, MAX_ATTEMPTS + 1):
        logger.info(f"Attempt {attempt}/{MAX_ATTEMPTS}...")
        schedule = scheduler.build_schedule(data, selected_year)
        
        if schedule:
            logger.info(f"✓ SUCCESS on attempt {attempt}! Schedule created with {len(schedule.getClasses())} classes")
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
        # For LAB courses with multiple instructors, create entry for EACH instructor
        if cls.course.course_type == 'LAB':
            # Get all assigned instructors for this section
            assignment = CourseInstructorAssignment.objects.filter(
                year=selected_year,
                section_number=cls.section_number,
                course=cls.course
            ).first()
            
            if assignment and assignment.instructors.exists():
                # Create separate entry for each instructor (so all see it in their timetable)
                for instructor in assignment.instructors.all():
                    # Use get_or_create to prevent duplicates
                    TimetableEntry.objects.get_or_create(
                        timetable=timetable_obj,
                        year=selected_year,
                        section_number=cls.section_number,
                        course=cls.course,
                        instructor=instructor,  # Each instructor gets their own entry
                        lab_room=cls.room,
                        meeting_time=cls.meeting_time
                    )
            else:
                # Fallback: single entry with assigned instructor
                TimetableEntry.objects.get_or_create(
                    timetable=timetable_obj,
                    year=selected_year,
                    section_number=cls.section_number,
                    course=cls.course,
                    instructor=cls.instructor,
                    lab_room=cls.room,
                    meeting_time=cls.meeting_time
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
                meeting_time=cls.meeting_time
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
            import random
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
def labRoomDelete(request, pk):
    lab = LabRoom.objects.filter(pk=pk)
    if request.method == 'POST':
        lab.delete()
        return redirect('labRoomEdit')



@login_required
def meetingTimeAdd(request):
    form = MeetingTimeForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            meeting_time = form.save(commit=False)
            # Auto-generate PID
            existing_pids = MeetingTime.objects.all().order_by('-pid')
            if existing_pids.exists():
                last_pid = existing_pids.first().pid
                try:
                    new_pid_num = int(last_pid) + 1
                    meeting_time.pid = str(new_pid_num)
                except:
                    # If last PID is not numeric, count all and add 1
                    meeting_time.pid = str(MeetingTime.objects.count() + 1)
            else:
                meeting_time.pid = "1"
            meeting_time.save()
            return redirect('meetingTimeAdd')
        else:
            logger.warning("Invalid MeetingTime form submission by user %s", request.user.username)
    context = {'form': form}
    return render(request, 'meetingTimeAdd.html', context)


@login_required
def meetingTimeEdit(request):
    context = {'meeting_times': MeetingTime.objects.all()}
    return render(request, 'meetingTimeEdit.html', context)


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


'''
Error pages
'''

def error_404(request, exception):
    return render(request,'errors/404.html', {})

def error_500(request, *args, **argv):
    return render(request,'errors/500.html', {})
