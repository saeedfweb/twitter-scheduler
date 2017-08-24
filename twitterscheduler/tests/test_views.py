from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
from django.shortcuts import reverse
from django.http import Http404
from django.contrib.sites.models import Site

import datetime
from unittest import mock

from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken

from twitterscheduler.models import Tweet, ScheduledTweet, Profile
from twitterscheduler.views import index, get_authed_tweepy, sync_tweets_from_twitter


class TestIndexView(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create 13 tweets
        user = User.objects.create_user('boy', password='nice_pass')
        num_tweets = 13
        for tweet_i in range(num_tweets):
            Tweet.objects.create(tweet_id=str(tweet_i), text=f'text for tweet_i: {tweet_i}', user=user, sentiment='p',
                                 is_posted=True, time_posted_at=timezone.now()+datetime.timedelta(minutes=-tweet_i))

    def setUp(self):
        self.user1 = User.objects.create_user('test_user1', password='nice_pass')
        self.user2 = User.objects.create_user('test_user2', password='nice_pass')
        self.view_reverse = reverse('twitterscheduler:index')

    def test_exists_at_desired_url(self):
        resp = self.client.get('/scheduler/')
        self.assertNotEqual(resp.status_code, 404)

    def test_redirects_when_not_logged_in(self):
        resp = self.client.get(self.view_reverse)
        self.assertRedirects(resp, f'/accounts/login/?next={self.view_reverse}')

    def test_accessible_when_logged_in(self):
        login = self.client.login(username='test_user1', password='nice_pass')
        resp = self.client.get(self.view_reverse)
        self.assertEqual(resp.status_code, 200)

    def test_correct_user_context(self):
        login = self.client.login(username='test_user1', password='nice_pass')
        resp = self.client.get(self.view_reverse)
        self.assertEqual(str(resp.context['user']), 'test_user1')

    def test_correct_template(self):
        login = self.client.login(username='test_user1', password='nice_pass')
        resp = self.client.get(self.view_reverse)
        self.assertTemplateUsed(resp, 'twitterscheduler/index.html')

    def test_user_tweets_context_is_passed_in(self):
        login = self.client.login(username='test_user1', password='nice_pass')
        resp = self.client.get(self.view_reverse)

        self.assertTrue('user_tweets' in resp.context)
        self.assertEqual(len(resp.context['user_tweets']), 0)

        Tweet.objects.create(user=self.user1, text='text 1')
        Tweet.objects.create(user=self.user1, text='text 2')
        resp = self.client.get(self.view_reverse)
        self.assertEqual(len(resp.context['user_tweets']), 2)

    def test_only_users_tweets_are_in_context(self):
        login = self.client.login(username='test_user1', password='nice_pass')

        Tweet.objects.create(user=self.user1, text='text 1')
        Tweet.objects.create(user=self.user1, text='text 2')
        Tweet.objects.create(user=self.user2, text='text 3')
        resp = self.client.get(self.view_reverse)
        self.assertEqual(len(resp.context['user_tweets']), 2)
        for tweet in resp.context['user_tweets']:
            self.assertEqual(tweet.user.username, 'test_user1')


class TestCreateScheduledTweet(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user('test_user1', password='nice_pass')
        self.user2 = User.objects.create_user('test_user2', password='nice_pass')
        self.view_reverse = reverse('twitterscheduler:create-scheduled-tweet')

    def test_exists_at_desired_url(self):
        resp = self.client.get('/scheduler/tweet/create/')
        self.assertNotEqual(resp.status_code, 404)

    def test_reverse_url(self):
        resp = self.client.get(self.view_reverse)
        self.assertNotEqual(resp.status_code, 404)

    def test_redirected_to_login_if_not_authed(self):
        resp = self.client.get(self.view_reverse)
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, f'/accounts/login/?next={self.view_reverse}')

    def test_logged_in_user_can_access_page(self):
        login = self.client.login(username='test_user1', password='nice_pass')
        resp = self.client.get(self.view_reverse)
        self.assertEqual(resp.status_code, 200)

    def test_tweet_form_in_context(self):
        login = self.client.login(username='test_user1', password='nice_pass')
        resp = self.client.get(self.view_reverse)
        self.assertTrue('tweet_form' in resp.context)

    def test_correct_template(self):
        login = self.client.login(username='test_user1', password='nice_pass')
        resp = self.client.get(self.view_reverse)
        self.assertTemplateUsed(resp, 'twitterscheduler/create_scheduled_tweet.html')

    def test_form_correct_initial_date(self):
        login = self.client.login(username='test_user1', password='nice_pass')
        resp = self.client.get(self.view_reverse)
        future_date = timezone.now() + datetime.timedelta(minutes=5)
        self.assertTrue(future_date - resp.context['tweet_form'].initial['time_to_tweet'] < datetime.timedelta(seconds=10))

    def test_redirects_to_index_after_posting_valid_data(self):
        login = self.client.login(username='test_user1', password='nice_pass')
        time_to_tweet = datetime.datetime.now()+datetime.timedelta(minutes=5)
        resp = self.client.post(self.view_reverse, {'time_to_tweet': time_to_tweet, 'text': 'nice tweet dood'})
        self.assertRedirects(resp, reverse('twitterscheduler:index'))

    # def test_posts_scheduled_tweet_and_associated_tweet(self):
    #     self.assertTrue(False)


class DictToObj:
    def __init__(self, **kwargs):
        for key, val in kwargs.items():
            setattr(self, key, val)


class TestTwitterIntegrations(TestCase):

    @classmethod
    def setUpTestData(cls):
        Site.objects.create(domain='http://127.0.0.1:8000', name='localhost')

    def setUp(self):
        site = Site.objects.get(name='localhost')
        self.app = SocialApp.objects.create(provider='twitter', name='twitter', client_id='id_1234',
                                            secret='secret_1234')
        self.app.sites.add(site)
        self.app.save()
        self.user = User.objects.create_user('bob', password='nice_pass')
        self.mock_tweets = [
            DictToObj(id_str=str(i), text=f'text {i}', created_at=timezone.now() + datetime.timedelta(minutes=-i-15))
            for i in range(10)
        ]

    def test_get_authed_tweepy_returns_404_when_no_twitter_app(self):
        SocialApp.objects.get(name='twitter').delete()
        self.assertRaises(Http404, get_authed_tweepy, '1', '1')

    def test_get_authed_tweepy_returns_instance_with_credentials_set(self):
        authed = get_authed_tweepy('123', '456')
        self.assertEqual(authed.auth.consumer_key, b'id_1234')
        self.assertEqual(authed.auth.consumer_secret, b'secret_1234')
        self.assertEqual(authed.auth.access_token, '123')
        self.assertEqual(authed.auth.access_token_secret, '456')

    @mock.patch('twitterscheduler.views.get_authed_tweepy')
    def test_sync_tweets_from_twitter_no_tweets_created_when_no_tweets_on_twitter(self, mock_tweepy):
        mock_tweepy.return_value.user_timeline = lambda : []

        sync_tweets_from_twitter(self.user, '123', '456')
        tweets = Tweet.objects.filter(user=self.user)
        self.assertEqual(len(tweets), 0)
        tweets = Tweet.objects.all()
        self.assertEqual(len(tweets), 0)

    @mock.patch('twitterscheduler.views.get_authed_tweepy')
    def test_sync_tweets_from_twitter_tweets_added_when_db_is_empty(self, mock_tweepy):
        mock_tweepy.return_value.user_timeline = lambda : self.mock_tweets[:5]

        sync_tweets_from_twitter(self.user, '123', '456')
        tweets = Tweet.objects.filter(user=self.user)
        self.assertEqual(len(tweets), 5)

    @mock.patch('twitterscheduler.views.get_authed_tweepy')
    def test_sync_tweets_from_twitter_tweets_not_added_when_existing_in_db(self, mock_tweepy):
        mock_tweepy.return_value.user_timeline = lambda : self.mock_tweets[:5]

        for mock_tweet in self.mock_tweets[:5]:
            Tweet.objects.create(tweet_id=mock_tweet.id_str, user=self.user, text='boogala')

        sync_tweets_from_twitter(self.user, '123', '456')
        tweets = Tweet.objects.filter(user=self.user)
        self.assertEqual(len(tweets), 5)
        for tweet in tweets:
            self.assertEqual(tweet.text, 'boogala')

    @mock.patch('twitterscheduler.views.get_authed_tweepy')
    def test_sync_tweets_from_twitter_only_new_tweets_added(self, mock_tweepy):
        # new as in not already in db. doesn't have to do with time.
        mock_tweepy.return_value.user_timeline = lambda : self.mock_tweets[:3]

        for mock_tweet in self.mock_tweets[:1]:
            Tweet.objects.create(tweet_id=mock_tweet.id_str, user=self.user, text='boogala')

        tweets = Tweet.objects.filter(user=self.user)
        self.assertEqual(len(tweets), 1)

        sync_tweets_from_twitter(self.user, '123', '456')
        tweets = Tweet.objects.filter(user=self.user)
        self.assertEqual(len(tweets), 3)
        self.assertEqual(tweets[0].text, 'boogala')

    @mock.patch('twitterscheduler.views.get_authed_tweepy')
    def test_sync_tweets_from_twitter_dont_add_tweets_within_last_5_minutes(self, mock_tweepy):
        new_tweet = DictToObj(id_str='20', text=f'text 20', created_at=timezone.now() + datetime.timedelta(minutes=-1))
        new_tweet2 = DictToObj(id_str='21', text=f'text 21', created_at=timezone.now() + datetime.timedelta(minutes=-4, seconds=59))
        mock_tweepy.return_value.user_timeline = lambda : [new_tweet, new_tweet2]

        sync_tweets_from_twitter(self.user, '123', '456')
        tweets = Tweet.objects.filter(user=self.user)
        self.assertEqual(len(tweets), 0)


