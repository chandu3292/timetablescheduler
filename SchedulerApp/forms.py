from django.forms import ModelForm
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import (
    Instructor, LabRoom, Course, Department, Year, MeetingTime,
    CourseInstructorAssignment, SpecialPeriod, LabBatchAssignment,
)


class UserLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'UserName', 'id': 'id_username'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'Password', 'id': 'id_password'
    }))


class InstructorForm(ModelForm):
    class Meta:
        model = Instructor
        labels = {'uid': 'Instructor ID', 'name': 'Instructor Name'}
        fields = ['uid', 'name']


class LabRoomForm(ModelForm):
    class Meta:
        model = LabRoom
        labels = {'lab_name': 'Lab Room Name'}
        fields = ['lab_name', 'seating_capacity']


class CourseForm(ModelForm):
    class Meta:
        model = Course
        labels = {'max_numb_students': 'Maximum students'}
        fields = [
            'course_number', 'course_name', 'max_numb_students',
            'hours_per_week', 'priority', 'max_continuous_hours',
            'course_type', 'split_into_batches',
            'instructors', 'lab_rooms',
        ]


class DepartmentForm(ModelForm):
    class Meta:
        model = Department
        fields = ['dept_name']


class YearForm(ModelForm):
    class Meta:
        model = Year
        fields = ['year_name', 'courses']


class MeetingTimeForm(ModelForm):
    class Meta:
        model = MeetingTime
        fields = ['pid', 'time', 'day', 'year']
        widgets = {
            'pid':  forms.TextInput(),
            'time': forms.Select(),
            'day':  forms.Select(),
        }


class CourseInstructorAssignmentForm(ModelForm):
    class Meta:
        model = CourseInstructorAssignment
        fields = ['course', 'year', 'section_number', 'instructors']


class SpecialPeriodForm(ModelForm):
    class Meta:
        model = SpecialPeriod
        fields = ['period_type', 'hours_per_week', 'continuous_hours', 'instructor', 'year']


class LabBatchAssignmentForm(ModelForm):
    class Meta:
        model = LabBatchAssignment
        fields = [
            'year', 'section_number', 'batch', 'session_number',
            'course', 'paired_course', 'lab_room', 'instructors',
        ]
