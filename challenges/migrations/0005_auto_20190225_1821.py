# Generated by Django 2.1.7 on 2019-02-25 21:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('challenges', '0004_challenge_published'),
    ]

    operations = [
        migrations.AlterField(
            model_name='challenge',
            name='function_name',
            field=models.CharField(blank=True, max_length=50),
        ),
    ]
