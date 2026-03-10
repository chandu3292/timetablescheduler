from django.contrib import admin
from .models import *
from .models import CourseInstructorAssignment, GeneratedTimetable, TimetableEntry, LabBatchAssignment

admin.site.register(LabRoom)
admin.site.register(Instructor)
admin.site.register(MeetingTime)

class CourseAdmin(admin.ModelAdmin):
    list_display = ('course_number', 'course_name', 'course_type', 'split_into_batches', 'hours_per_week', 'priority')
    list_filter = ('course_type', 'split_into_batches')
    search_fields = ('course_number', 'course_name')
    list_editable = ('split_into_batches',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('course_number', 'course_name', 'course_type')
        }),
        ('Scheduling Configuration', {
            'fields': ('hours_per_week', 'max_continuous_hours', 'priority'),
        }),
        ('Batch Splitting', {
            'fields': ('split_into_batches',),
            'description': '✅ Check this box for labs that split sections into Batch 1 (B1) and Batch 2 (B2) with rotation. After checking this, you can create Lab Batch Assignments to define which batch gets which instructor/lab for each session.'
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

admin.site.register(Course, CourseAdmin)
admin.site.register(Department)
admin.site.register(Year)
admin.site.register(CourseInstructorAssignment)
admin.site.register(GeneratedTimetable)
admin.site.register(TimetableEntry)
admin.site.register(SpecialPeriod, SpecialPeriodAdmin)


class LabBatchAssignmentAdmin(admin.ModelAdmin):
    list_display = ('year', 'section_number', 'course', 'batch', 'session_number', 'get_instructors', 'lab_room', 'paired_course')
    list_filter = ('year', 'section_number', 'batch', 'session_number')
    search_fields = ('course__course_name', 'instructors__name', 'lab_room__lab_name')
    ordering = ('year', 'section_number', 'course', 'session_number', 'batch')
    
    fieldsets = (
        ('Assignment Details', {
            'fields': ('year', 'section_number', 'course', 'batch', 'session_number'),
            'description': 'Define which batch gets which resources for each session. The scheduler will automatically find available time slots.'
        }),
        ('Resources', {
            'fields': ('instructors', 'lab_room'),
            'description': 'Select one or more instructors for this batch in this session'
        }),
        ('Pairing (Optional)', {
            'fields': ('paired_course',),
            'description': 'The other lab that runs simultaneously (e.g., IoT pairs with Cryptography)'
        }),
    )
    
    def get_instructors(self, obj):
        return ", ".join([inst.name for inst in obj.instructors.all()])
    get_instructors.short_description = 'Instructors'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('year', 'course', 'lab_room', 'paired_course').prefetch_related('instructors')

admin.site.register(LabBatchAssignment, LabBatchAssignmentAdmin)