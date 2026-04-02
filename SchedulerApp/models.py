from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import AbstractUser, User
from django.db.models.signals import post_save, post_delete


TIME_SLOTS = (
    ('8:45 - 9:45'  , '8:45 - 9:45'),
    ('9:45 - 10:35', '9:45 - 10:35'),
    ('10:35 - 11:25', '10:35 - 11:25'),
    ('11:25 - 12:15'  , '11:25 - 12:15'),
    ('12:15 - 1:05', '12:15 - 1:05'),
    ('1:05 - 1:55'  , '1:05 - 1:55'),
    ('1:55 - 2:45'  , '1:55 - 2:45'),
    ('2:45 - 3:35'  , '2:45 - 3:35'),
    
)

# TIME_SLOTS = (
#     ('8:40 - 10:30', '9:30 - 10:30'),
#     ('10:30 - 11:30', '10:30 - 11:30'),
#     ('11:30 - 12:30', '11:30 - 12:30'),
#     ('12:30 - 1:30', '12:30 - 1:30'),
#     ('2:30 - 3:30', '2:30 - 3:30'),
#     ('3:30 - 4:30', '3:30 - 4:30'),
#     ('4:30 - 5:30', '4:30 - 5:30'),
# )

DAYS_OF_WEEK = (
    ('Monday', 'Monday'),
    ('Tuesday', 'Tuesday'),
    ('Wednesday', 'Wednesday'),
    ('Thursday', 'Thursday'),
    ('Friday', 'Friday'),
    ('Saturday', 'Saturday'),
)
    # ('Saturday', 'Saturday'),
    
COURSE_TYPE = (
    ('THEORY','THEORY'),
    ('LAB','LAB'),
    ('ELECTIVE','ELECTIVE'),
)

SPECIAL_PERIOD_TYPE = (
    ('Counseling', 'Counseling'),
    ('Training', 'Training'),
    ('Sports', 'Sports'),
    ('Library', 'Library'),
)


DESIGNATION_CHOICES = (
    ('PROF', 'Professor'),
    ('ASSOC_PROF', 'Associate Professor'),
    ('ASST_PROF', 'Assistant Professor'),
)

DAYS_OF_WEEK_LIST = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']


class LabRoom(models.Model):
    lab_name = models.CharField(max_length=50)  # Lab-1, Lab-2, Lab-3
    seating_capacity = models.IntegerField(default=30)

    def __str__(self):
        return self.lab_name



class Instructor(models.Model):
    uid = models.CharField(max_length=6)
    name = models.CharField(max_length=25)
    email = models.EmailField(unique=True, blank=True, null=True, help_text="Email ID for login")
    department = models.CharField(max_length=10, null=True, blank=True, help_text="Department code: IT, EC, ME, etc.")
    designation = models.CharField(max_length=20, choices=DESIGNATION_CHOICES, default='ASST_PROF', help_text="Professor, Associate Professor, or Assistant Professor")
    
    # Link to Django User for authentication
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='instructor_profile')

    def __str__(self):
        return f'{self.uid} {self.name}'
    
    def is_assistant_professor(self):
        """Check if instructor is an Assistant Professor (eligible to be evaluator)"""
        return self.designation == 'ASST_PROF'


class InstructorPriority(models.Model):
    """
    Stores instructor preferences for each period of each day.
    Priority ranges from 1 (highest) to 7 (lowest).
    Instructors must set priorities for all 7 periods for each working day.
    """
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE, related_name='priorities')
    day = models.CharField(max_length=15, choices=DAYS_OF_WEEK)
    
    # Period priorities (1 = highest preference, 7 = lowest preference)
    period_1_priority = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(7)], default=1)
    period_2_priority = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(7)], default=2)
    period_3_priority = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(7)], default=3)
    period_4_priority = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(7)], default=4)
    period_5_priority = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(7)], default=5)
    period_6_priority = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(7)], default=6)
    period_7_priority = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(7)], default=7)
    
    class Meta:
        unique_together = ['instructor', 'day']
        ordering = ['instructor', 'day']
    
    def __str__(self):
        return f"{self.instructor.name} - {self.day} priorities"
    
    def get_period_priority(self, period_number):
        """Get priority for a specific period (1-7)"""
        priority_map = {
            1: self.period_1_priority,
            2: self.period_2_priority,
            3: self.period_3_priority,
            4: self.period_4_priority,
            5: self.period_5_priority,
            6: self.period_6_priority,
            7: self.period_7_priority,
        }
        return priority_map.get(period_number, 7)  # Default to lowest priority if invalid
    
    def set_period_priority(self, period_number, priority_value):
        """Set priority for a specific period"""
        if period_number == 1:
            self.period_1_priority = priority_value
        elif period_number == 2:
            self.period_2_priority = priority_value
        elif period_number == 3:
            self.period_3_priority = priority_value
        elif period_number == 4:
            self.period_4_priority = priority_value
        elif period_number == 5:
            self.period_5_priority = priority_value
        elif period_number == 6:
            self.period_6_priority = priority_value
        elif period_number == 7:
            self.period_7_priority = priority_value

    
