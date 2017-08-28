# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-08-14 20:37
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('require_correctly_spelled', models.BooleanField(default=False)),
                ('require_positive_sentiment', models.BooleanField(default=False)),
                ('last_sync_time', models.DateTimeField(default=django.utils.timezone.now)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ScheduledTweet',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('time_to_tweet', models.DateTimeField()),
            ],
        ),
        migrations.CreateModel(
            name='Tweet',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tweet_id', models.IntegerField()),
                ('text', models.CharField(max_length=140)),
                ('sentiment', models.CharField(blank=True, choices=[('p', 'positive'), ('n', 'negative'), ('u', 'unknown')], default='u', help_text='Sentiment of tweet', max_length=1)),
                ('time_posted_at', models.DateTimeField(blank=True, null=True)),
                ('is_posted', models.BooleanField(default=False, help_text='Whether or not the tweet has been posted to twitter')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='scheduledtweet',
            name='tweet',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='twitterscheduler.Tweet'),
        ),
    ]