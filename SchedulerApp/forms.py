from django.forms import ModelForm
from .models import *
from django import forms
from django.contrib.auth.forms import AuthenticationForm


class UserLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(UserLoginForm, self).__init__(*args, **kwargs)

    username = forms.CharField(widget=forms.TextInput(
        attrs={
            'class': 'form-control',
            'type': 'text',
            'placeholder': 'UserName',
            'id': 'id_username'
        }))
    password = forms.CharField(widget=forms.PasswordInput(
        attrs={
            'class': 'form-control',
            'type': 'password',
            'placeholder': 'Password',
            'id': 'id_password',
        }))


class LabRoomForm(ModelForm):
    class Meta:
        model = LabRoom
        fields = ['lab_name', 'seating_capacity']
        labels = {
            'lab_name': 'Lab Room Name',
            'seating_capacity': 'Seating Capacity'
        }

class InstructorForm(ModelForm):
    class Meta:
        model = Instructor
        labels = {'uid': 'Instructor ID', 'name': 'Instructor Name'}
        fields = ['uid', 'name']


class MeetingTimeForm(ModelForm):
    class Meta:
        model = MeetingTime
        fields = ['year', 'time', 'day']   
        widgets = {
            'year': forms.Select(),               
            'time': forms.Select(),
            'day': forms.Select(),
        }



class CourseForm(ModelForm):
    year = forms.ModelChoiceField(
        queryset=Year.objects.all(),
        required=True,
        label='Year'
    )
    
    # For THEORY/ELECTIVE courses - single instructor per section
    section_1_instructor = forms.ModelChoiceField(
        queryset=Instructor.objects.all(),
        required=False,
        label='Section 1 Instructor'
    )
    
    section_2_instructor = forms.ModelChoiceField(
        queryset=Instructor.objects.all(),
        required=False,
        label='Section 2 Instructor'
    )
    
    section_3_instructor = forms.ModelChoiceField(
        queryset=Instructor.objects.all(),
        required=False,
        label='Section 3 Instructor'
    )
    
    # For LAB courses - multiple instructors per section
    section_1_lab_instructors = forms.ModelMultipleChoiceField(
        queryset=Instructor.objects.all(),
        required=False,
        label='Section 1 Lab Instructors',
        widget=forms.SelectMultiple(attrs={'size': '8'})
    )
    
    section_2_lab_instructors = forms.ModelMultipleChoiceField(
        queryset=Instructor.objects.all(),
        required=False,
        label='Section 2 Lab Instructors',
        widget=forms.SelectMultiple(attrs={'size': '8'})
    )
    
    section_3_lab_instructors = forms.ModelMultipleChoiceField(
        queryset=Instructor.objects.all(),
        required=False,
        label='Section 3 Lab Instructors',
        widget=forms.SelectMultiple(attrs={'size': '8'})
    )
    
    lab_rooms = forms.ModelMultipleChoiceField(
        queryset=LabRoom.objects.all(),
        required=False,
        label='Lab Rooms (for LAB courses only)',
        widget=forms.SelectMultiple(attrs={'size': '6'})
    )
    
    class Meta:
        model = Course
        labels = {
            'course_type': 'Course Type', 
            'hours_per_week': 'Hours Per Week', 
            'max_continuous_hours': 'Maximum Continuous Hours', 
            'priority': 'Priority'
        }
        fields = [
            'course_number', 'course_name',
            'section_1_instructor', 'section_2_instructor', 'section_3_instructor',
            'section_1_lab_instructors', 'section_2_lab_instructors', 'section_3_lab_instructors',
            'course_type', 'lab_rooms', 'hours_per_week', 'max_continuous_hours', 'priority'
        ]
        
class YearForm(ModelForm):
    class Meta:
        model = Year
        fields = ['year_name', 'courses']
        labels = {
            'year_name': 'Year',
            'courses': 'Courses for this Year'
        }
        widgets = {
            'courses': forms.CheckboxSelectMultiple(),
        }



class DepartmentForm(ModelForm):
    class Meta:
        model = Department
        labels = {'dept_name': 'Department name'}
        fields = ['dept_name', 'courses']


class SpecialPeriodForm(ModelForm):
    class Meta:
        model = SpecialPeriod
        fields = ['period_type', 'year', 'hours_per_week', 'continuous_hours', 'instructor']
        labels = {
            'period_type': 'Period Type',
            'year': 'Year (Applies to all 3 sections)',
            'hours_per_week': 'Hours Per Week',
            'continuous_hours': 'Continuous Hours',
            'instructor': 'Instructor (Optional)'
        }
        widgets = {
            'period_type': forms.Select(),
            'year': forms.Select(),
            'hours_per_week': forms.NumberInput(attrs={'min': 1, 'max': 5}),
            'continuous_hours': forms.NumberInput(attrs={'min': 1, 'max': 5}),
            'instructor': forms.Select()
        }
