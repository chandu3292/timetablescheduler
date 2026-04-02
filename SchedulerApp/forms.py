from django.forms import ModelForm
from .models import *
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User


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


class UnifiedLoginForm(forms.Form):
    """Unified login form with role selection"""
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('instructor', 'Instructor'),
    ]
    
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'id_role'
        }),
        label='Login As'
    )
    
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'type': 'text',
            'placeholder': 'Username / Email',
            'id': 'id_username'
        }),
        label='Username / Email'
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'type': 'password',
            'placeholder': 'Password',
            'id': 'id_password',
        }),
        label='Password'
    )


class LabRoomForm(ModelForm):
    class Meta:
        model = LabRoom
        fields = ['lab_name', 'seating_capacity']
        labels = {
            'lab_name': 'Lab Room Name',
            'seating_capacity': 'Seating Capacity'
        }

class InstructorForm(ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text="Leave blank to keep existing password. Set password for new instructors."
    )
    
    designation = forms.ChoiceField(
        choices=[
            ('PROF', 'Professor'),
            ('ASSOC_PROF', 'Associate Professor'),
            ('ASST_PROF', 'Assistant Professor'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True,
        label='Designation',
        help_text='Professor, Associate Professor, or Assistant Professor'
    )
    
    class Meta:
        model = Instructor
        fields = ['uid', 'name', 'email', 'designation', 'department']
        labels = {
            'uid': 'Instructor ID',
            'name': 'Instructor Name',
            'email': 'Email ID',
            'department': 'Department Code'
        }
        widgets = {
            'uid': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def save(self, commit=True):
        instructor = super().save(commit=False)
        password = self.cleaned_data.get('password')
        
        if commit:
            instructor.save()
            # Create or update associated User account
            if not instructor.user:
                user = User.objects.create_user(
                    username=instructor.email,
                    email=instructor.email,
                    password=password if password else 'defaultpassword123'
                )
                instructor.user = user
                instructor.save()
            elif password:
                instructor.user.set_password(password)
                instructor.user.save()
        
        return instructor


class InstructorLoginForm(forms.Form):
    """Instructor login form using email and password"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email ID',
            'id': 'id_email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'id': 'id_password'
        })
    )


class InstructorPriorityForm(ModelForm):
    """Form for instructors to set their period priorities for a specific day"""
    class Meta:
        model = InstructorPriority
        fields = ['day', 'period_1_priority', 'period_2_priority', 'period_3_priority', 
                  'period_4_priority', 'period_5_priority', 'period_6_priority', 'period_7_priority']
        widgets = {
            'day': forms.Select(attrs={'class': 'form-control'}),
            'period_1_priority': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 7}),
            'period_2_priority': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 7}),
            'period_3_priority': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 7}),
            'period_4_priority': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 7}),
            'period_5_priority': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 7}),
            'period_6_priority': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 7}),
            'period_7_priority': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 7}),
        }
        labels = {
            'day': 'Day of Week',
            'period_1_priority': 'Period 1 Priority (1=highest, 7=lowest)',
            'period_2_priority': 'Period 2 Priority',
            'period_3_priority': 'Period 3 Priority',
            'period_4_priority': 'Period 4 Priority',
            'period_5_priority': 'Period 5 Priority',
            'period_6_priority': 'Period 6 Priority',
            'period_7_priority': 'Period 7 Priority',
        }


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
