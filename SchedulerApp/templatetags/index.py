from django import template

register = template.Library()


@register.filter
def dictKey(d, k):
    '''Returns the given key from a dictionary.'''
    return ', '.join(d.get(k, [])) if d else ''


@register.simple_tag
def sub(schedule, section_number, day, time):
    '''
    Returns the subject-teacher for a SECTION, weekday and time period
    (SECTION-wise timetable)
    Shows batch information for split labs
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
    
    # Multiple classes at same time (batch splitting)
    # Group by batch
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
