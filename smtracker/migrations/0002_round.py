# Generated by Django 5.2 on 2025-04-04 21:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('smtracker', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Round',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ident', models.CharField(max_length=10, unique=True)),
                ('name', models.CharField(max_length=100)),
                ('order_index', models.IntegerField(unique=True)),
            ],
        ),
    ]
