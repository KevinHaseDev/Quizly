"""Migration: add question_title, question_options, and answer fields to Question."""

from django.db import migrations, models


def copy_existing_question_titles(apps, schema_editor):
    """Copy the legacy title field into the new question_title field for existing rows."""
    question_model = apps.get_model('quiz_app', 'Question')
    for question in question_model.objects.all().iterator():
        question.question_title = question.title
        question.save(update_fields=['question_title'])


class Migration(migrations.Migration):

    dependencies = [
        ('quiz_app', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='question_title',
            field=models.CharField(default='Generated Question', max_length=255),
        ),
        migrations.AddField(
            model_name='question',
            name='question_options',
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name='question',
            name='answer',
            field=models.CharField(default='', max_length=255),
        ),
        migrations.RunPython(copy_existing_question_titles, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='question',
            name='title',
        ),
        migrations.RemoveField(
            model_name='question',
            name='description',
        ),
    ]
