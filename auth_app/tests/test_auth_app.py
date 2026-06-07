"""Integration tests for auth_app API endpoints."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()


class RegistrationEndpointTests(APITestCase):
	"""Tests for the POST /api/register/ endpoint."""

	def setUp(self):
		self.url = "/api/register/"

	def test_register_returns_201_for_valid_payload(self):
		"""Expect 201 Created when a valid registration payload is submitted."""
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
		"""Expect 400 Bad Request when confirmed_password does not match password."""
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
		"""Expect 400 Bad Request and no new user when the email is already taken."""
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
	"""Tests for the POST /api/login/ endpoint."""

	def setUp(self):
		self.url = "/api/login/"
		self.user = User.objects.create_user(
			username="alice",
			email="alice@example.com",
			password="safe-password-123",
		)

	def test_login_returns_200_for_valid_credentials(self):
		"""Expect 200 OK when correct username and password are provided."""
		payload = {
			"username": "alice",
			"password": "safe-password-123",
		}

		response = self.client.post(self.url, payload, format="json")

		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_login_returns_401_for_invalid_credentials(self):
		"""Expect 401 Unauthorized when the password is wrong."""
		payload = {
			"username": "alice",
			"password": "wrong-password-456",
		}

		response = self.client.post(self.url, payload, format="json")

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_login_sets_access_and_refresh_token_cookies(self):
		"""Expect both access_token and refresh_token cookies to be set on success."""
		payload = {
			"username": "alice",
			"password": "safe-password-123",
		}

		response = self.client.post(self.url, payload, format="json")

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn("access_token", response.cookies)
		self.assertIn("refresh_token", response.cookies)


class TokenRefreshEndpointTests(APITestCase):
	"""Tests for the POST /api/token/refresh/ endpoint."""

	def setUp(self):
		self.url = "/api/token/refresh/"
		self.user = User.objects.create_user(
			username="alice",
			email="alice@example.com",
			password="safe-password-123",
		)
		self.refresh_token = str(RefreshToken.for_user(self.user))

	def test_refresh_returns_200_for_valid_refresh_token_cookie(self):
		"""Expect 200 OK when a valid refresh_token cookie is present."""
		self.client.cookies["refresh_token"] = self.refresh_token

		response = self.client.post(self.url, {}, format="json")

		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_refresh_returns_401_for_missing_refresh_token_cookie(self):
		"""Expect 401 Unauthorized when no refresh_token cookie is sent."""
		response = self.client.post(self.url, {}, format="json")

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_refresh_returns_401_for_invalid_refresh_token_cookie(self):
		"""Expect 401 Unauthorized when the refresh_token cookie value is invalid."""
		self.client.cookies["refresh_token"] = "invalid-refresh-token"

		response = self.client.post(self.url, {}, format="json")

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_refresh_sets_new_access_token_cookie(self):
		"""Expect a new access_token cookie that differs from the stale one."""
		self.client.cookies["refresh_token"] = self.refresh_token
		self.client.cookies["access_token"] = "stale-access-token"

		response = self.client.post(self.url, {}, format="json")

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn("access_token", response.cookies)
		self.assertNotEqual(response.cookies["access_token"].value, "stale-access-token")


class LogoutEndpointTests(APITestCase):
	"""Tests for the POST /api/logout/ endpoint."""

	def setUp(self):
		self.url = "/api/logout/"
		self.user = User.objects.create_user(
			username="alice",
			email="alice@example.com",
			password="safe-password-123",
		)
		self.refresh_token = RefreshToken.for_user(self.user)
		self.access_token = str(self.refresh_token.access_token)

	def test_logout_returns_200_for_cookie_authenticated_user(self):
		"""Expect 200 OK when the user is authenticated via token cookies."""
		self.client.cookies["access_token"] = self.access_token
		self.client.cookies["refresh_token"] = str(self.refresh_token)

		response = self.client.post(self.url, {}, format="json")

		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_logout_returns_200_for_authenticated_user(self):
		"""Expect 200 OK when the user is force-authenticated and tokens are in cookies."""
		self.client.force_authenticate(user=self.user)
		self.client.cookies["access_token"] = self.access_token
		self.client.cookies["refresh_token"] = str(self.refresh_token)

		response = self.client.post(self.url, {}, format="json")

		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_logout_returns_401_without_authentication(self):
		"""Expect 401 Unauthorized when the request carries no credentials."""
		response = self.client.post(self.url, {}, format="json")

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_logout_deletes_access_and_refresh_token_cookies(self):
		"""Expect both token cookies to be expired (max-age=0) after logout."""
		self.client.force_authenticate(user=self.user)
		self.client.cookies["access_token"] = self.access_token
		self.client.cookies["refresh_token"] = str(self.refresh_token)

		response = self.client.post(self.url, {}, format="json")

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn("access_token", response.cookies)
		self.assertIn("refresh_token", response.cookies)
		self.assertEqual(str(response.cookies["access_token"]["max-age"]), "0")
		self.assertEqual(str(response.cookies["refresh_token"]["max-age"]), "0")
