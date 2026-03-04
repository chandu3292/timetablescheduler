from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import AbstractUser
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


class LabRoom(models.Model):
    lab_name = models.CharField(max_length=50)  # Lab-1, Lab-2, Lab-3
    seating_capacity = models.IntegerField(default=30)

    def __str__(self):
        return self.lab_name



class Instructor(models.Model):
    uid = models.CharField(max_length=6)
    name = models.CharField(max_length=25)

    def __str__(self):
        return f'{self.uid} {self.name}'
    
class Course(models.Model):
    course_number = models.CharField(max_length=5, primary_key=True)
    course_name = models.CharField(max_length=40)
    max_numb_students = models.CharField(max_length=65)
    instructors = models.ManyToManyField(Instructor)

    course_type = models.CharField(max_length=10, choices=COURSE_TYPE, default='THEORY')
    lab_rooms = models.ManyToManyField(LabRoom, blank=True)

    hours_per_week = models.IntegerField(default=3)
    max_continuous_hours = models.IntegerField(default=1)
    priority = models.IntegerField(default=1)

    def __str__(self):
        return f'{self.course_number} {self.course_name}'
class Year(models.Model):
    year_name = models.CharField(max_length=20)  # e.g. "2nd Year"
    courses = models.ManyToManyField(Course)

    def __str__(self):
        return self.year_name


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
    instructors = models.ManyToManyField(Instructor)  # Changed to ManyToMany for multiple instructors per section

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


class TimetableEntry(models.Model):
    """Individual class entry in the timetable"""
    timetable = models.ForeignKey(GeneratedTimetable, on_delete=models.CASCADE, related_name='entries')
    year = models.ForeignKey(Year, on_delete=models.CASCADE)
    section_number = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(3)])  # 1, 2, or 3
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE)
    lab_room = models.ForeignKey(LabRoom, on_delete=models.CASCADE, null=True, blank=True)
    meeting_time = models.ForeignKey(MeetingTime, on_delete=models.CASCADE)
    
    class Meta:
        ordering = ['year', 'section_number', 'meeting_time__day', 'meeting_time__time']
        
    def __str__(self):
        room_info = self.lab_room if self.lab_room else None
        return f"{self.year} Section {self.section_number} - {self.course.course_name} @ {self.meeting_time.day} {self.meeting_time.time}"
    
    def get_room(self):
        """Returns the appropriate room (lab or regular)"""
        return self.lab_room
