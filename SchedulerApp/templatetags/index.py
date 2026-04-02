from django import template

register = template.Library()


@register.filter
def dictKey(d, k):
    '''Returns the given key from a dictionary.'''
    return ', '.join(d.get(k, [])) if d else ''


def _get_time_slots():
    """Get ordered time slots from settings"""
    from SchedulerApp.models import TIME_SLOTS
    return [slot[0] for slot in TIME_SLOTS]


def _is_lab_block_start(schedule, section_number, day, time):
    """
    Check if this time slot is the START of a multi-period lab block.
    Returns (is_start, rowspan, content) or (False, 0, None)
    """
    classes_at_time = [
        c for c in schedule
        if c.section_number == section_number 
        and c.meeting_time.day == day 
        and c.meeting_time.time == time
    ]
    
    if not classes_at_time:
        return False, 0, None
    
    # Check if this is a multi-instructor LAB
    course_types = set(c.course.course_type for c in classes_at_time)
    if 'LAB' not in course_types:
        return False, 0, None
    
    course_names = set(c.course.course_name for c in classes_at_time)
    if len(course_names) != 1:
        return False, 0, None
    
    # This is a multi-instructor lab - now check if it's the first period
    time_slots = _get_time_slots()
    current_idx = time_slots.index(time)
    
    # Count consecutive periods with same lab
    consecutive_count = 1
    course_name = classes_at_time[0].course.course_name
    
    # Look ahead for consecutive periods
    for i in range(current_idx + 1, len(time_slots)):
        next_time = time_slots[i]
        
        # Skip lunch
        if "12:15 - 1:05" in next_time:
            break
        
        next_classes = [
            c for c in schedule
            if c.section_number == section_number 
            and c.meeting_time.day == day 
            and c.meeting_time.time == next_time
            and c.course.course_name == course_name
        ]
        
        if next_classes:
            consecutive_count += 1
        else:
            break
    
    # Check if previous period has same lab (if so, this is not the start)
    if current_idx > 0:
        prev_time = time_slots[current_idx - 1]
        if "12:15 - 1:05" not in prev_time:
            prev_classes = [
                c for c in schedule
                if c.section_number == section_number 
                and c.meeting_time.day == day 
                and c.meeting_time.time == prev_time
                and c.course.course_name == course_name
            ]
            if prev_classes:
                # This is a continuation, not a start
                return False, 0, None
    
    # This is the start of a lab block
    if consecutive_count > 1:
        # Build content with all instructors
        c = classes_at_time[0]
        instructors = [cls.instructor.name for cls in classes_at_time if cls.instructor]
        room_info = f' - {c.room}' if c.room else ''
        content = f'{c.course.course_name} ({", ".join(instructors)}{room_info})'
        
        return True, consecutive_count, content
    
    return False, 0, None


@register.simple_tag
def is_lab_block_start(schedule, section_number, day, time):
    """Template tag to check if this is the start of a lab block"""
    is_start, rowspan, content = _is_lab_block_start(schedule, section_number, day, time)
    return is_start


@register.simple_tag
def get_lab_rowspan(schedule, section_number, day, time):
    """Template tag to get rowspan for lab block"""
    is_start, rowspan, content = _is_lab_block_start(schedule, section_number, day, time)
    return rowspan if is_start else 1


@register.simple_tag
def get_lab_content(schedule, section_number, day, time):
    """Template tag to get content for lab block"""
    is_start, rowspan, content = _is_lab_block_start(schedule, section_number, day, time)
    return content if content else ''


@register.simple_tag
def is_lab_continuation(schedule, section_number, day, time):
    """
    Check if this cell is a continuation of a previous lab block (should be hidden)
    """
    classes_at_time = [
        c for c in schedule
        if c.section_number == section_number 
        and c.meeting_time.day == day 
        and c.meeting_time.time == time
    ]
    
    if not classes_at_time:
        return False
    
    # Check if this is a LAB
    course_types = set(c.course.course_type for c in classes_at_time)
    if 'LAB' not in course_types:
        return False
    
    course_names = set(c.course.course_name for c in classes_at_time)
    if len(course_names) != 1:
        return False
    
    # Check if previous period has same lab
    time_slots = _get_time_slots()
    current_idx = time_slots.index(time)
    
    if current_idx > 0:
        prev_time = time_slots[current_idx - 1]
        if "12:15 - 1:05" not in prev_time:
            course_name = classes_at_time[0].course.course_name
            prev_classes = [
                c for c in schedule
                if c.section_number == section_number 
                and c.meeting_time.day == day 
                and c.meeting_time.time == prev_time
                and c.course.course_name == course_name
            ]
            if prev_classes:
                # This is a continuation
                return True
    
    return False


