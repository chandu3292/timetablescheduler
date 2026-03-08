from django.contrib import admin
from .models import (
    Instructor, LabRoom, Course, Department, Year, MeetingTime,
    CourseInstructorAssignment, SpecialPeriod, GeneratedTimetable,
    TimetableEntry, LabBatchAssignment,
)

admin.site.register(Instructor)
admin.site.register(LabRoom)
admin.site.register(Course)
admin.site.register(Department)
admin.site.register(Year)
admin.site.register(MeetingTime)
admin.site.register(CourseInstructorAssignment)
admin.site.register(SpecialPeriod)
admin.site.register(GeneratedTimetable)
admin.site.register(TimetableEntry)
admin.site.register(LabBatchAssignment)
