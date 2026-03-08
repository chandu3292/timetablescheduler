from django import template

register = template.Library()


@register.filter
def dictKey(d, k):
    return ', '.join(d.get(k, [])) if d else ''


@register.simple_tag
def sub(schedule, section_id, day, time):
    """
    Returns formatted label for a cell in the timetable grid.
    schedule is a list of Gene-like objects or dicts from _build_context entries.
    """
    for c in schedule:
        if str(c.section) != str(section_id):
            continue
        for i, mt in enumerate(c.meeting_times):
            if mt.day == day and mt.time == time:
                label = c.course.course_name
                ct    = c.course.course_type
                if c.is_special:
                    label += ' [Special]'
                elif ct == 'ELECTIVE':
                    label += ' [Elective]'
                elif ct == 'LAB':
                    label += ' [Lab]' if i == 0 else ' [Lab cont.]'
                inst = c.instructor
                inst_name = inst.name if hasattr(inst, 'name') else str(inst) if inst else ''
                return f'{label} ({inst_name})' if inst_name else label
    return ''


@register.simple_tag
def sub_instructor(schedule, instructor, day, time):
    """Returns the subject for an INSTRUCTOR, weekday and time period."""
    for c in schedule:
        if c.instructor != instructor:
            continue
        for mt in c.meeting_times:
            if mt.day == day and mt.time == time:
                lr = c.lab_room.lab_name if c.lab_room else ''
                room_str = f', {lr}' if lr else ''
                return f'{c.course.course_name} (S{c.section}{room_str})'
    return ''


@register.tag
def active(parser, token):
    args = token.split_contents()
    if len(args) < 2:
        raise template.TemplateSyntaxError(
            f'{args[0]} tag requires at least one argument')
    return NavSelectedNode(args[1:])


class NavSelectedNode(template.Node):
    def __init__(self, patterns):
        self.patterns = patterns

    def render(self, context):
        path = context['request'].path
        for p in self.patterns:
            if path == template.Variable(p).resolve(context):
                return 'active'
        return ''