@register.simple_tag
def sub(schedule, section_number, day, time):
    '''
    Returns the subject-teacher for a SECTION, weekday and time period
    (SECTION-wise timetable)
    Shows batch information for split labs
    For multi-instructor labs: Shows all instructors in one display
    '''
    classes_at_time = []
    for c in schedule:
        if (
            c.section_number == section_number and
            c.meeting_time.day == day and
            c.meeting_time.time == time
        ):
            classes_at_time.append(c)
    
    if not classes_at_time:
        return ''
    
    # If only one class (normal case)
    if len(classes_at_time) == 1:
        c = classes_at_time[0]
        instructor_name = c.instructor.name if c.instructor else 'No Instructor'
        room_info = f', {c.room}' if c.room else ''
        
        # Check if this is a split lab
        if hasattr(c, 'batch') and c.batch != 'FULL':
            return f'{c.course.course_name} [{c.batch}] ({instructor_name}{room_info})'
        else:
            return f'{c.course.course_name} ({instructor_name}{room_info})'
    
    # Multiple classes at same time
    # Check if they are all the same LAB course (multi-instructor lab)
    course_names = set(c.course.course_name for c in classes_at_time)
    course_types = set(c.course.course_type for c in classes_at_time)
    
    if len(course_names) == 1 and len(course_types) == 1 and 'LAB' in course_types:
        # Multi-instructor LAB - show all instructors together
        c = classes_at_time[0]
        instructors = [cls.instructor.name for cls in classes_at_time if cls.instructor]
        room_info = f' - {c.room}' if c.room else ''
        
        return f'{c.course.course_name} ({", ".join(instructors)}{room_info})'
    
    # Different courses or batch splitting
    result = []
    for c in classes_at_time:
        instructor_name = c.instructor.name if c.instructor else 'No Instructor'
        room_info = f', {c.room}' if c.room else ''
        batch_label = c.batch if hasattr(c, 'batch') and c.batch != 'FULL' else ''
        
        if batch_label:
            result.append(f'{c.course.course_name} [{batch_label}] ({instructor_name}{room_info})')
        else:
            result.append(f'{c.course.course_name} ({instructor_name}{room_info})')
    
    return '<br>'.join(result)


@register.simple_tag
def sub_instructor(schedule, instructor, day, time):
    '''
    Returns the subject for an INSTRUCTOR, weekday and time period
    (Instructor-wise timetable)
    Shows co-instructors for LAB courses and batch information for split labs
    '''
    from SchedulerApp.models import CourseInstructorAssignment
    
    for c in schedule:
        if (
            c.instructor == instructor and
            c.meeting_time.day == day and
            c.meeting_time.time == time
        ):
            room_info = f', {c.room}' if c.room else ''
            batch_info = f' [{c.batch}]' if hasattr(c, 'batch') and c.batch != 'FULL' else ''
            
            # For LAB courses, show co-instructors
            if c.course.course_type == 'LAB':
                # Get all instructors for this lab section
                assignment = CourseInstructorAssignment.objects.filter(
                    year=c.year,
                    section_number=c.section_number,
                    course=c.course
                ).first()
                
                if assignment and assignment.instructors.count() > 1:
                    # Get other instructors (excluding current one)
                    other_instructors = [inst.name for inst in assignment.instructors.all() if inst != instructor]
                    if other_instructors:
                        co_inst_text = f' (with {", ".join(other_instructors)})'
                        return f'{c.course.course_name}{batch_info} ({c.year.year_name} - Sec {c.section_number}{room_info}{co_inst_text})'
            
            return f'{c.course.course_name}{batch_info} ({c.year.year_name} - Sec {c.section_number}{room_info})'
    return ''


@register.tag
def active(parser, token):
    args = token.split_contents()
    template_tag = args[0]
    if len(args) < 2:
        raise template.TemplateSyntaxError(
            f'{template_tag} tag requires at least one argument'
        )
    return NavSelectedNode(args[1:])


