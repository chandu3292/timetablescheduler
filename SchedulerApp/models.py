from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

TIME_SLOTS = (
    ('8:45 - 9:45',   '8:45 - 9:45'),
    ('9:45 - 10:35',  '9:45 - 10:35'),
    ('10:35 - 11:25', '10:35 - 11:25'),
    ('11:25 - 12:15', '11:25 - 12:15'),
    # --- Lunch break 12:15 - 1:05 ---
    ('1:05 - 1:55',   '1:05 - 1:55'),
    ('1:55 - 2:45',   '1:55 - 2:45'),
    ('2:45 - 3:35',   '2:45 - 3:35'),
)

DAYS_OF_WEEK = (
    ('Monday',    'Monday'),
    ('Tuesday',   'Tuesday'),
    ('Wednesday', 'Wednesday'),
    ('Thursday',  'Thursday'),
    ('Friday',    'Friday'),
    ('Saturday',  'Saturday'),
)

COURSE_TYPES = (
    ('THEORY',   'Theory'),
    ('LAB',      'Lab'),
    ('ELECTIVE', 'Elective'),
)

SPECIAL_PERIOD_TYPES = (
    ('Counseling',     'Counseling'),
    ('Training',       'Training'),
    ('Sports/Library', 'Sports/Library'),
)

DESIGNATION_CHOICES = (
    ('Professor',           'Professor'),
    ('Associate Professor', 'Associate Professor'),
    ('Assistant Professor', 'Assistant Professor'),
)


class Instructor(models.Model):
    uid         = models.CharField(max_length=10)
    name        = models.CharField(max_length=50)
    designation = models.CharField(max_length=25, choices=DESIGNATION_CHOICES,
                                   default='Assistant Professor')

    def __str__(self):
        return f'{self.uid} {self.name}'


class LabRoom(models.Model):
    lab_name         = models.CharField(max_length=50)
    seating_capacity = models.IntegerField(default=0)

    def __str__(self):
        return self.lab_name


class Course(models.Model):
    course_number        = models.CharField(max_length=15, primary_key=True)
    course_name          = models.CharField(max_length=60)
    max_numb_students    = models.CharField(max_length=65, blank=True, default='')
    hours_per_week       = models.IntegerField(default=0,
                               validators=[MinValueValidator(0)],
                               help_text='Contact hours per week')
    priority             = models.IntegerField(default=3,
                               help_text='Lower = scheduled earlier')
    max_continuous_hours = models.IntegerField(default=2,
                               validators=[MinValueValidator(1)],
                               help_text='Max consecutive hours per day')
    course_type          = models.CharField(max_length=10, choices=COURSE_TYPES, default='THEORY')
    split_into_batches   = models.BooleanField(default=False,
                               help_text='Divide section into B1/B2 batches for this lab')
    instructors          = models.ManyToManyField(Instructor, blank=True)
    lab_rooms            = models.ManyToManyField(LabRoom, blank=True,
                               help_text='Allowed lab rooms for this course')

    def __str__(self):
        return f'{self.course_number} {self.course_name}'


class Department(models.Model):
    dept_name = models.CharField(max_length=50)

    def __str__(self):
        return self.dept_name


class Year(models.Model):
    year_name = models.CharField(max_length=20)
    courses   = models.ManyToManyField(Course, blank=True)

    def __str__(self):
        return self.year_name


class MeetingTime(models.Model):
    pid  = models.CharField(max_length=10, primary_key=True)
    time = models.CharField(max_length=50, choices=TIME_SLOTS, default='8:45 - 9:45')
    day  = models.CharField(max_length=15, choices=DAYS_OF_WEEK)
    year = models.ForeignKey(Year, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f'{self.pid} {self.day} {self.time}'


class CourseInstructorAssignment(models.Model):
    """Instructor(s) assigned to a course for a specific year+section."""
    course         = models.ForeignKey(Course, on_delete=models.CASCADE)
    year           = models.ForeignKey(Year, on_delete=models.CASCADE)
    section_number = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(3)]
    )
    instructors    = models.ManyToManyField(Instructor, blank=True)

    class Meta:
        unique_together = ['year', 'section_number', 'course']

    def __str__(self):
        return f'{self.year} S{self.section_number} {self.course}'


class SpecialPeriod(models.Model):
    """A special period (Counseling / Training / Sports-Library) for a year."""
    period_type      = models.CharField(max_length=20, choices=SPECIAL_PERIOD_TYPES)
    hours_per_week   = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    continuous_hours = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    instructor       = models.ForeignKey(Instructor, on_delete=models.SET_NULL,
                           null=True, blank=True)
    year             = models.ForeignKey(Year, on_delete=models.CASCADE)

    class Meta:
        unique_together = ['period_type', 'year']

    def __str__(self):
        return f'{self.year} {self.period_type}'


class GeneratedTimetable(models.Model):
    year            = models.ForeignKey(Year, on_delete=models.CASCADE)
    generated_at    = models.DateTimeField(auto_now=True)
    fitness_score   = models.FloatField(default=0.0)
    generation_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-generated_at']

    def __str__(self):
        return f'Timetable for {self.year} (fitness={self.fitness_score:.4f})'


class TimetableEntry(models.Model):
    """One scheduled hour in a generated timetable."""
    timetable      = models.ForeignKey(GeneratedTimetable, on_delete=models.CASCADE,
                         related_name='entries')
    year           = models.ForeignKey(Year, on_delete=models.CASCADE)
    section_number = models.IntegerField(default=1)
    course         = models.ForeignKey(Course, on_delete=models.CASCADE)
    instructor     = models.ForeignKey(Instructor, on_delete=models.SET_NULL,
                         null=True, blank=True,
                         related_name='timetable_entries')
    lab_room       = models.ForeignKey(LabRoom, on_delete=models.SET_NULL,
                         null=True, blank=True)
    meeting_time   = models.ForeignKey(MeetingTime, on_delete=models.CASCADE)
    batch          = models.CharField(max_length=10, default='FULL',
                         help_text="FULL | B1 | B2 ...")
    evaluators     = models.ManyToManyField(Instructor, blank=True,
                         related_name='evaluator_entries',
                         help_text='Lab evaluators (Assistant Professors only)')

    def __str__(self):
        return (f'{self.year} S{self.section_number} {self.course} '
                f'{self.meeting_time.day} {self.meeting_time.time}')


class LabBatchAssignment(models.Model):
    """Defines how a split-into-batches lab is scheduled per section."""
    year           = models.ForeignKey(Year, on_delete=models.CASCADE)
    section_number = models.IntegerField(default=1)
    batch          = models.CharField(max_length=10)          # B1, B2, …
    session_number = models.IntegerField(default=1)
    course         = models.ForeignKey(Course, on_delete=models.CASCADE,
                         related_name='batch_assignments')
    paired_course  = models.ForeignKey(Course, on_delete=models.SET_NULL,
                         null=True, blank=True,
                         related_name='paired_batch_assignments')
    lab_room       = models.ForeignKey(LabRoom, on_delete=models.CASCADE)
    instructors    = models.ManyToManyField(Instructor, blank=True)

    def __str__(self):
        return (f'{self.year} S{self.section_number} {self.batch} '
                f'{self.course}')
