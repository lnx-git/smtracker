# Generated by Django 5.2 on 2025-04-25 16:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('smtracker', '0017_alter_match_schedule_time'),
    ]

    operations = [
        migrations.AlterField(
            model_name='match',
            name='result_robot1_points',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='match',
            name='result_robot2_points',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
