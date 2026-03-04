from django.contrib import admin
from .models import *
from .models import CourseInstructorAssignment, GeneratedTimetable, TimetableEntry

admin.site.register(LabRoom)
admin.site.register(Instructor)
admin.site.register(MeetingTime)

class CourseAdmin(admin.ModelAdmin):
    exclude = ('max_numb_students',)

admin.site.register(Course, CourseAdmin)
admin.site.register(Department)
admin.site.register(Year)
admin.site.register(CourseInstructorAssignment)
admin.site.register(GeneratedTimetable)
admin.site.register(TimetableEntry)