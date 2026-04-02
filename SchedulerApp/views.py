from django.http.response import HttpResponse
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import *
from .forms import *
from .models import TIME_SLOTS, DAYS_OF_WEEK
from collections import defaultdict
import random
import logging

logger = logging.getLogger(__name__)

# CONSTRAINT-BASED SCHEDULING PARAMETERS (NO MORE GA!)
MAX_ATTEMPTS = 30  # Try more times to find a fully feasible schedule


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
    def __init__(self, year, section_number, course, is_evaluator=False):
        self.year = year
        self.course = course
        self.instructor = None
        self.meeting_time = None
        self.room = None
        self.section_number = section_number
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

    def validate_continuous_theory_strict(self):
        """
        â­ STRICT VALIDATION for TP courses and other continuous theory courses
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
                logger.warning(f"â­ STRICT REJECT: {course.course_number} Sec {section} split across {len(days)} days")
                return False
            
            # REJECT: Not enough hours
            if len(days) == 0:
                logger.warning(f"â­ STRICT REJECT: {course.course_number} Sec {section} has no hours scheduled")
                return False
            
            day = list(days.keys())[0]
            times = days[day]
            
            if len(times) < required:
                logger.warning(f"â­ STRICT REJECT: {course.course_number} Sec {section} has only {len(times)}/{required} hours")
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
                logger.warning(f"â­ STRICT REJECT: {course.course_number} Sec {section} NOT continuous: {times}")
                return False
        
        # All checks passed
        return True

    def validate_full_course_allocation(self):
        """
        Ensure every course gets all required weekly hours in every section.
        Counts unique section-course-day-time slots to avoid duplicate instructor entries.
        """
        year = self._data.get_year()
        if not year:
            return True

        delivered_slots = set()
        for c in self.getClasses():
            delivered_slots.add((c.section_number, c.course.course_number, c.meeting_time.day, c.meeting_time.time))

        delivered = {}
        for section, course_num, day, time in delivered_slots:
            key = (section, course_num)
            delivered[key] = delivered.get(key, 0) + 1

        for course in year.courses.all():
            for section in self._data.get_sections():
                key = (section, course.course_number)
                got = delivered.get(key, 0)
                need = course.hours_per_week
                if got < need:
                    logger.warning(
                        f"HOUR ALLOCATION REJECT: {course.course_number} Sec{section} has {got}/{need} hours"
                    )
                    return False

        return True

    def get_allocation_report(self):
        """
        Generate a detailed allocation report for diagnostics.
        Returns: {
            'total_hours_delivered': int,
            'total_hours_needed': int,
            'complete_courses': list of (section, course_number),
            'incomplete_courses': list of {section, course_num, got, need}
        }
        """
        year = self._data.get_year()
        if not year:
            return None

        delivered_slots = set()
        for c in self.getClasses():
            delivered_slots.add((c.section_number, c.course.course_number, c.meeting_time.day, c.meeting_time.time))

        delivered = {}
        for section, course_num, day, time in delivered_slots:
            key = (section, course_num)
            delivered[key] = delivered.get(key, 0) + 1

        complete = []
        incomplete = []
        total_delivered = 0
        total_needed = 0

        for course in year.courses.all():
            for section in self._data.get_sections():
                key = (section, course.course_number)
                got = delivered.get(key, 0)
                need = course.hours_per_week
                total_delivered += got
                total_needed += need

                if got >= need:
                    complete.append((section, course.course_number))
                else:
                    incomplete.append({
                        'section': section,
                        'course': course.course_number,
                        'got': got,
                        'need': need,
                        'missing': need - got
                    })

        return {
            'total_delivered': total_delivered,
            'total_needed': total_needed,
            'complete': len(complete),
            'incomplete_count': len(incomplete),
            'incomplete_list': incomplete
        }

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
        # â­ STRICT CONSTRAINT: THEORY courses where hours_per_week == max_continuous_hours > 1
        # MUST have ALL hours as a continuous block on one day (e.g., TP courses with 2 continuous hours)
        # This is NON-NEGOTIABLE - violations get MASSIVE penalty (10000) to force rejection
        theory_by_section_course = {}  # {(section, course): [(day, time), ...]}

        for c in classes:
            if c.course.course_type != 'THEORY':
                continue
            
            # Only check courses that need continuous scheduling
            if c.course.max_continuous_hours <= 1:
                continue
            
            # â­ STRICT: Only check courses where ALL weekly hours should be continuous
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
            
            # â­ STRICT VIOLATION: Hours split across multiple days - UNACCEPTABLE
            if len(days) > 1:
                self._numberOfConflicts += 10000  # MASSIVE penalty - forces rejection
                logger.error(f"STRICT VIOLATION: {course.course_number} Section {section} split across {len(days)} days (Must be on ONE day)")
                continue
            
            # Check if the hours on the single day are continuous
            if len(days) == 1:
                day = list(days.keys())[0]
                times = days[day]
                
                # â­ STRICT VIOLATION: Missing hours
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

                # â­ STRICT VIOLATION: Hours NOT continuous (e.g., 9:45-10:35 and 1:05-1:55)
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

    def _get_teaching_period_number(self, time_value, year=None):
        """Map timetable slot to teaching period number (1-7), excluding lunch."""
        lunch_period = year.lunch_period if year and hasattr(year, 'lunch_period') else 5
        teaching_period = 0

        for slot_idx, slot in enumerate(TIME_SLOTS, start=1):
            if slot_idx == lunch_period:
                continue
            teaching_period += 1
            if slot[0] == time_value:
                return teaching_period

        return None

    def _get_instructor_priority_lookup(self, instructor):
        """Load and cache {day: {period: priority}} for an instructor."""
        from .models import InstructorPriority

        if not hasattr(self, '_instructor_priority_cache'):
            self._instructor_priority_cache = {}

        cache_key = instructor.id if instructor else None
        if cache_key in self._instructor_priority_cache:
            return self._instructor_priority_cache[cache_key]

        priority_lookup = {}
        if instructor:
            priorities = InstructorPriority.objects.filter(instructor=instructor)
            for obj in priorities:
                day_priorities = {}
                for period in range(1, 8):
                    day_priorities[period] = obj.get_period_priority(period)
                priority_lookup[obj.day] = day_priorities

        self._instructor_priority_cache[cache_key] = priority_lookup
        return priority_lookup

    def _sort_meeting_times_by_instructor_priority(self, meeting_times, instructor=None, year=None):
        """Sort slots by instructor priority first, then by day/time."""
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        time_order = [t[0] for t in TIME_SLOTS]

        if not instructor:
            return sorted(meeting_times, key=lambda mt: (
                day_order.index(mt.day) if mt.day in day_order else 999,
                time_order.index(mt.time) if mt.time in time_order else 999
            ))

        priority_lookup = self._get_instructor_priority_lookup(instructor)

        def sort_key(mt):
            period = self._get_teaching_period_number(mt.time, year)
            day_priorities = priority_lookup.get(mt.day, {})
            priority = day_priorities.get(period, 999) if period else 999
            return (
                priority,
                day_order.index(mt.day) if mt.day in day_order else 999,
                time_order.index(mt.time) if mt.time in time_order else 999
            )

        return sorted(meeting_times, key=sort_key)
    
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

        # Helper: Identify courses needing alignment (same time for all sections)
        def needs_section_alignment(course):
            if course.course_type == 'LAB':
                return False
            
            # EXCLUDE TP courses from forced alignment (they need strict 2-hour continuity)
            if 'TP' in course.course_number:
                return False
            
            # CHECK: If same instructor teaches multiple sections, DON'T force alignment
            try:
                from SchedulerApp.models import CourseInstructorAssignment
                assignments = CourseInstructorAssignment.objects.filter(course=course)
                if assignments.exists():
                    instructors_per_section = {}
                    for a in assignments:
                        inst_ids = set(a.instructors.values_list('id', flat=True))
                        if a.section_number not in instructors_per_section:
                            instructors_per_section[a.section_number] = inst_ids
                        else:
                            instructors_per_section[a.section_number].update(inst_ids)
                    
                    all_instructors = set()
                    for section_insts in instructors_per_section.values():
                        intersection = all_instructors & section_insts
                        if intersection:
                            return False
                        all_instructors.update(section_insts)
            except:
                pass
            
            if course.course_type == 'ELECTIVE':
                return True
            if course.course_number.startswith('23IT6') or course.course_number.startswith('23IT7'):
                return True
            if course.course_number.startswith('23IT5') and course.course_type != 'LAB':
                return True
            return False

        # Priority order
        lab_courses = sorted([c for c in all_courses if c.course_type == 'LAB'], key=lambda x: -x.max_continuous_hours)
        elective_courses = [c for c in all_courses if needs_section_alignment(c)]
        all_theory = [c for c in all_courses.filter(course_type='THEORY') if c not in elective_courses]
        continuous_theory_courses = [c for c in all_theory if c.max_continuous_hours > 1]
        regular_theory_courses = [c for c in all_theory if c.max_continuous_hours == 1]

        # Constrained-first ordering improves feasibility and full hour allocation.
        def min_instructor_options(course):
            counts = []
            for section in sections:
                assigned = CourseInstructorAssignment.objects.filter(
                    year=selected_year,
                    section_number=section,
                    course=course
                ).first()
                if assigned:
                    cnt = assigned.instructors.count()
                else:
                    cnt = course.instructors.count()
                counts.append(cnt if cnt > 0 else 999)
            return min(counts) if counts else 999

        continuous_theory_courses = sorted(
            continuous_theory_courses,
            key=lambda c: (min_instructor_options(c), -c.max_continuous_hours, -c.hours_per_week)
        )
        regular_theory_courses = sorted(
            regular_theory_courses,
            key=lambda c: (min_instructor_options(c), -c.hours_per_week)
        )

        logger.info(f"ðŸ”· Scheduling Order: {len(lab_courses)} LABs â†’ {len(elective_courses)} ELECTIVEs â†’ {len(continuous_theory_courses)} TP courses â†’ {len(regular_theory_courses)} regular THEORY")

        # PHASE 1: LABS
        for course in lab_courses:
            logger.info(f"  ====> Processing LAB course: {course.course_number}")
            for section in sections:
                logger.info(f"    ====> Section {section}")
                if not self._schedule_lab_course(schedule, data, course, selected_year, section):
                    logger.warning(f"Failed to schedule LAB {course.course_number} for section {section}")

        # PHASE 2: ELECTIVES (aligned)
        unscheduled_electives = []
        for course in elective_courses:
            if not self._schedule_elective_course(schedule, data, course, selected_year, sections):
                logger.warning(f"âš  ELECTIVE {course.course_number} failed parallel scheduling - will retry separately")
                unscheduled_electives.append(course)

        # PHASE 3: CONTINUOUS THEORY (TP)
        for course in continuous_theory_courses:
            logger.info(f"  ====> Processing TP course: {course.course_number}")
            for section in sections:
                if not self._schedule_theory_course(schedule, data, course, selected_year, section):
                    logger.warning(f"Failed to schedule TP {course.course_number} for section {section}")

        # PHASE 4: REGULAR THEORY
        unscheduled_theory = []
        for course in regular_theory_courses:
            for section in sections:
                if not self._schedule_theory_course(schedule, data, course, selected_year, section):
                    logger.warning(f"âš  REGULAR THEORY {course.course_number} Sec{section} failed - will retry in gap-filling")
                    unscheduled_theory.append((course, section))

        # PHASE 4.5: RETRY FAILED ELECTIVES
        if unscheduled_electives:
            logger.info(f"ðŸ”§ GAP-FILLING: Attempting to schedule {len(unscheduled_electives)} failed electives WITH ALIGNMENT")
            for course in unscheduled_electives:
                if not self._schedule_elective_course_dynamic(schedule, data, course, selected_year, sections):
                    logger.error(f"âŒ CRITICAL: ELECTIVE {course.course_number} could not be scheduled even with dynamic search!")
                    logger.error("   This elective will have incomplete hours - manual adjustment needed")
                else:
                    logger.info(f"âœ“ Gap-filled ELECTIVE {course.course_number} with alignment maintained")

        # PHASE 4.6: RETRY FAILED THEORY
        if unscheduled_theory:
            logger.info(f"ðŸ”§ GAP-FILLING: Attempting to schedule {len(unscheduled_theory)} failed theory courses")
            for course, section in unscheduled_theory:
                if not self._schedule_theory_course_relaxed(schedule, data, course, selected_year, section):
                    logger.error(f"âŒ CRITICAL: THEORY {course.course_number} Sec{section} could not be scheduled even with relaxed constraints!")
                else:
                    logger.info(f"âœ“ Gap-filled THEORY {course.course_number} Sec{section}")

        # PHASE 4.9: FINAL GAP FILL
        logger.info("ðŸ”§ FINAL GAP CHECK: Verifying all courses are fully scheduled")
        final_gaps_found = False

        for course in all_courses:
            if needs_section_alignment(course):
                for section in sections:
                    scheduled_count = sum(
                        1 for cls in schedule._classes
                        if cls.section_number == section
                        and cls.course == course
                        and cls.course.course_number not in ['COUNSELING', 'SPORTS_LIBRARY', 'SPORT', 'COUNS']
                    )
                    needed = course.hours_per_week
                    if scheduled_count < needed:
                        missing = needed - scheduled_count
                        logger.error(f"âš ï¸ ELECTIVE GAP (cannot force-fill): {course.course_number} Sec{section} missing {missing}/{needed} hours")
                        logger.error("   Electives require alignment - manual adjustment or regeneration needed")
                continue

            for section in sections:
                scheduled_count = sum(
                    1 for cls in schedule._classes
                    if cls.section_number == section
                    and cls.course == course
                    and cls.course.course_number not in ['COUNSELING', 'SPORTS_LIBRARY', 'SPORT', 'COUNS']
                )
                needed = course.hours_per_week

                if scheduled_count < needed:
                    missing = needed - scheduled_count
                    logger.warning(f"âš  FINAL GAP: {course.course_number} Sec{section} missing {missing}/{needed} hours")
                    final_gaps_found = True

                    for _ in range(missing):
                        if not self._force_schedule_single_hour(schedule, data, course, selected_year, section):
                            logger.error(f"âŒ CRITICAL: Could not force-schedule {course.course_number} Sec{section}")
                            break

                    new_count = sum(
                        1 for cls in schedule._classes
                        if cls.section_number == section
                        and cls.course == course
                        and cls.course.course_number not in ['COUNSELING', 'SPORTS_LIBRARY', 'SPORT', 'COUNS']
                    )
                    if new_count == needed:
                        logger.info(f"âœ“ Force-filled {course.course_number} Sec{section}: {new_count}/{needed}")

        if not final_gaps_found:
            logger.info("âœ“ All courses fully scheduled - no gaps remaining")

        # PHASE 5: Special periods
        logger.info("ðŸ“… Starting special periods scheduling...")
        if not self._schedule_special_periods(schedule, data, selected_year, sections):
            logger.warning("Failed to schedule some special periods (continuing anyway)")

        # Validation check: TP continuity (warn if violated, but don't reject)
        # For 3rd year and other constrained years, full constraint satisfaction may be infeasible
        tp_continuous = schedule.validate_continuous_theory_strict()
        full_hours = schedule.validate_full_course_allocation()

        if not tp_continuous:
            logger.warning("âš ï¸ TP continuity constraint violated (some TP courses split across days)")
        if not full_hours:
            logger.warning("âš ï¸ Some courses lack full weekly hour allocation (partial schedule)")

        logger.info(f"âœ… Successfully scheduled {len(schedule._classes)} classes")
        return schedule
    
    def _schedule_lab_course(self, schedule, data, course, year, section):
        """Schedule a LAB course (needs continuous time blocks)"""
        
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
        
        available_blocks = self._find_continuous_blocks(data, hours_needed, main_instructor, year)
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
                new_class = Class(year, section, course, is_evaluator=False)
                new_class.set_meetingTime(mt)
                new_class.set_instructor(main_instructor)
                new_class.set_room(lab_room)
                schedule._classes.append(new_class)
            
            # Create entries for EVALUATORS (if any)
            for evaluator in evaluators:
                for mt in block:
                    new_class = Class(year, section, course, is_evaluator=True)
                    new_class.set_meetingTime(mt)
                    new_class.set_instructor(evaluator)
                    new_class.set_room(lab_room)
                    schedule._classes.append(new_class)
        
        return True
    
    
    def _schedule_elective_course(self, schedule, data, course, year, sections):
        """
        Schedule ELECTIVE using PRE-ALLOCATED times (same time for all sections).
        Uses the elective_time_tracker to ensure all sections have electives at the same time.
        """
        hours_per_week = course.hours_per_week
        max_continuous = course.max_continuous_hours if course.max_continuous_hours > 0 else hours_per_week
        
        logger.info(f"  Scheduling ELECTIVE {course.course_number}: {hours_per_week}hrs using pre-allocated times")
        
        # Get pre-allocated times from elective_time_tracker
        continuous_hours = max_continuous if max_continuous > 1 else 0
        single_hours = hours_per_week - continuous_hours
        
        times_to_use = []
        
        # FIRST: Get continuous block if exists
        if continuous_hours > 0:
            block_key = f"{course.course_number}_continuous"
            if block_key in data.elective_time_tracker:
                continuous_block = data.elective_time_tracker[block_key]
                times_to_use.extend(continuous_block)
                logger.info(f"    Using pre-allocated continuous block: {continuous_block[0].day} {[mt.time for mt in continuous_block]}")
        
        # SECOND: Get single period times if exists
        if single_hours > 0:
            single_key = f"{course.course_number}_single"
            if single_key in data.elective_time_tracker:
                single_times = data.elective_time_tracker[single_key]
                times_to_use.extend(single_times)
                logger.info(f"    Using pre-allocated single times: {[(mt.day, mt.time) for mt in single_times]}")
        
        # Verify we have enough pre-allocated times
        if len(times_to_use) < hours_per_week:
            logger.warning(f"    âŒ Not enough pre-allocated times! Need {hours_per_week}, got {len(times_to_use)}")
            logger.warning(f"    Falling back to dynamic scheduling...")
            return self._schedule_elective_course_dynamic(schedule, data, course, year, sections)
        
        # Schedule ALL sections at the SAME times
        # CRITICAL: Only schedule if ALL sections can use the same time (maintain alignment)
        scheduled_hours = 0
        for mt in times_to_use:
            # FIRST: Check if this time works for ALL sections
            can_schedule_all = True
            for section in sections:
                if not self._can_schedule_single(schedule, section, course, mt, year=year):
                    can_schedule_all = False
                    logger.warning(f"    âš ï¸ Cannot use {mt.day} {mt.time} - conflict in Section {section}")
                    break
            
            # SECOND: Only schedule if ALL sections are conflict-free
            if can_schedule_all:
                for section in sections:
                    instructors = self._get_instructors(course, year, section)
                    instructor = instructors[0] if instructors else None
                    
                    new_class = Class(year, section, course)
                    new_class.set_meetingTime(mt)
                    new_class.set_instructor(instructor)
                    new_class.set_room(None)
                    schedule._classes.append(new_class)
                
                scheduled_hours += 1
                logger.debug(f"    âœ“ Scheduled hour {scheduled_hours}/{hours_per_week} for ALL sections at {mt.day} {mt.time}")
            else:
                logger.warning(f"    â­ï¸  Skipping {mt.day} {mt.time} - cannot schedule ALL sections (alignment required)")
        
        success = (scheduled_hours == hours_per_week)
        if success:
            logger.info(f"    âœ… ELECTIVE {course.course_number}: Successfully scheduled all {scheduled_hours} hours at SAME times for all sections")
        else:
            logger.warning(f"    âš ï¸ ELECTIVE {course.course_number}: Only scheduled {scheduled_hours}/{hours_per_week} hours")
        
        return success
    
    def _schedule_elective_course_dynamic(self, schedule, data, course, year, sections):
        """
        FALLBACK: Schedule ELECTIVE dynamically when pre-allocation fails.
        Tries to find times that work for ALL sections.
        """
        hours_per_week = course.hours_per_week
        max_continuous = course.max_continuous_hours if course.max_continuous_hours > 0 else hours_per_week
        meeting_times = list(data.get_meetingTimes())
        
        logger.info(f"    Dynamic scheduling ELECTIVE {course.course_number}: {hours_per_week}hrs")
        
        # Track hours per day AND time slot usage for spreading
        from collections import defaultdict
        day_hours = defaultdict(int)
        time_slot_usage = defaultdict(int)
        
        scheduled_hours = 0
        max_attempts = hours_per_week * len(meeting_times)  # Generous attempt limit
        attempts = 0
        
        # Find times that work for ALL sections
        while scheduled_hours < hours_per_week and attempts < max_attempts:
            attempts += 1
            best_time = None
            
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
                can_schedule_all = True
                
                # Check each section
                for section in sections:
                    if not self._can_schedule_single(schedule, section, course, mt, year=year):
                        can_schedule_all = False
                        break
                    
                    # Check if scheduling here would exceed max_continuous consecutive periods
                    consecutive_before = self._count_consecutive_before(schedule, section, course, mt)
                    consecutive_after = self._count_consecutive_after(schedule, section, course, mt)
                    total_consecutive = consecutive_before + consecutive_after + 1
                    
                    if total_consecutive > max_continuous:
                        can_schedule_all = False
                        break

                if can_schedule_all:
                    best_time = mt
                    break
            
            if best_time is None:
                logger.warning(f"  ELECTIVE {course.course_number}: No valid time slot found after {attempts} attempts")
                break  # No more valid slots available

            # Schedule for all sections at the same time (strict alignment)
            for section in sections:
                instructors = self._get_instructors(course, year, section)
                instructor = instructors[0] if instructors else None
                
                new_class = Class(year, section, course)
                new_class.set_meetingTime(best_time)
                new_class.set_instructor(instructor)
                new_class.set_room(None)
                schedule._classes.append(new_class)

            day_hours[best_time.day] += 1
            time_slot_usage[best_time.time] += 1
            scheduled_hours += 1
            logger.debug(f"  ELECTIVE {course.course_number}: Scheduled hour {scheduled_hours}/{hours_per_week} for ALL sections at {best_time.day} {best_time.time}")
        
        if scheduled_hours == hours_per_week:
            logger.info(f"  âœ“ ELECTIVE {course.course_number}: Successfully scheduled all {scheduled_hours} hours")
            return True
        else:
            logger.warning(f"  âš  ELECTIVE {course.course_number}: Only scheduled {scheduled_hours}/{hours_per_week} hours (will retry separately)")
            return False  # Trigger separate section scheduling
    
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
        
        # â­ CRITICAL FIX FOR TP COURSES:
        # If hours_per_week == max_continuous_hours > 1, ALL hours MUST be continuous
        # Example: TP courses with 2hrs/week and max_continuous=2
        # These MUST be scheduled as ONE 2-hour block, NOT as separate 1-hour periods
        if hours_per_week == max_continuous and max_continuous > 1:
            logger.info(f"    {course.course_number} Sec{section}: Scheduling as {max_continuous}-hour continuous block (TP course)")
            
            # Find continuous blocks
            available_blocks = self._find_continuous_blocks(data, max_continuous, instructor, year)
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
                    new_class = Class(year, section, course)
                    new_class.set_meetingTime(mt)
                    new_class.set_instructor(instructor)
                    new_class.set_room(None)  # Theory courses don't use lab rooms
                    schedule._classes.append(new_class)
                
                return True
            else:
                # FALLBACK: No continuous blocks available, try to schedule as separate periods
                # This is not ideal but allows the schedule to be created
                # The fitness function will penalize this heavily, but won't fail completely
                logger.warning(f"      âš  No continuous blocks available for {course.course_number} Sec{section}")
                logger.warning(f"      â†’ Falling back to separate period scheduling (will be penalized in fitness)")
                # Continue to regular scheduling below instead of returning False
        
        # â­ REGULAR THEORY SCHEDULING (for courses that can be spread across days)
        # SPREAD-ACROSS-DAYS STRATEGY WITH INSTRUCTOR PRIORITIES
        # Limit max hours per day and prioritize spreading across multiple days
        scheduled_count = 0
        attempts = 0
        max_attempts = len(meeting_times) * 10
        
        # Track hours scheduled per day
        from collections import defaultdict
        day_hours = defaultdict(int)
        
        logger.info(f"      {course.course_number} Sec{section}: Day-filling {hours_per_week} hrs (max {max_continuous} hrs/day) with instructor priorities")
        
        # Group meeting times by day
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        time_order = [t[0] for t in TIME_SLOTS]
        
        # Create a mapping of day -> sorted meeting times for that day
        days_dict = defaultdict(list)
        for mt in meeting_times:
            days_dict[mt.day].append(mt)
        
        # Sort meeting times within each day by INSTRUCTOR PRIORITY
        for day in days_dict:
            days_dict[day] = self._sort_meeting_times_by_instructor_priority(days_dict[day], instructor, year)
            logger.debug(f"        {day}: Sorted by instructor priority")
        
        logger.info(f"      {course.course_number} Sec{section}: Starting DAY-FILLING (max {max_continuous} hrs/day per course) with instructor priorities")
        
        # â­ DAY-FILLING STRATEGY: Process days sequentially, fill each up to max_continuous_hours
        # Within each day, times are sorted by instructor priority (1=highest preference)
        # This ensures courses are distributed across multiple days instead of clustering on one day
        for day in day_order:
            if scheduled_count >= hours_per_week:
                break  # All hours scheduled
            
            if day not in days_dict:
                continue  # No meeting times for this day
            
            logger.debug(f"        Attempting to fill {day}...")
            
            # Try to schedule as many hours as possible on this day (up to max_continuous limit)
            for mt in days_dict[day]:
                if scheduled_count >= hours_per_week:
                    break  # All hours scheduled
                
                # â­â­ CRITICAL: Check day limit FIRST (cannot exceed max_continuous_hours on any day)
                if day_hours[day] >= max_continuous:
                    logger.debug(f"          Day limit reached: {day} already has {day_hours[day]} hours (max={max_continuous})")
                    break  # Move to next day
                
                # Check if we can schedule here (instructor free, no conflicts)
                if not self._can_schedule_single(schedule, section, course, mt, instructor, year):
                    continue
                
                # Count consecutive hours
                consecutive_before = self._count_consecutive_before(schedule, section, course, mt)
                consecutive_after = self._count_consecutive_after(schedule, section, course, mt)
                total_consecutive = consecutive_before + consecutive_after + 1
                
                # Skip if adding this would exceed max_continuous_hours in consecutive slots
                if total_consecutive > max_continuous:
                    logger.debug(f"          {mt.time}: Skipped (would exceed consecutive max={max_continuous})")
                    continue
                
                # â­ Schedule it
                new_class = Class(year, section, course)
                new_class.set_meetingTime(mt)
                new_class.set_instructor(instructor)
                new_class.set_room(None)
                schedule._classes.append(new_class)
                scheduled_count += 1
                day_hours[day] += 1
                logger.debug(f"          {mt.time}: Scheduled ({scheduled_count}/{hours_per_week} total, {day_hours[day]} on {day})")
            
            if day_hours[day] > 0:
                logger.info(f"        {day}: Scheduled {day_hours[day]} period(s)")
        
        # Check if day-filling completed all hours
        if scheduled_count < hours_per_week:
            logger.warning(f"        Day-filling completed {scheduled_count}/{hours_per_week} hours - starting gap-filling")
        else:
            logger.info(f"        Day-filling SUCCESS: All {scheduled_count} hours scheduled")
        
        # â­ GAP-FILLING PHASE: If not all hours scheduled, fill remaining gaps
        # Ignore day limits and just fill ANY available slot where instructor is free
        if scheduled_count < hours_per_week:
            logger.info(f"      ðŸ”§ GAP-FILLING PHASE 1: {hours_per_week - scheduled_count} hours remaining, filling gaps (respecting max continuous)")
            
            # Flatten all meeting times from all days
            all_meeting_times = []
            for day in day_order:
                if day in days_dict:
                    all_meeting_times.extend(days_dict[day])
            
            # PASS 1: Try to schedule remaining hours while respecting max_continuous_hours
            for mt in all_meeting_times:
                if scheduled_count >= hours_per_week:
                    break  # All hours scheduled
                
                # Check if we can schedule here (instructor free, no conflicts)
                if not self._can_schedule_single(schedule, section, course, mt, instructor, year):
                    continue
                
                # â­ NEW: Check total hours on this day (cannot exceed max_continuous_hours)
                hours_on_day = day_hours[mt.day]
                if hours_on_day >= max_continuous:
                    logger.debug(f"          {mt.day} {mt.time}: Day limit reached ({hours_on_day}/{max_continuous})")
                    continue
                
                # Count consecutive hours
                consecutive_before = self._count_consecutive_before(schedule, section, course, mt)
                consecutive_after = self._count_consecutive_after(schedule, section, course, mt)
                total_consecutive = consecutive_before + consecutive_after + 1
                
                # Skip if adding this would exceed max_continuous_hours
                if total_consecutive > max_continuous:
                    continue
                
                # â­ Schedule it (respecting both day limits and consecutive limits!)
                new_class = Class(year, section, course)
                new_class.set_meetingTime(mt)
                new_class.set_instructor(instructor)
                new_class.set_room(None)
                schedule._classes.append(new_class)
                scheduled_count += 1
                day_hours[mt.day] += 1
                logger.debug(f"          GAP-FILL Pass1: {mt.day} {mt.time} - {scheduled_count}/{hours_per_week}")
        
        # â­â­ ULTRA-RELAXED GAP-FILLING PHASE 2: Ignore consecutive constraint but RESPECT day limit
        # If STILL not fully scheduled, allow non-consecutive scheduling but respect max hours per day
        if scheduled_count < hours_per_week:
            logger.warning(f"      ðŸ”§ðŸ”§ GAP-FILLING PHASE 2 (ULTRA-RELAXED): {hours_per_week - scheduled_count} hours still missing, ignoring consecutive constraint but respecting day limit")
            
            # Flatten all meeting times again
            all_meeting_times = []
            for day in day_order:
                if day in days_dict:
                    all_meeting_times.extend(days_dict[day])
            
            # PASS 2: Schedule remaining hours WITHOUT checking consecutive hours but WITH day limit
            for mt in all_meeting_times:
                if scheduled_count >= hours_per_week:
                    break  # All hours scheduled
                
                # Check conflicts
                if not self._can_schedule_single(schedule, section, course, mt, instructor, year):
                    continue
                
                # â­â­ CRITICAL: Still respect day limit (max_continuous_hours per day)
                hours_on_day = day_hours[mt.day]
                if hours_on_day >= max_continuous:
                    logger.debug(f"          {mt.day} {mt.time}: Day limit reached ({hours_on_day}/{max_continuous})")
                    continue
                
                # â­â­ RELAX: Don't check if consecutive - just fill the gap!
                # This allows courses to be scheduled non-consecutively if needed
                
                # Schedule it!
                new_class = Class(year, section, course)
                new_class.set_meetingTime(mt)
                new_class.set_instructor(instructor)
                new_class.set_room(None)
                schedule._classes.append(new_class)
                scheduled_count += 1
                day_hours[mt.day] += 1
                logger.debug(f"          GAP-FILL Pass2 (RELAXED): {mt.day} {mt.time} - {scheduled_count}/{hours_per_week}")
        
        # Log summary
        for day in day_order:
            if day_hours[day] > 0:
                logger.info(f"        {day}: {day_hours[day]} period(s)")
        
        if scheduled_count < hours_per_week:
            logger.warning(f"    {course.course_number} Sec{section}: Only scheduled {scheduled_count}/{hours_per_week} hours (INCOMPLETE)")
        else:
            logger.info(f"    {course.course_number} Sec{section}: Successfully scheduled all {scheduled_count} hours")
        
        return scheduled_count == hours_per_week
    
    def _schedule_theory_course_relaxed(self, schedule, data, course, year, section):
        """
        RELAXED scheduling for gap-filling.
        Relaxes placement rules but still prefers instructor-priority slots.
        Use this as a fallback when strict scheduling fails.
        """
        hours_per_week = course.hours_per_week
        max_continuous = course.max_continuous_hours if course.max_continuous_hours > 0 else hours_per_week
        meeting_times = list(data.get_meetingTimes())
        
        # Get instructor
        instructors = self._get_instructors(course, year, section)
        if not instructors:
            logger.warning(f"    No instructors for {course.course_number} Sec {section}")
            return False
        instructor = instructors[0]
        
        logger.info(f"  ðŸ”§ RELAXED SCHEDULING: {course.course_number} Sec{section} - filling ANY available slots")
        
        scheduled_count = 0
        
        # Try all meeting times in priority order and spread across days.
        from collections import defaultdict
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        day_hours = defaultdict(int)
        
        # Group by day
        days_dict = defaultdict(list)
        for mt in meeting_times:
            days_dict[mt.day].append(mt)
        
        # Sort times by instructor priority within each day
        for day in days_dict:
            days_dict[day] = self._sort_meeting_times_by_instructor_priority(days_dict[day], instructor, year)
        
        # Fill across days evenly (day-filling but simpler)
        max_per_day = (hours_per_week // len(day_order)) + 1  # Spread evenly
        
        for day in day_order:
            if scheduled_count >= hours_per_week:
                break
            
            if day not in days_dict:
                continue
            
            for mt in days_dict[day]:
                if scheduled_count >= hours_per_week:
                    break
                
                # Don't overfill one day
                if day_hours[day] >= max_per_day and scheduled_count < hours_per_week - 1:
                    continue
                
                # Check if we can schedule here
                if not self._can_schedule_single(schedule, section, course, mt, instructor, year):
                    continue
                
                # Check consecutive limit
                consecutive_before = self._count_consecutive_before(schedule, section, course, mt)
                consecutive_after = self._count_consecutive_after(schedule, section, course, mt)
                total_consecutive = consecutive_before + consecutive_after + 1
                
                if total_consecutive > max_continuous:
                    continue
                
                # Schedule it!
                new_class = Class(year, section, course)
                new_class.set_meetingTime(mt)
                new_class.set_instructor(instructor)
                new_class.set_room(None)
                schedule._classes.append(new_class)
                scheduled_count += 1
                day_hours[day] += 1
                logger.debug(f"    Relaxed: {day} {mt.time} - {scheduled_count}/{hours_per_week}")
        
        if scheduled_count == hours_per_week:
            logger.info(f"  âœ“ RELAXED: Successfully scheduled all {scheduled_count} hours")
            return True
        else:
            logger.error(f"  âŒ RELAXED FAILED: Only {scheduled_count}/{hours_per_week} hours scheduled")
            return False
    
    def _force_schedule_single_hour(self, schedule, data, course, year, section):
        """
        ULTRA-AGGRESSIVE: Schedule a single hour in ANY available slot.
        Relaxes day distribution and consecutive constraint, while still preferring priorities.
        BUT STILL RESPECTS max_continuous_hours as a day limit.
        Used as absolute last resort for gap-filling.
        """
        instructors = self._get_instructors(course, year, section)
        if not instructors:
            return False
        instructor = instructors[0]
        
        meeting_times = self._sort_meeting_times_by_instructor_priority(list(data.get_meetingTimes()), instructor, year)
        max_continuous = course.max_continuous_hours
        
        # Count current hours per day for this course
        from collections import defaultdict
        day_hours = defaultdict(int)
        for cls in schedule._classes:
            if (cls.section_number == section and 
                cls.course == course):
                day_hours[cls.meeting_time.day] += 1
        
        # Try EVERY possible time slot
        for mt in meeting_times:
            # Check basic conflicts
            if not self._can_schedule_single(schedule, section, course, mt, instructor, year):
                continue
            
            # â­ CRITICAL: Respect day limit (cannot exceed max_continuous_hours per day)
            if day_hours[mt.day] >= max_continuous:
                logger.debug(f"    Force-schedule skip {mt.day} {mt.time}: Day limit reached ({day_hours[mt.day]}/{max_continuous})")
                continue
            
            # â­â­ RELAXED: Skip consecutive hours check (can be non-consecutive)
            # But we still respect the total hours per day limit
            
            # SCHEDULE IT!
            new_class = Class(year, section, course)
            new_class.set_meetingTime(mt)
            new_class.set_instructor(instructor)
            new_class.set_room(None)
            schedule._classes.append(new_class)
            logger.debug(f"    Force-scheduled (non-consecutive OK, day limit respected): {mt.day} {mt.time}")
            return True
        
        # Could not find ANY valid slot
        logger.warning(f"    Force-schedule failed: All days at max limit ({max_continuous} hrs/day)")
        return False
    
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
    
    def _find_continuous_blocks(self, data, hours_needed, instructor=None, year=None):
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

        # Prefer blocks that match instructor priorities when available.
        if instructor and blocks:
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
            time_order = [t[0] for t in TIME_SLOTS]
            priority_lookup = self._get_instructor_priority_lookup(instructor)

            def block_key(block):
                priority_values = []
                for mt in block:
                    period = self._get_teaching_period_number(mt.time, year)
                    day_priorities = priority_lookup.get(mt.day, {})
                    priority_values.append(day_priorities.get(period, 999) if period else 999)

                avg_priority = sum(priority_values) / len(priority_values) if priority_values else 999
                return (
                    avg_priority,
                    day_order.index(block[0].day) if block[0].day in day_order else 999,
                    time_order.index(block[0].time) if block[0].time in time_order else 999
                )

            blocks.sort(key=block_key)
        
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
        """Schedule special periods (Counseling, Training, Sports, Library) - applies to all sections"""
        from .models import SpecialPeriod
        
        # Get all special periods configured for this year
        special_periods = SpecialPeriod.objects.filter(year=year)
        
        if not special_periods.exists():
            logger.info("  No special periods configured for this year")
            return True
        
        logger.info(f"  Found {special_periods.count()} special period type(s) to schedule for all {len(sections)} sections")
        
        # Create pseudo-courses for special periods if they don't exist
        special_courses = {}
        for period_type in ['Counseling', 'Training', 'Sports', 'Library']:
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
        available_blocks = self._find_continuous_blocks(data, hours_needed, instructor, year)
        
        # Filter blocks that don't conflict
        for block in available_blocks:
            if self._can_schedule_block(schedule, section, course, block, instructor, year, None):
                # Schedule the block
                for mt in block:
                    new_class = Class(year, section, course)
                    new_class.set_meetingTime(mt)
                    new_class.set_instructor(instructor)
                    new_class.set_room(None)
                    schedule._classes.append(new_class)
                return True
        
        return False
    
    def _schedule_special_single(self, schedule, data, special_period, course, year, section):
        """Schedule a single-hour special period (e.g., Counseling, Sports, Library)"""
        instructor = special_period.instructor
        meeting_times = list(data.get_meetingTimes())
        
        # Try to find an available slot honoring instructor priorities.
        sorted_times = self._sort_meeting_times_by_instructor_priority(meeting_times, instructor, year)
        
        for mt in sorted_times:
            if self._can_schedule_single(schedule, section, course, mt, instructor, year):
                new_class = Class(year, section, course)
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
        ONLY Assistant Professors can be selected as evaluators.
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
        
        # Get all ASSISTANT PROFESSOR instructors from this department
        # CRITICAL: Only Assistant Professors can be evaluators
        dept_instructors = list(Instructor.objects.filter(
            department=dept_code,
            designation='ASST_PROF'  # Only Assistant Professors
        ))
        
        if not dept_instructors:
            logger.warning(f"    No Assistant Professor instructors found for department {dept_code}")
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

def generate_all_years(request):
    """Generate timetables for all years at once"""
    if not request.user.is_authenticated:
        return JsonResponse({
            'error': 'Authentication required. Please login and try again.'
        }, status=401)

    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=400)
    
    years = Year.objects.all().order_by('id')
    total_years = years.count()
    success_count = 0
    failed_years = []
    results = []

    # Clear stale generated data first so cross-year conflict checks use only fresh runs.
    TimetableEntry.objects.all().delete()
    GeneratedTimetable.objects.all().delete()
    
    for year in years:
        try:
            # Create data for this year
            year_data = Data(year)
            year_data.elective_time_tracker = {}
            
            # Generate new timetable using constraint scheduler (retry hard-constraint failures)
            scheduler = ConstraintScheduler()
            schedule = None
            used_attempt = 0
            for attempt in range(1, MAX_ATTEMPTS + 1):
                schedule = scheduler.build_schedule(year_data, year)
                if schedule:
                    used_attempt = attempt
                    break
            
            if schedule:
                # Calculate fitness and conflicts
                conflicts = schedule.getNumbOfConflicts()
                fitness = schedule.getFitness()
                
                # Save to database
                generated_timetable = GeneratedTimetable.objects.create(
                    year=year,
                    fitness_score=fitness,
                    generation_count=used_attempt or 1
                )
                
                # Save all timetable entries
                entry_count = 0
                for cls in schedule.getClasses():
                    # Match the logic from the regular timetable() function
                    # For LAB courses with multiple instructors (non-split), use is_evaluator flag from Class object
                    if cls.course.course_type == 'LAB':
                        TimetableEntry.objects.update_or_create(
                            timetable=generated_timetable,
                            year=year,
                            section_number=cls.section_number,
                            course=cls.course,
                            instructor=cls.instructor,
                            meeting_time=cls.meeting_time,
                            defaults={
                                'lab_room': cls.room if hasattr(cls, 'room') else None,
                                'is_evaluator': cls.is_evaluator
                            }
                        )
                        entry_count += 1
                    else:
                        # For THEORY/ELECTIVE courses: single instructor entry
                        TimetableEntry.objects.get_or_create(
                            timetable=generated_timetable,
                            year=year,
                            section_number=cls.section_number,
                            course=cls.course,
                            instructor=cls.instructor,
                            lab_room=None,
                            meeting_time=cls.meeting_time,
                            defaults={'is_evaluator': False}
                        )
                        entry_count += 1
                
                # Get allocation report for diagnostics
                alloc_report = schedule.get_allocation_report()
                
                # Determine if schedule is fully allocated
                is_fully_allocated = (alloc_report and 
                                     alloc_report['incomplete_count'] == 0)
                
                # Log incomplete courses for debugging
                if alloc_report and alloc_report['incomplete_list']:
                    logger.warning(f"âš ï¸ {year.year_name} has {alloc_report['incomplete_count']} under-allocated course-sections:")
                    for item in alloc_report['incomplete_list']:
                        logger.warning(f"   {item['course']} Sec{item['section']}: {item['got']}/{item['need']} hours")
                
                results.append({
                    'year': year.year_name,
                    'success': True,
                    'classes': len(schedule.getClasses()),
                    'conflicts': conflicts,
                    'fitness': f"{fitness:.2%}",
                    'fully_allocated': is_fully_allocated,
                    'allocation': {
                        'delivered': alloc_report['total_delivered'] if alloc_report else 0,
                        'needed': alloc_report['total_needed'] if alloc_report else 0,
                        'complete_courses': alloc_report['complete'] if alloc_report else 0,
                        'incomplete_courses': alloc_report['incomplete_count'] if alloc_report else 0
                    }
                })
                success_count += 1
            else:
                results.append({
                    'year': year.year_name,
                    'success': False,
                    'error': 'Could not generate schedule'
                })
                failed_years.append(year.year_name)
        
        except Exception as e:
            results.append({
                'year': year.year_name,
                'success': False,
                'error': str(e)
            })
            failed_years.append(year.year_name)
    
    return JsonResponse({
        'total': total_years,
        'success': success_count,
        'failed': len(failed_years),
        'results': results
    })


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
        
        # Convert to class objects for template compatibility
        # DO NOT deduplicate - we need all instructor entries for multi-instructor labs
        classes = []
        for entry in entries:
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
    # Include: course_type='ELECTIVE' OR courses that need alignment (OE/PE by number)
    all_courses = selected_year.courses.all()
    
    # Helper: Identify courses needing alignment (same time for all sections)
    def needs_section_alignment(course):
        """Check if course should be scheduled at same time for all sections"""
        # LAB courses are NEVER aligned - they have batches and separate scheduling
        if course.course_type == 'LAB':
            return False
        
        # CHECK: If same instructor teaches multiple sections, DON'T force alignment
        try:
            from SchedulerApp.models import CourseInstructorAssignment
            assignments = CourseInstructorAssignment.objects.filter(course=course)
            if assignments.exists():
                instructors_per_section = {}
                for a in assignments:
                    inst_ids = set(a.instructors.values_list('id', flat=True))
                    if a.section_number not in instructors_per_section:
                        instructors_per_section[a.section_number] = inst_ids
                    else:
                        instructors_per_section[a.section_number].update(inst_ids)
                
                all_instructors = set()
                for section_insts in instructors_per_section.values():
                    intersection = all_instructors & section_insts
                    if intersection:
                        return False
                    all_instructors.update(section_insts)
        except:
            pass
        
        # ELECTIVE course type always needs alignment
        if course.course_type == 'ELECTIVE':
            return True
        # OE (Open Elective) - starts with 23IT6 or 23IT7 (6xxx/7xxx are elective codes)
        if course.course_number.startswith('23IT6') or course.course_number.startswith('23IT7'):
            return True
        # PE (Professional Elective) - 23IT5xxx series (THEORY courses only, not labs)
        if course.course_number.startswith('23IT5') and course.course_type != 'LAB':
            return True
        return False
    
    # Get all courses that need alignment
    elective_courses = [c for c in all_courses if needs_section_alignment(c)]
    meeting_times = list(MeetingTime.objects.filter(year=selected_year))
    
    logger.info(f"Pre-allocating times for {len(elective_courses)} courses needing section alignment...")
    logger.info(f"  Aligned courses: {[c.course_number for c in elective_courses]}")

    if meeting_times:
        global_used_times = []
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
                    if mt not in global_used_times:
                        day_groups.setdefault(mt.day, []).append(mt)

                for day in day_groups:
                    day_groups[day].sort(key=lambda x: TIME_SLOTS.index((x.time, x.time)))

                valid_blocks = []
                for day, times in day_groups.items():
                    for i in range(len(times) - course.max_continuous_hours + 1):
                        block = times[i:i + course.max_continuous_hours]
                        if not any(t.time == "12:15 - 1:05" for t in block):
                            is_contiguous = True
                            for j in range(len(block)-1):
                                idx1 = TIME_SLOTS.index((block[j].time, block[j].time))
                                idx2 = TIME_SLOTS.index((block[j+1].time, block[j+1].time))
                                if idx2 != idx1 + 1:
                                    is_contiguous = False
                                    break
                            if is_contiguous:
                                valid_blocks.append(block)

                if valid_blocks:
                    block_key = f"{course.course_number}_continuous"
                    import random
                    selected_block = random.choice(valid_blocks)
                    data.elective_time_tracker[block_key] = selected_block
                    logger.info(f"  {course.course_number} continuous: {selected_block[0].day} {[mt.time for mt in selected_block]}")
                    used_times.extend(selected_block)
                    global_used_times.extend(selected_block)

            # SECOND: Pre-allocate single period times from REMAINING times (exclude continuous block times)
            if single_hours > 0:
                available_times = [mt for mt in meeting_times if mt not in used_times and mt not in global_used_times]
                if len(available_times) >= single_hours:
                    single_key = f"{course.course_number}_single"
                    import random
                    def fragmentation_score(mt):
                        if mt.time in ['8:45 - 9:45', '11:25 - 12:15', '1:05 - 1:55', '2:45 - 3:35']: return random.randint(0,10)
                        if mt.time in ['9:45 - 10:35', '10:35 - 11:25', '1:55 - 2:45']: return 100 + random.randint(0,10)
                        return 50
                    available_times.sort(key=fragmentation_score)
                    selected_times = available_times[:single_hours]
                    data.elective_time_tracker[single_key] = selected_times  # Store as LIST
                    global_used_times.extend(selected_times)
                    logger.info(f"  {course.course_number} single ({single_hours} periods): {[(t.day, t.time) for t in selected_times]}")

                    # Also create index tracker for each section
                    index_key = f"{course.course_number}_single_index"
                    data.elective_time_tracker[index_key] = {}

    # Log courses ONCE before scheduling
    # Helper: Identify courses needing alignment (same time for all sections)
    def needs_section_alignment(course):
        """Check if course should be scheduled at same time for all sections"""
        # LAB courses are NEVER aligned - they have batches and separate scheduling
        if course.course_type == 'LAB':
            return False
        
        # CHECK: If same instructor teaches multiple sections, DON'T force alignment
        try:
            from SchedulerApp.models import CourseInstructorAssignment
            assignments = CourseInstructorAssignment.objects.filter(course=course)
            if assignments.exists():
                instructors_per_section = {}
                for a in assignments:
                    inst_ids = set(a.instructors.values_list('id', flat=True))
                    if a.section_number not in instructors_per_section:
                        instructors_per_section[a.section_number] = inst_ids
                    else:
                        instructors_per_section[a.section_number].update(inst_ids)
                
                all_instructors = set()
                for section_insts in instructors_per_section.values():
                    intersection = all_instructors & section_insts
                    if intersection:
                        return False
                    all_instructors.update(section_insts)
        except:
            pass
        
        # ELECTIVE type courses always need alignment
        if course.course_type == 'ELECTIVE':
            return True
        # OE (Open Elective) - 23IT6xxx or 23IT7xxx (THEORY courses only)
        if course.course_number.startswith('23IT6') or course.course_number.startswith('23IT7'):
            return True
        # PE (Professional Elective) - 23IT5xxx (THEORY courses only, not labs)
        if course.course_number.startswith('23IT5') and course.course_type != 'LAB':
            return True
        return False
    
    all_courses = selected_year.courses.all()
    lab_courses = list(all_courses.filter(course_type='LAB').order_by('-priority'))
    elective_courses = [c for c in all_courses if needs_section_alignment(c)]
    all_theory_excluding_aligned = [c for c in all_courses.filter(course_type='THEORY') if c not in elective_courses]
    continuous_theory_courses = list([c for c in all_theory_excluding_aligned if c.max_continuous_hours > 1])
    regular_theory_courses = list([c for c in all_theory_excluding_aligned if c.max_continuous_hours == 1])
    
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
            # SUCCESS: Schedule passed all hard constraints (including TP continuity)
            conflicts = schedule.getNumbOfConflicts()
            fitness = schedule.getFitness()
            
            logger.info(f"[OK] Attempt {attempt}: TP courses are continuous (fitness: {fitness:.2%}, conflicts: {conflicts})")

            logger.info(f"SUCCESS on attempt {attempt}! Schedule created with {len(schedule.getClasses())} classes")
            break
        else:
            logger.warning(f"âœ— Attempt {attempt} failed hard constraints (including TP continuity), retrying...")
    
    if not schedule:
        logger.error(f"FAILED to create schedule after {MAX_ATTEMPTS} attempts")
        
        # Fall back to existing timetable if available
        if existing_timetable:
            entries = TimetableEntry.objects.filter(timetable=existing_timetable)
            
            # DO NOT deduplicate - we need all instructor entries for multi-instructor labs
            classes = []
            for entry in entries:
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
        # For LAB courses with multiple instructors (non-split), use is_evaluator flag from Class object
        if cls.course.course_type == 'LAB':
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
        'generation_count': attempt,
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
    # Key: (year, section, course, day, time, room) â†’ entry
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
                        'schedule': _convert_entries_to_classes(entries, deduplicate_lab_instructors=True),
                        'total_classes': len(set((e.meeting_time.day, e.meeting_time.time) for e in entries))
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
            context['schedule'] = _convert_entries_to_classes(entries, deduplicate_lab_instructors=True)
            context['total_classes'] = len(set((e.meeting_time.day, e.meeting_time.time) for e in entries))
    
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
            
    # HALF-DAY WISE (Show who's FREE for an entire half day)
    elif view_type == 'halfday':
        day = request.GET.get('day')
        half = request.GET.get('half')  # 'forenoon' or 'afternoon'
        
        if day and half:
            # Determine relevant time slots based on index
            all_slots = [slot[0] for slot in TIME_SLOTS]
            
            if half == 'forenoon':
                # First 4 periods (indexes 0, 1, 2, 3)
                target_slots = all_slots[:4]
            else:
                # Afternoon periods (skipping lunch which is usually index 4 depending on year, so we take periods after 12:15)
                # Just take the last 3 slots, since the system normally has 8 slots total (4 forenoon, 1 lunch, 3 afternoon)
                target_slots = all_slots[-3:]
                
            # Get all faculty teaching at ANY of these times
            busy_faculty = TimetableEntry.objects.filter(
                meeting_time__day=day,
                meeting_time__time__in=target_slots,
                instructor__isnull=False
            ).values_list('instructor_id', flat=True).distinct()
            
            # Get free faculty
            all_faculty = Instructor.objects.all()
            free_faculty = all_faculty.exclude(id__in=busy_faculty)
            
            # Get busy faculty details across the half day to show what they are doing
            busy_entries = TimetableEntry.objects.filter(
                meeting_time__day=day,
                meeting_time__time__in=target_slots,
                instructor__isnull=False
            ).select_related('course', 'instructor', 'meeting_time', 'year')
            
            busy_faculty_dict = {}
            for entry in busy_entries:
                if entry.instructor not in busy_faculty_dict:
                    busy_faculty_dict[entry.instructor] = []
                busy_faculty_dict[entry.instructor].append(entry)
                
            context['selected_day'] = day
            context['selected_half'] = half
            context['target_slots'] = target_slots
            context['free_faculty'] = free_faculty
            context['busy_faculty_dict'] = busy_faculty_dict
            context['total_free'] = free_faculty.count()
            context['total_busy'] = len(busy_faculty_dict)
    
    return render(request, 'view_timetable.html', context)


def _convert_entries_to_classes(entries, deduplicate_lab_instructors=False):
    """
    Helper function to convert TimetableEntry queryset to Class objects
    """
    classes = []
    seen = {}
    for entry in entries:
        if deduplicate_lab_instructors and entry.course.course_type == 'LAB':
            key = (entry.year_id, entry.section_number, entry.course_id, entry.meeting_time.day, entry.meeting_time.time, entry.lab_room_id)
            if key in seen:
                # Add instructor to the list of instructors
                if entry.instructor:
                    seen[key].append(entry.instructor.name)
                continue
            else:
                if entry.instructor:
                    seen[key] = [entry.instructor.name]
                else:
                    seen[key] = []
        
        cls = Class(entry.year, entry.section_number, entry.course)
        cls.set_instructor(entry.instructor)
        cls.set_meetingTime(entry.meeting_time)
        cls.room = entry.lab_room
        classes.append(cls)
    
    # If deduplicated, we could optionally update the instructor names on the class objects
    if deduplicate_lab_instructors:
        for cls in classes:
            if cls.course.course_type == 'LAB':
                key = (cls.year.id, cls.section_number, cls.course.course_number, cls.meeting_time.day, cls.meeting_time.time, cls.room.id if cls.room else None)
                if key in seen and seen[key]:
                    # Create a dummy instructor with comma separated names
                    class DummyInstructor:
                        def __init__(self, names):
                            self.name = ", ".join(names)
                    cls.set_instructor(DummyInstructor(seen[key]))
                    
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
        issues.append(f"âš ï¸ No courses linked to {selected_year.year_name}! Edit year at /yearEdit/ and select courses")
    
    if data_info['year_meeting_times'].count() == 0:
        issues.append(f"âš ï¸ No meeting times for {selected_year.year_name}! Add time slots at /meetingTimeAdd/ and select this year")
    
    # Check for lab courses without lab rooms
    lab_courses = data_info['year_courses'].filter(course_type='LAB')
    if lab_courses.exists() and data_info['total_lab_rooms'] == 0:
        issues.append("âš ï¸ Lab courses exist but no lab rooms! Add lab rooms at /labRoomAdd/")
    
    # Check for courses without instructor assignments
    for section_number in data_info['year_sections']:
        for course in data_info['year_courses']:
            assignment = CourseInstructorAssignment.objects.filter(
                year=selected_year, section_number=section_number, course=course
            ).first()
            if not assignment:
                issues.append(f"âš ï¸ No instructor assigned for {course.course_number} in section {section_number}")
            elif assignment.instructors.count() == 0:
                issues.append(f"âš ï¸ No instructors selected for {course.course_number} in section {section_number}")
    
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
            
            # Get time slots excluding the lunch period for this year
            time_slots = []
            for i, slot in enumerate(TIME_SLOTS, start=1):
                if i != year.lunch_period:
                    time_slots.append(slot[0])
            
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


# ============================================================
# INSTRUCTOR LOGIN AND PRIORITY MANAGEMENT
# ============================================================

def instructor_login(request):
    """Instructor login view using email and password"""
    if request.user.is_authenticated:
        # Check if user is an instructor
        try:
            instructor = Instructor.objects.get(user=request.user)
            return redirect('instructor_dashboard')
        except Instructor.DoesNotExist:
            logout(request)
    
    if request.method == 'POST':
        form = InstructorLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            # Find instructor by email
            try:
                instructor = Instructor.objects.get(email=email)
                # Authenticate using the linked user account
                user = authenticate(request, username=instructor.user.username if instructor.user else email, password=password)
                
                if user is not None:
                    login(request, user)
                    return redirect('instructor_dashboard')
                else:
                    messages.error(request, 'Invalid email or password')
            except Instructor.DoesNotExist:
                messages.error(request, 'Invalid email or password')
    else:
        form = InstructorLoginForm()
    
    return render(request, 'instructor_login.html', {'form': form})


def instructor_logout(request):
    """Logout instructor"""
    logout(request)
    return redirect('instructor_login')


@login_required
def instructor_dashboard(request):
    """Instructor dashboard showing their profile, courses, and timetable"""
    try:
        instructor = Instructor.objects.get(user=request.user)
    except Instructor.DoesNotExist:
        messages.error(request, 'Instructor profile not found')
        return redirect('home')
    
    # Get instructor's priorities
    priorities = InstructorPriority.objects.filter(instructor=instructor)
    days_with_priorities = [p.day for p in priorities]
    
    # Check which days are missing priorities
    all_days = [day[0] for day in DAYS_OF_WEEK]
    missing_days = [day for day in all_days if day not in days_with_priorities]
    
    # Get courses where this instructor is assigned (main or evaluator)
    assigned_courses = CourseInstructorAssignment.objects.filter(
        instructors=instructor
    ).select_related('year', 'course').order_by('year', 'section_number', 'course__course_name')
    
    # Get instructor's timetable entries
    timetable_entries = TimetableEntry.objects.filter(
        instructor=instructor
    ).select_related('year', 'course', 'meeting_time', 'lab_room').order_by(
        'meeting_time__day', 'meeting_time__time'
    )
    
    # Organize timetable by day and time
    timetable_by_day = defaultdict(list)
    for entry in timetable_entries:
        day = entry.meeting_time.day
        timetable_by_day[day].append(entry)
    
    # Get the days in correct order
    days_order = [day[0] for day in DAYS_OF_WEEK]
    ordered_timetable = [(day, timetable_by_day.get(day, [])) for day in days_order if timetable_by_day.get(day)]
    
    # Count total teaching hours
    total_hours = timetable_entries.count()
    
    context = {
        'instructor': instructor,
        'priorities': priorities,
        'missing_days': missing_days,
        'priorities_complete': len(missing_days) == 0,
        'assigned_courses': assigned_courses,
        'timetable_entries': timetable_entries,
        'timetable_by_day': ordered_timetable,
        'total_hours': total_hours,
    }
    
    return render(request, 'instructor_dashboard.html', context)


def unified_login(request):
    """Unified login view with role selection (Admin or Instructor)"""
    if request.user.is_authenticated:
        # Redirect based on user type
        try:
            instructor = Instructor.objects.get(user=request.user)
            return redirect('instructor_dashboard')
        except Instructor.DoesNotExist:
            # Assume admin user
            return redirect('home')
    
    if request.method == 'POST':
        form = UnifiedLoginForm(request.POST)
        if form.is_valid():
            role = form.cleaned_data['role']
            username_or_email = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            if role == 'admin':
                # Admin login using username
                user = authenticate(request, username=username_or_email, password=password)
                if user is not None and user.is_staff:
                    login(request, user)
                    return redirect('home')
                else:
                    messages.error(request, 'Invalid admin credentials or insufficient permissions')
            
            elif role == 'instructor':
                # Instructor login using email
                try:
                    instructor = Instructor.objects.get(email=username_or_email)
                    # Authenticate using the linked user account
                    user = authenticate(request, username=instructor.user.username if instructor.user else username_or_email, password=password)
                    
                    if user is not None:
                        login(request, user)
                        return redirect('instructor_dashboard')
                    else:
                        messages.error(request, 'Invalid instructor credentials')
                except Instructor.DoesNotExist:
                    messages.error(request, 'Instructor not found with this email')
    else:
        form = UnifiedLoginForm()
    
    return render(request, 'registration/unified_login.html', {'form': form})


@login_required
def instructor_set_priorities(request):
    """View for instructors to set their period priorities"""
    try:
        instructor = Instructor.objects.get(user=request.user)
    except Instructor.DoesNotExist:
        messages.error(request, 'Instructor profile not found')
        return redirect('home')
    
    if request.method == 'POST':
        day = request.POST.get('day')
        
        # Get or create priority for this day
        priority, created = InstructorPriority.objects.get_or_create(
            instructor=instructor,
            day=day
        )
        
        # Update priorities for all 7 periods
        for period in range(1, 8):
            priority_value = request.POST.get(f'period_{period}_priority')
            if priority_value:
                priority.set_period_priority(period, int(priority_value))
        
        priority.save()
        messages.success(request, f'Priorities saved for {day}')
        return redirect('instructor_dashboard')
    
    # GET request - show form
    day = request.GET.get('day')
    if not day:
        # Show day selection
        all_days = [day[0] for day in DAYS_OF_WEEK]
        existing_priorities = InstructorPriority.objects.filter(instructor=instructor)
        days_with_priorities = [p.day for p in existing_priorities]
        
        context = {
            'instructor': instructor,
            'all_days': all_days,
            'days_with_priorities': days_with_priorities
        }
        return render(request, 'instructor_select_day.html', context)
    
    # Show priority form for selected day
    priority = InstructorPriority.objects.filter(instructor=instructor, day=day).first()
    
    # Prepare period data with existing priority values and time slots
    # Priorities are for 7 teaching periods (lunch excluded).
    teaching_slots = [slot[1] for idx, slot in enumerate(TIME_SLOTS, start=1) if idx != 5]
    period_data = []
    for period in range(1, 8):
        current_value = priority.get_period_priority(period) if priority else period
        # Periods are teaching periods only: 1..7 mapped after excluding lunch slot.
        time_slot = teaching_slots[period - 1] if period <= len(teaching_slots) else ''
        period_data.append({
            'number': period,
            'value': current_value,
            'time_slot': time_slot
        })
    
    context = {
        'instructor': instructor,
        'day': day,
        'priority': priority,
        'period_data': period_data
    }
    
    return render(request, 'instructor_set_priorities.html', context)


@login_required
def instructor_view_priorities(request):
    """View all priorities for the instructor"""
    try:
        instructor = Instructor.objects.get(user=request.user)
    except Instructor.DoesNotExist:
        messages.error(request, 'Instructor profile not found')
        return redirect('home')
    
    priorities = InstructorPriority.objects.filter(instructor=instructor).order_by('day')
    
    context = {
        'instructor': instructor,
        'priorities': priorities,
        'time_slots': TIME_SLOTS
    }
    
    return render(request, 'instructor_view_priorities.html', context)


'''
Error pages
'''

def error_404(request, exception):
    return render(request,'errors/404.html', {})

def error_500(request, *args, **argv):
    return render(request,'errors/500.html', {})


