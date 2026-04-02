from django.contrib import admin
from .models import *
from .models import CourseInstructorAssignment, GeneratedTimetable, TimetableEntry

@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ['uid', 'name', 'email', 'designation', 'department']
    list_filter = ['designation', 'department']
    search_fields = ['uid', 'name', 'email']
    list_editable = ['designation', 'department']

@admin.register(InstructorPriority)
class InstructorPriorityAdmin(admin.ModelAdmin):
    list_display = ['instructor', 'day', 'period_1_priority', 'period_2_priority', 'period_3_priority', 
                    'period_4_priority', 'period_5_priority', 'period_6_priority', 'period_7_priority']
    list_filter = ['day', 'instructor']
    search_fields = ['instructor__name']

admin.site.register(LabRoom)
admin.site.register(MeetingTime)

class CourseAdmin(admin.ModelAdmin):
    list_display = ('course_number', 'course_name', 'course_type', 'hours_per_week', 'priority')
    list_filter = ('course_type',)
    search_fields = ('course_number', 'course_name')
    list_editable = ()
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('course_number', 'course_name', 'course_type')
        }),
        ('Scheduling Configuration', {
            'fields': ('hours_per_week', 'max_continuous_hours', 'priority'),
        }),
        ('Lab Resources (for LAB courses only)', {
            'fields': ('lab_rooms',),
        }),
        ('Instructors', {
            'fields': ('instructors',),
        }),
    )
    
    exclude = ('max_numb_students',)

class SpecialPeriodAdmin(admin.ModelAdmin):
    list_display = ('period_type', 'year', 'hours_per_week', 'continuous_hours', 'instructor', 'applies_to_sections')
    list_filter = ('period_type', 'year')
    search_fields = ('period_type', 'year__year_name')
    list_editable = ('hours_per_week', 'continuous_hours', 'instructor')
    ordering = ('year', 'period_type')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('period_type', 'year'),
            'description': 'This special period will automatically apply to all 3 sections in the selected year'
        }),
        ('Time Configuration', {
            'fields': ('hours_per_week', 'continuous_hours'),
            'description': 'Hours per week: total hours. Continuous hours: block size (e.g., 2 for 2-hour Training blocks)'
        }),
        ('Instructor (Optional)', {
            'fields': ('instructor',),
            'description': 'Leave empty if no specific instructor is assigned'
        }),
    )
    
    def applies_to_sections(self, obj):
        return "Sections 1, 2, 3"
    applies_to_sections.short_description = 'Applies To'
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['hours_per_week'].initial = 1
        form.base_fields['continuous_hours'].initial = 1
        return form


class YearAdmin(admin.ModelAdmin):
    list_display = ('year_name', 'get_lunch_time', 'get_period_count')
    fields = ('year_name', 'lunch_period', 'courses')
    
    def get_lunch_time(self, obj):
        time_slots = [
            '8:45-9:45', '9:45-10:35', '10:35-11:25', '11:25-12:15',
            '12:15-1:05', '1:05-1:55', '1:55-2:45', '2:45-3:35'
        ]
        if 1 <= obj.lunch_period <= len(time_slots):
            return f"Period {obj.lunch_period}: {time_slots[obj.lunch_period-1]}"
        return "Not set"
    get_lunch_time.short_description = 'Lunch Break'
    
    def get_period_count(self, obj):
        return "7 periods"
    get_period_count.short_description = 'Class Periods'


admin.site.register(Course, CourseAdmin)
admin.site.register(Department)
admin.site.register(Year, YearAdmin)
admin.site.register(CourseInstructorAssignment)
admin.site.register(GeneratedTimetable)
admin.site.register(TimetableEntry)
admin.site.register(SpecialPeriod, SpecialPeriodAdmin)


