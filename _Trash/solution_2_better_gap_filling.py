"""
SOLUTION 2: SMARTER GAP-FILLING ALGORITHM
==========================================

Add an aggressive final gap-filling phase that:
1. Identifies incomplete courses
2. For electives: Try to find common slots for ALL sections
3. For regular courses: Fill per section with relaxed constraints
4. Uses constraint relaxation when needed

This code adds a new method to SchedulerApp/views.py
"""

code_to_add = """
def _emergency_gap_filler(self, schedule, data, selected_year, sections):
    \"\"\"
    EMERGENCY: Fill remaining gaps with maximum flexibility
    Called as absolute last resort when all other scheduling fails
    \"\"\"
    from collections import defaultdict
    import random
    
    logger.info("🚨 EMERGENCY GAP FILLING: Last resort to complete all courses")
    
    all_courses = selected_year.courses.all()
    meeting_times = list(data.get_meetingTimes())
    
    # Helper to check if course needs alignment
    def needs_section_alignment(course):
        if course.course_type == 'LAB':
            return False
        if course.course_type == 'ELECTIVE':
            return True
        if course.course_number.startswith('23IT6') or course.course_number.startswith('23IT7'):
            return True
        if course.course_number.startswith('23IT5') and course.course_type != 'LAB':
            return True
        return False
    
    gaps_filled = 0
    
    for course in all_courses:
        if course.course_number in ['COUNSELING', 'SPORTS_LIBRARY', 'SPORT', 'COUNS']:
            continue
        
        # Check if course needs alignment
        if needs_section_alignment(course):
            # ALIGNED COURSES: Must find common slots for ALL sections
            logger.info(f"  Emergency filling ALIGNED course: {course.course_number}")
            
            # Calculate how many hours each section needs
            section_needs = {}
            for section in sections:
                scheduled = sum(1 for cls in schedule._classes 
                              if cls.section_number == section and cls.course == course)
                needed = course.hours_per_week - scheduled
                section_needs[section] = needed
            
            max_need = max(section_needs.values()) if section_needs else 0
            
            if max_need > 0:
                logger.info(f"    Needs: {section_needs}")
                
                # Try to find common slots
                attempts = 0
                max_attempts = len(meeting_times) * 3
                
                while max_need > 0 and attempts < max_attempts:
                    attempts += 1
                    
                    # Pick a random time
                    mt = random.choice(meeting_times)
                    
                    # Check if ALL sections that need hours can use this slot
                    can_schedule_all_who_need = True
                    sections_that_need = [s for s, need in section_needs.items() if need > 0]
                    
                    for section in sections_that_need:
                        if not self._can_schedule_single(schedule, section, course, mt, year=selected_year):
                            can_schedule_all_who_need = False
                            break
                    
                    if can_schedule_all_who_need and len(sections_that_need) > 0:
                        # Schedule for all sections that need it
                        for section in sections_that_need:
                            instructors = self._get_instructors(course, selected_year, section)
                            instructor = instructors[0] if instructors else None
                            
                            new_class = Class(selected_year, section, course, batch='FULL')
                            new_class.set_meetingTime(mt)
                            new_class.set_instructor(instructor)
                            new_class.set_room(None)
                            schedule._classes.append(new_class)
                            
                            section_needs[section] -= 1
                            gaps_filled += 1
                        
                        max_need = max(section_needs.values())
                        logger.info(f"    ✓ Filled {len(sections_that_need)} sections at {mt.day} {mt.time}")
                
                if max_need > 0:
                    logger.error(f"    ❌ Could not fill all gaps for {course.course_number} (alignment required)")
        
        else:
            # NON-ALIGNED COURSES: Fill per section independently
            for section in sections:
                scheduled = sum(1 for cls in schedule._classes 
                              if cls.section_number == section and cls.course == course)
                needed = course.hours_per_week - scheduled
                
                if needed > 0:
                    logger.info(f"  Emergency filling {course.course_number} Sec{section}: need {needed} hours")
                    
                    # Try to fill with maximum relaxation
                    filled = 0
                    for mt in meeting_times:
                        if filled >= needed:
                            break
                        
                        # Very relaxed check - just avoid hard conflicts
                        if self._can_schedule_single(schedule, section, course, mt, year=selected_year):
                            instructors = self._get_instructors(course, selected_year, section)
                            instructor = instructors[0] if instructors else None
                            
                            new_class = Class(selected_year, section, course, batch='FULL')
                            new_class.set_meetingTime(mt)
                            new_class.set_instructor(instructor)
                            new_class.set_room(None)
                            schedule._classes.append(new_class)
                            
                            filled += 1
                            gaps_filled += 1
                    
                    if filled < needed:
                        logger.error(f"    ❌ Only filled {filled}/{needed} for {course.course_number} Sec{section}")
    
    logger.info(f"🚨 Emergency gap filling complete: {gaps_filled} hours added")
    return gaps_filled
"""

print("="*80)
print("SOLUTION 2: IMPROVED GAP-FILLING ALGORITHM")
print("="*80)
print("""
ADD THIS METHOD to ConstraintScheduler class in views.py:

The method:
1. Identifies which courses have gaps
2. For ALIGNED courses (electives): Finds common slots for all sections
3. For REGULAR courses: Fills per section with relaxed constraints
4. Uses random slot selection to explore more options

WHERE TO ADD:
- Add the _emergency_gap_filler method to ConstraintScheduler class
- Call it at the very end of build_schedule() method
- Only runs if gaps still exist after all other phases

BENEFITS:
- Maintains elective alignment even in gap-filling
- More aggressive search for available slots
- Last resort to ensure 100% completion
""")

print("\nCode to add is saved above.")
print("This provides a safety net when normal scheduling can't complete.")
