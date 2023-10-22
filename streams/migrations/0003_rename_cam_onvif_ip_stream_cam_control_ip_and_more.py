# Generated by Django 4.2.5 on 2023-10-17 17:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('streams', '0002_stream_cam_onvif_adminpasswd_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='stream',
            old_name='cam_onvif_ip',
            new_name='cam_control_ip',
        ),
        migrations.RenameField(
            model_name='stream',
            old_name='cam_onvif_adminpasswd',
            new_name='cam_control_passwd',
        ),
        migrations.RenameField(
            model_name='stream',
            old_name='cam_onvif_port',
            new_name='cam_control_port',
        ),
        migrations.RenameField(
            model_name='stream',
            old_name='cam_onvif_adminuser',
            new_name='cam_control_user',
        ),
        migrations.AddField(
            model_name='stream',
            name='cam_control_mode',
            field=models.IntegerField(choices=[(0, 'Url'), (1, 'ISAPI'), (2, 'ONVIF')], default=0),
        ),
    ]
