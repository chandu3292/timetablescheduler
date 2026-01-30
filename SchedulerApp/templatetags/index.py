from django import template

register = template.Library()


@register.filter
def dictKey(d, k):
    '''Returns the given key from a dictionary.'''
    return ', '.join(d.get(k, [])) if d else ''


@register.simple_tag
def sub(schedule, section_id, day, time):
    '''
    Returns the subject-teacher for a SECTION, weekday and time period
    (SECTION-wise timetable)
    '''
    for c in schedule:
        if (
            str(c.section) == str(section_id) and
            c.meeting_time.day == day and
            c.meeting_time.time == time
        ):
            return f'{c.course.course_name} ({c.instructor.name})'
    return ''


@register.simple_tag
def sub_instructor(schedule, instructor, day, time):
    '''
    Returns the subject for an INSTRUCTOR, weekday and time period
    (Instructor-wise timetable)
    '''
    for c in schedule:
        if (
            c.instructor == instructor and
            c.meeting_time.day == day and
            c.meeting_time.time == time
        ):
            return f'{c.course.course_name} ({c.section}, {c.room.r_number})'
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
