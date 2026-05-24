from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from quiz_app.models import Quiz


User = get_user_model()


class QuizListCreateEndpointTests(APITestCase):
    def setUp(self):
        self.url = '/api/quizzes/'
        self.user = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='safe-password-123',
        )
        self.other_user = User.objects.create_user(
            username='bob',
            email='bob@example.com',
            password='safe-password-123',
        )

    def test_quiz_list_returns_401_without_authentication(self):
        response = self.client.get(self.url, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_quiz_list_returns_200_for_own_quizzes(self):
        own_quiz = Quiz.objects.create(
            owner=self.user,
            video_url='https://www.youtube.com/watch?v=ownquiz001',
            title='Own Quiz',
            description='Owned by authenticated user',
        )
        Quiz.objects.create(
            owner=self.other_user,
            video_url='https://www.youtube.com/watch?v=otherquiz01',
            title='Other Quiz',
            description='Owned by another user',
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], own_quiz.id)

    def test_quiz_create_returns_201_for_valid_youtube_url(self):
        payload = {
            'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        }
        self.client.force_authenticate(user=self.user)

        # Keep external generation mocked during API tests.
        with patch('quiz_app.api.views.create_quiz_from_youtube_url', create=True) as mocked_create:
            mocked_create.return_value = Quiz.objects.create(
                owner=self.user,
                video_url=payload['url'],
                title='Generated Quiz',
                description='Created by mocked generator',
            )
            response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_quiz_create_returns_400_for_invalid_url(self):
        payload = {
            'url': 'https://example.com/not-a-youtube-video',
        }
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class QuizDetailEndpointTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='charlie',
            email='charlie@example.com',
            password='safe-password-123',
        )
        self.other_user = User.objects.create_user(
            username='diana',
            email='diana@example.com',
            password='safe-password-123',
        )
        self.own_quiz = Quiz.objects.create(
            owner=self.user,
            video_url='https://www.youtube.com/watch?v=ownquiz002',
            title='Owned Quiz',
            description='Owned by requesting user',
        )
        self.other_quiz = Quiz.objects.create(
            owner=self.other_user,
            video_url='https://www.youtube.com/watch?v=otherquiz02',
            title='Foreign Quiz',
            description='Owned by another user',
        )

    def test_quiz_detail_returns_401_without_authentication(self):
        response = self.client.get(self._detail_url(self.own_quiz.id), format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_quiz_detail_returns_200_for_own_quiz(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self._detail_url(self.own_quiz.id), format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_quiz_detail_returns_403_for_foreign_quiz(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self._detail_url(self.other_quiz.id), format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_quiz_detail_returns_404_for_unknown_quiz_id(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self._detail_url(999999), format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def _detail_url(self, quiz_id):
        return f'/api/quizzes/{quiz_id}/'
