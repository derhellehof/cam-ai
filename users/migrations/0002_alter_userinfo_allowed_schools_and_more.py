# Generated by Django 4.2.1 on 2023-08-06 15:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userinfo',
            name='allowed_schools',
            field=models.IntegerField(default=3),
        ),
        migrations.AlterField(
            model_name='userinfo',
            name='allowed_streams',
            field=models.IntegerField(default=2),
        ),
    ]
