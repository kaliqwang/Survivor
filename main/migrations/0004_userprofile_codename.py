# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-11-06 06:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_player_num_kills_copy'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='codename',
            field=models.CharField(default='my_codename', max_length=50),
            preserve_default=False,
        ),
    ]