class Course(models.Model):
    course_number = models.CharField(max_length=10, primary_key=True)
    course_name = models.CharField(max_length=40)
    max_numb_students = models.CharField(max_length=65)
    instructors = models.ManyToManyField(Instructor)

    course_type = models.CharField(max_length=10, choices=COURSE_TYPE, default='THEORY')
    lab_rooms = models.ManyToManyField(LabRoom, blank=True)

    hours_per_week = models.IntegerField(default=3)
    max_continuous_hours = models.IntegerField(default=1)
    priority = models.IntegerField(default=1)
    
    # Department code for the course (determines which evaluators can be assigned)
    dept_code = models.CharField(max_length=10, null=True, blank=True, help_text="Department code: IT, EC, ME, etc.")
    


    def __str__(self):
        return f'{self.course_number} {self.course_name}'
class Year(models.Model):
    year_name = models.CharField(max_length=20)  # e.g. "2nd Year"
    courses = models.ManyToManyField(Course)
    lunch_period = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(8)],
        help_text="Which time slot is lunch break (1-8). 1st year=4 (11:25-12:15), Others=5 (12:15-1:05)"
    )

    def __str__(self):
        return self.year_name
    
    def get_available_periods(self):
        """Returns list of (index, time_slot) tuples excluding lunch break"""
        available = []
        for i, slot in enumerate(TIME_SLOTS, start=1):
            if i != self.lunch_period:
                available.append((i, slot[1]))
        return available


class MeetingTime(models.Model):
    pid = models.CharField(max_length=4, primary_key=True)

    year = models.ForeignKey(
    Year,
    on_delete=models.CASCADE,
    related_name='meeting_times',
    null=True,      # 👈 add this
    blank=True      # 👈 add this
)


    day = models.CharField(max_length=15, choices=DAYS_OF_WEEK)
    time = models.CharField(max_length=50, choices=TIME_SLOTS)

    def __str__(self):
        return f'{self.year} | {self.day} | {self.time}'

class Department(models.Model):
    dept_name = models.CharField(max_length=50)
    courses = models.ManyToManyField(Course)

    @property
    def get_courses(self):
        return self.courses

    def __str__(self):
        return self.dept_name


class CourseInstructorAssignment(models.Model):
    year = models.ForeignKey(Year, on_delete=models.CASCADE)
    section_number = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(3)])  # 1, 2, or 3
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    main_instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE, related_name='main_courses', null=True, blank=True, help_text="Primary instructor whose availability determines scheduling")
    instructors = models.ManyToManyField(Instructor)  # Changed to ManyToMany for multiple instructors per section (includes main + evaluators)

    class Meta:
        unique_together = ['year', 'section_number', 'course']

    def __str__(self):
        instructor_names = ", ".join([str(i) for i in self.instructors.all()])
        return f"{self.year} Section {self.section_number} - {self.course} → {instructor_names}"





class GeneratedTimetable(models.Model):
    """Stores generated timetables for each year"""
    year = models.OneToOneField(Year, on_delete=models.CASCADE, related_name='generated_timetable')
    generated_at = models.DateTimeField(auto_now=True)
    fitness_score = models.FloatField(default=0.0)
    generation_count = models.IntegerField(default=0)
    
    def __str__(self):
        return f"Timetable for {self.year.year_name} (Fitness: {self.fitness_score:.2%})"


class SpecialPeriod(models.Model):
    """Special periods like counseling, training, sports/library - applies to all sections in a year"""
    period_type = models.CharField(max_length=20, choices=SPECIAL_PERIOD_TYPE)
    year = models.ForeignKey(Year, on_delete=models.CASCADE)
    hours_per_week = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    continuous_hours = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    instructor = models.ForeignKey(Instructor, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ['period_type', 'year']
        ordering = ['year', 'period_type']
    
    def __str__(self):
        return f"{self.period_type} - {self.year} (All Sections)"


class TimetableEntry(models.Model):
    """Individual class entry in the timetable"""
    timetable = models.ForeignKey(GeneratedTimetable, on_delete=models.CASCADE, related_name='entries')
    year = models.ForeignKey(Year, on_delete=models.CASCADE)
    section_number = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(3)])  # 1, 2, or 3
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE, null=True, blank=True)
    lab_room = models.ForeignKey(LabRoom, on_delete=models.CASCADE, null=True, blank=True)
    meeting_time = models.ForeignKey(MeetingTime, on_delete=models.CASCADE)
    
    
    # Instructor role (for labs with multiple instructors)
    is_evaluator = models.BooleanField(default=False, help_text="True if this instructor is an evaluator, False if main instructor")
    
    class Meta:
        ordering = ['year', 'section_number', 'meeting_time__day', 'meeting_time__time']
        
    def __str__(self):
        role = " (Evaluator)" if self.is_evaluator else ""
        room_info = self.lab_room if self.lab_room else None
        return f"{self.year} Section {self.section_number} - {self.course.course_name} @ {self.meeting_time.day} {self.meeting_time.time}{role}"
    
    def get_room(self):
        """Returns the appropriate room (lab or regular)"""
        return self.lab_room
