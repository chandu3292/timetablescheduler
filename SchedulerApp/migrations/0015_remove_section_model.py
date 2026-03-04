# Generated manually on 2026-02-19

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('SchedulerApp', '0014_auto_20260219_1744'),
    ]

    operations = [
        # Remove section ForeignKey from CourseInstructorAssignment and add year + section_number
        migrations.RemoveField(
            model_name='courseinstructorassignment',
            name='section',
        ),
        migrations.AddField(
            model_name='courseinstructorassignment',
            name='year',
            field=models.ForeignKey(default=1, on_delete=models.deletion.CASCADE, to='SchedulerApp.year'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='courseinstructorassignment',
            name='section_number',
            field=models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(3)]),
            preserve_default=False,
        ),
        migrations.AlterUniqueTogether(
            name='courseinstructorassignment',
            unique_together={('year', 'section_number', 'course')},
        ),
        
        # Remove section ForeignKey from TimetableEntry and add year + section_number
        migrations.RemoveField(
            model_name='timetableentry',
            name='section',
        ),
        migrations.AddField(
            model_name='timetableentry',
            name='year',
            field=models.ForeignKey(default=1, on_delete=models.deletion.CASCADE, to='SchedulerApp.year'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='timetableentry',
            name='section_number',
            field=models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(3)]),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name='timetableentry',
            options={'ordering': ['year', 'section_number', 'meeting_time__day', 'meeting_time__time']},
        ),
        
        # Delete the Section model
        migrations.DeleteModel(
            name='Section',
        ),
    ]
