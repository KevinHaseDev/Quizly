from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()


class RegistrationEndpointTests(APITestCase):
	"""Tests for the user registration endpoint."""
	def setUp(self):
		"""Set up the URL for the registration endpoint."""
		self.url = "/api/register/"

	def test_register_returns_201_for_valid_payload(self):
		"""Test that a valid registration payload creates a new user and returns 201."""
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
		"""Test that a registration payload with mismatched password and confirmed_password returns 400."""
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
		"""Test that a registration payload with an email that is already taken returns 400."""
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
	"""Tests for the user login endpoint."""
	def setUp(self):
		"""Set up the URL for the login endpoint and create a test user."""
		self.url = "/api/login/"
		self.user = User.objects.create_user(
			username="alice",
			email="alice@example.com",
			password="safe-password-123",
		)

	def test_login_returns_200_for_valid_credentials(self):
		"""Test that a login with valid credentials returns 200."""
		payload = {
			"username": "alice",
			"password": "safe-password-123",
		}

		response = self.client.post(self.url, payload, format="json")

		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_login_returns_401_for_invalid_credentials(self):
		"""Test that a login with invalid credentials returns 401."""
		payload = {
			"username": "alice",
			"password": "wrong-password-456",
		}

		response = self.client.post(self.url, payload, format="json")

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_login_sets_access_and_refresh_token_cookies(self):
		"""Test that a login with valid credentials sets access and refresh token cookies."""
		payload = {
			"username": "alice",
			"password": "safe-password-123",
		}

		response = self.client.post(self.url, payload, format="json")

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn("access_token", response.cookies)
		self.assertIn("refresh_token", response.cookies)


class TokenRefreshEndpointTests(APITestCase):
	"""Tests for the token refresh endpoint."""
	def setUp(self):
		"""Set up the URL for the token refresh endpoint and create a test user."""
		self.url = "/api/token/refresh/"
		self.user = User.objects.create_user(
			username="alice",
			email="alice@example.com",
			password="safe-password-123",
		)
		self.refresh_token = str(RefreshToken.for_user(self.user))

	def test_refresh_returns_200_for_valid_refresh_token_cookie(self):
		"""Test that a token refresh with a valid refresh token cookie returns 200."""
		self.client.cookies["refresh_token"] = self.refresh_token

		response = self.client.post(self.url, {}, format="json")

		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_refresh_returns_401_for_missing_refresh_token_cookie(self):
		"""Test that a token refresh without a refresh token cookie returns 401."""
		response = self.client.post(self.url, {}, format="json")

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_refresh_returns_401_for_invalid_refresh_token_cookie(self):
		"""Test that a token refresh with an invalid refresh token cookie returns 401."""
		self.client.cookies["refresh_token"] = "invalid-refresh-token"

		response = self.client.post(self.url, {}, format="json")

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_refresh_sets_new_access_token_cookie(self):
		"""Test that a token refresh with a valid refresh token cookie sets a new access token cookie."""
		self.client.cookies["refresh_token"] = self.refresh_token
		self.client.cookies["access_token"] = "stale-access-token"

		response = self.client.post(self.url, {}, format="json")

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn("access_token", response.cookies)
		self.assertNotEqual(response.cookies["access_token"].value, "stale-access-token")


class LogoutEndpointTests(APITestCase):
	"""Tests for the user logout endpoint."""
	def setUp(self):
		"""Set up the URL for the logout endpoint and create a test user with tokens."""
		self.url = "/api/logout/"
		self.user = User.objects.create_user(
			username="alice",
			email="alice@example.com",
			password="safe-password-123",
		)
		self.refresh_token = RefreshToken.for_user(self.user)
		self.access_token = str(self.refresh_token.access_token)

	def test_logout_returns_200_for_cookie_authenticated_user(self):
		"""Test that a logout with valid access and refresh token cookies returns 200."""
		self.client.cookies["access_token"] = self.access_token
		self.client.cookies["refresh_token"] = str(self.refresh_token)

		response = self.client.post(self.url, {}, format="json")

		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_logout_returns_200_for_authenticated_user(self):
		"""Test that a logout with valid access and refresh token cookies returns 200 for an authenticated user."""
		self.client.force_authenticate(user=self.user)
		self.client.cookies["access_token"] = self.access_token
		self.client.cookies["refresh_token"] = str(self.refresh_token)

		response = self.client.post(self.url, {}, format="json")

		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_logout_returns_401_without_authentication(self):
		"""Test that a logout without authentication returns 401."""
		response = self.client.post(self.url, {}, format="json")

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_logout_deletes_access_and_refresh_token_cookies(self):
		"""Test that a logout deletes access and refresh token cookies."""
		self.client.force_authenticate(user=self.user)
		self.client.cookies["access_token"] = self.access_token
		self.client.cookies["refresh_token"] = str(self.refresh_token)

		response = self.client.post(self.url, {}, format="json")

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn("access_token", response.cookies)
		self.assertIn("refresh_token", response.cookies)
		self.assertEqual(str(response.cookies["access_token"]["max-age"]), "0")
		self.assertEqual(str(response.cookies["refresh_token"]["max-age"]), "0")
