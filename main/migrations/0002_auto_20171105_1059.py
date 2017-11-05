# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-11-05 15:59
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ServerState',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('elimination_in_progress', models.BooleanField(default=False)),
                ('revert_in_progress', models.BooleanField(default=False)),
            ],
            options={
                'verbose_name_plural': 'server state',
            },
        ),
        migrations.RemoveField(
            model_name='elimination',
            name='killer',
        ),
        migrations.AddField(
            model_name='elimination',
            name='is_reverse',
            field=models.BooleanField(default=False),
        ),
    ]