from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class RegistrationEndpointTests(APITestCase):
	def setUp(self):
		self.url = "/api/register/"

	def test_register_returns_201_for_valid_payload(self):
		payload = {
			"username": "alice",
			"email": "alice@example.com",
			"password": "safe-password-123",
			"confirmed_password": "safe-password-123",
		}

		response = self.client.post(self.url, payload, format="json")

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertTrue(User.objects.filter(username="alice", email="alice@example.com").exists())

	def test_register_returns_400_for_mismatched_confirmed_password(self):
		payload = {
			"username": "bob",
			"email": "bob@example.com",
			"password": "safe-password-123",
			"confirmed_password": "different-password-456",
		}

		response = self.client.post(self.url, payload, format="json")

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertFalse(User.objects.filter(username="bob", email="bob@example.com").exists())

	def test_register_returns_400_for_duplicate_email(self):
		User.objects.create_user(
			username="existing-user",
			email="taken@example.com",
			password="safe-password-123",
		)
		payload = {
			"username": "new-user",
			"email": "taken@example.com",
			"password": "safe-password-123",
			"confirmed_password": "safe-password-123",
		}

		response = self.client.post(self.url, payload, format="json")

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(User.objects.filter(email="taken@example.com").count(), 1)


class LoginEndpointTests(APITestCase):
	def setUp(self):
		self.url = "/api/login/"
		self.user = User.objects.create_user(
			username="alice",
			email="alice@example.com",
			password="safe-password-123",
		)

	def test_login_returns_200_for_valid_credentials(self):
		payload = {
			"username": "alice",
			"password": "safe-password-123",
		}

		response = self.client.post(self.url, payload, format="json")

		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_login_returns_401_for_invalid_credentials(self):
		payload = {
			"username": "alice",
			"password": "wrong-password-456",
		}

		response = self.client.post(self.url, payload, format="json")

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_login_sets_access_and_refresh_token_cookies(self):
		payload = {
			"username": "alice",
			"password": "safe-password-123",
		}

		response = self.client.post(self.url, payload, format="json")

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn("access_token", response.cookies)
		self.assertIn("refresh_token", response.cookies)