class NavSelectedNode(template.Node):
    def __init__(self, patterns):
        self.patterns = patterns

    def render(self, context):
        path = context['request'].path
        for p in self.patterns:
            pValue = template.Variable(p).resolve(context)
            if path == pValue:
                return 'active'
        return ''
def _is_general_lab_block_start(schedule, day, time, view_type='lab'):
    classes_at_time = [
        c for c in schedule
        if c.meeting_time.day == day 
        and c.meeting_time.time == time
    ]
    
    if not classes_at_time:
        return False, 0, None
    
    # Check if this is a LAB
    course_types = set(c.course.course_type for c in classes_at_time)
    if 'LAB' not in course_types:
        return False, 0, None
    
    course_names = set(c.course.course_name for c in classes_at_time)
    if len(course_names) != 1:
        return False, 0, None
    
    time_slots = _get_time_slots()
    current_idx = time_slots.index(time)
    
    # Count consecutive periods with same lab
    consecutive_count = 1
    course_name = classes_at_time[0].course.course_name
    section_number = classes_at_time[0].section_number
    
    # Look ahead for consecutive periods
    for i in range(current_idx + 1, len(time_slots)):
        next_time = time_slots[i]
        
        # Skip lunch
        if "12:15 - 1:05" in next_time:
            break
        
        next_classes = [
            c for c in schedule
            if c.meeting_time.day == day 
            and c.meeting_time.time == next_time
            and c.course.course_name == course_name
            and c.section_number == section_number
        ]
        
        if next_classes:
            consecutive_count += 1
        else:
            break
    
    # Check if previous period has same lab (if so, this is not the start)
    if current_idx > 0:
        prev_time = time_slots[current_idx - 1]
        if "12:15 - 1:05" not in prev_time:
            prev_classes = [
                c for c in schedule
                if c.meeting_time.day == day 
                and c.meeting_time.time == prev_time
                and c.course.course_name == course_name
                and c.section_number == section_number
            ]
            if prev_classes:
                # This is a continuation, not a start
                return False, 0, None
    
    # This is the start of a lab block
    if consecutive_count > 1:
        c = classes_at_time[0]
        instructors = [cls.instructor.name for cls in classes_at_time if cls.instructor]
        instructors_str = ", ".join(instructors)
        
        # Build HTML content based on view_type format
        # This matches the class-card HTML structure
        content = f'''
        <div class="class-card lab" style="margin:0; height:100%;">
            <div class="class-course">{c.course.course_name}</div>
            <div class="class-instructor">{instructors_str}</div>
            <div class="class-room">{c.year.year_name} S{c.section_number}</div>
        </div>
        '''
        
        return True, consecutive_count, content
    
    return False, 0, None


@register.simple_tag
def is_general_lab_block_start(schedule, day, time, view_type='lab'):
    is_start, rowspan, content = _is_general_lab_block_start(schedule, day, time, view_type)
    return is_start


@register.simple_tag
def get_general_lab_rowspan(schedule, day, time, view_type='lab'):
    is_start, rowspan, content = _is_general_lab_block_start(schedule, day, time, view_type)
    return rowspan if is_start else 1


@register.simple_tag
def get_general_lab_content(schedule, day, time, view_type='lab'):
    is_start, rowspan, content = _is_general_lab_block_start(schedule, day, time, view_type)
    return content if content else ''


@register.simple_tag
def is_general_lab_continuation(schedule, day, time):
    classes_at_time = [
        c for c in schedule
        if c.meeting_time.day == day 
        and c.meeting_time.time == time
    ]
    
    if not classes_at_time:
        return False
    
    # Check if this is a LAB
    course_types = set(c.course.course_type for c in classes_at_time)
    if 'LAB' not in course_types:
        return False
    
    course_names = set(c.course.course_name for c in classes_at_time)
    if len(course_names) != 1:
        return False
    
    time_slots = _get_time_slots()
    current_idx = time_slots.index(time)
    
    if current_idx > 0:
        prev_time = time_slots[current_idx - 1]
        if "12:15 - 1:05" not in prev_time:
            course_name = classes_at_time[0].course.course_name
            section_number = classes_at_time[0].section_number
            
            prev_classes = [
                c for c in schedule
                if c.meeting_time.day == day 
                and c.meeting_time.time == prev_time
                and c.course.course_name == course_name
                and c.section_number == section_number
            ]
            if prev_classes:
                return True
    
    return False

