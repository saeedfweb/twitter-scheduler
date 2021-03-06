from django.test import TestCase
from django.contrib.auth.models import User
from django.db.utils import DataError
from django.utils import timezone

from twitterscheduler.models import Profile, Tweet, ScheduledTweet

from datetime import timedelta


class TestProfile(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='bob', password='nice_pass')
        self.profile = Profile.objects.create(user=self.user)

    def test_profile_has_correct_user(self):
        profile = Profile.objects.get(pk=self.profile.id)
        self.assertEqual(profile.user, self.user)

    def test_profile_deleted_when_user_deleted(self):
        self.assertEqual(len(Profile.objects.filter(pk=self.profile.id)), 1)
        self.user.delete()
        self.assertEqual(len(Profile.objects.filter(pk=self.profile.id)), 0)

    def test_require_correctly_spelled_set_False_default(self):
        self.assertEqual(self.profile.require_correctly_spelled, False)

    def test_require_positive_sentiment_set_False_default(self):
        self.assertEqual(self.profile.require_positive_sentiment, False)

    def test_synced_tweets_recently_is_True_when_recently_syncing_tweets(self):
        self.profile.last_sync_time = timezone.now() - timedelta(minutes=14, seconds=59)
        self.assertIs(self.profile.synced_tweets_recently(), True)

    def test_synced_tweets_recently_greater_than_5_minutes(self):
        self.profile.last_sync_time = timezone.now() - timedelta(minutes=15)
        self.assertIs(self.profile.synced_tweets_recently(), False)

    def test_new_profile_not_recently_synced(self):
        self.assertIs(self.profile.synced_tweets_recently(), False)

    def test_profile_created_when_user_is_created(self):
        user = User.objects.create_user('roe', password='nice')
        self.assertEqual(len(Profile.objects.filter(user=user)), 1)


class TestTweetModel(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('bob', 'nice_pass')
        self.tweet = Tweet.objects.create(tweet_id='1', user=self.user, text='rando text')

    def test_tweet_id_max_value(self):
        tweet = Tweet.objects.create(tweet_id='1'*64, user=self.user, text='rando text')
        self.assertEqual(len(tweet.tweet_id), 64)

    def test_tweet_id_exceed_max_value(self):
        self.assertRaises(DataError, Tweet.objects.create, tweet_id='1'*65, user=self.user, text='rando text')

    def test_tweet_deleted_when_user_is_deleted(self):
        self.user.delete()
        self.assertEqual(len(Tweet.objects.filter(tweet_id='1')), 0)

    def test_text_max_length(self):
        max_length = self.tweet._meta.get_field('text').max_length
        self.assertEquals(max_length, 140)

    def test_default_sentiment_u(self):
        self.assertEqual(self.tweet.sentiment, 'u')

    def test_valid_sentiment_value(self):
        tweet = Tweet.objects.create(tweet_id='1', user=self.user, text='rando text', sentiment='p')
        self.assertTrue(('p', 'positive') in tweet._meta.get_field('sentiment').choices)
        self.assertTrue(('n', 'negative') in tweet._meta.get_field('sentiment').choices)

    def test_invalid_sentiment_value(self):
        tweet = Tweet.objects.create(tweet_id='1', user=self.user, text='rando text', sentiment='g')
        self.assertTrue(('g', 'grandiose') not in tweet._meta.get_field('sentiment').choices)

    def test_time_posted_at_can_be_blank(self):
        tweet = Tweet.objects.create(tweet_id='1', user=self.user, text='rando text')
        self.assertEqual(tweet.time_posted_at, None)

    def test_is_posted_default_False(self):
        self.assertFalse(self.tweet.is_posted)

    def test_order_by_posted_at_descending(self):
        tweet0 = Tweet.objects.create(tweet_id='2', user=self.user, text='rando 0', time_posted_at=timezone.now())
        tweet1 = Tweet.objects.create(tweet_id='3', user=self.user, text='rando 1', time_posted_at=timezone.now()-timedelta(minutes=10))
        tweet2 = Tweet.objects.create(tweet_id='4', user=self.user, text='rando 2', time_posted_at=timezone.now()-timedelta(minutes=20))
        tweets = Tweet.objects.all()
        self.assertEqual(tweets[1], tweet0)
        self.assertEqual(tweets[2], tweet1)
        self.assertEqual(tweets[3], tweet2)


class TestScheduleTweetModel(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('bob', 'nice_pass')
        self.tweet = Tweet.objects.create(tweet_id='1', user=self.user, text='rando text')
        self.scheduled = ScheduledTweet.objects.create(tweet=self.tweet, time_to_tweet=timezone.now())

    def test_scheduled_tweet_deleted_if_tweet_is_deleted(self):
        self.tweet.delete()
        self.assertEqual(len(ScheduledTweet.objects.filter(pk=1)), 0)

    def test_created_at_default_is_timezone_now(self):
        now = timezone.now()
        scheduled = ScheduledTweet.objects.create(tweet=self.tweet, time_to_tweet=timezone.now())
        self.assertTrue(scheduled.created_at-now < timedelta(minutes=1))

    def test_order_by_time_to_tweet_ascending(self):
        tweet1 = Tweet.objects.create(user=self.user, text='rando 0')
        tweet2 = Tweet.objects.create(user=self.user, text='rando 1')
        tweet3 = Tweet.objects.create(user=self.user, text='rando 2')
        scheduled_tweet1 = ScheduledTweet.objects.create(tweet=tweet1, time_to_tweet=timezone.now()+timedelta(minutes=4))
        scheduled_tweet2 = ScheduledTweet.objects.create(tweet=tweet2, time_to_tweet=timezone.now())
        scheduled_tweet3 = ScheduledTweet.objects.create(tweet=tweet3, time_to_tweet=timezone.now()+timedelta(minutes=10))
        scheduled = ScheduledTweet.objects.all()
        self.assertEqual(scheduled[1], scheduled_tweet2)
        self.assertEqual(scheduled[2], scheduled_tweet1)
        self.assertEqual(scheduled[3], scheduled_tweet3)

    def test_absolute_url(self):
        self.assertEqual(self.scheduled.get_absolute_url(), f'/scheduler/scheduled-tweet/{self.scheduled.id}/edit/')

