# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-08-19 22:14
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('twitterscheduler', '0002_auto_20170818_1119'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='tweet',
            options={'ordering': ['-time_posted_at']},
        ),
        migrations.AlterField(
            model_name='tweet',
            name='tweet_id',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
    ]