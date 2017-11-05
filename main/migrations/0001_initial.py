# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-11-04 21:17
from __future__ import unicode_literals

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import main.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Elimination',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('valid', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ('-pk',),
            },
        ),
        migrations.CreateModel(
            name='Game',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_start', models.DateField(default=main.models.default_start_date, help_text='Game starts at midnight')),
                ('date_end', models.DateField(blank=True, null=True)),
                ('date_close', models.DateField(blank=True, null=True)),
                ('date_last_quota_check', models.DateField(blank=True, null=True)),
                ('quota_period_days', models.IntegerField(default=7)),
                ('has_started', models.BooleanField(default=False)),
                ('has_ended', models.BooleanField(default=False)),
                ('has_closed', models.BooleanField(default=False)),
                ('details', models.TextField(blank=True)),
                ('twilio_phone_num', models.CharField(max_length=10, validators=[django.core.validators.RegexValidator(message='Must be a 10 digit phone number', regex='^\\d{10}$')], verbose_name='Twilio Phone Number')),
                ('twilio_account_sid', models.CharField(max_length=34, validators=[django.core.validators.RegexValidator(message='Must be a 34 digit alphanumeric string', regex='^[a-zA-Z0-9]{34}$')], verbose_name='Twilio Account SID')),
                ('twilio_auth_token', models.CharField(max_length=32, validators=[django.core.validators.RegexValidator(message='Must be a 32 digit lowercase alphanumeric string', regex='^[a-z0-9]{32}$')], verbose_name='Twilio Authorization Token')),
                ('admin', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='games_as_admin', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Player',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.IntegerField(default=-1)),
                ('num_kills_prev_quota_check', models.IntegerField(default=0)),
                ('exempt_from_quota_check', models.BooleanField(default=False)),
                ('alive', models.BooleanField(default=True)),
                ('game', models.ForeignKey(default=main.models.get_current_game, on_delete=django.db.models.deletion.CASCADE, related_name='players', to='main.Game')),
                ('target', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='attacker', to='main.Player')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='players', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-game', 'position'),
            },
        ),
        migrations.CreateModel(
            name='QuotaCheck',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('valid', models.BooleanField(default=True)),
                ('game', models.ForeignKey(default=main.models.get_current_game, on_delete=django.db.models.deletion.CASCADE, related_name='quota_checks', to='main.Game')),
            ],
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_num', models.CharField(max_length=10, validators=[django.core.validators.RegexValidator(message='Must be a 10 digit phone number', regex='^\\d{10}$')])),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='elimination',
            name='attacker',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='eliminations_as_attacker', to='main.Player'),
        ),
        migrations.AddField(
            model_name='elimination',
            name='game',
            field=models.ForeignKey(default=main.models.get_current_game, on_delete=django.db.models.deletion.CASCADE, related_name='eliminations', to='main.Game'),
        ),
        migrations.AddField(
            model_name='elimination',
            name='killer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='eliminations_as_killer', to='main.Player'),
        ),
        migrations.AddField(
            model_name='elimination',
            name='quota_check',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='eliminations', to='main.QuotaCheck'),
        ),
        migrations.AddField(
            model_name='elimination',
            name='target',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='eliminations_as_target', to='main.Player'),
        ),
        migrations.AlterUniqueTogether(
            name='player',
            unique_together=set([('game', 'user')]),
        ),
    ]
