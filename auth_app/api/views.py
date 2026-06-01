from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication


def _jwt_lifetime_seconds(setting_key, default_seconds):
    lifetime = (getattr(settings, 'SIMPLE_JWT', {}) or {}).get(setting_key)
    if lifetime is None:
        return default_seconds
    try:
        return int(lifetime.total_seconds())
    except (AttributeError, TypeError, ValueError):
        return default_seconds


def _access_cookie_max_age():
    return getattr(
        settings,
        'AUTH_COOKIE_ACCESS_MAX_AGE',
        _jwt_lifetime_seconds('ACCESS_TOKEN_LIFETIME', 300),
    )


def _refresh_cookie_max_age():
    return getattr(
        settings,
        'AUTH_COOKIE_REFRESH_MAX_AGE',
        _jwt_lifetime_seconds('REFRESH_TOKEN_LIFETIME', 86400),
    )


def _auth_cookie_secure():
    return bool(getattr(settings, 'AUTH_COOKIE_SECURE', False))


def _auth_cookie_samesite():
    return getattr(settings, 'AUTH_COOKIE_SAMESITE', 'Lax')


class CookieJWTAuthentication(JWTAuthentication):
    """Authenticate requests using only the access token cookie."""

    def get_header(self, request):
        # Authorization headers are intentionally ignored for protected routes.
        return None

    def authenticate(self, request):
        cookie_token = request.COOKIES.get('access_token')
        if not cookie_token:
            return None

        validated_token = self.get_validated_token(cookie_token)
        return self.get_user(validated_token), validated_token

from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializer import LoginSerializer, RegistrationSerializer



class RegistrationView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {'detail': 'User created successfully!'},
            status=status.HTTP_201_CREATED,
        )
        
class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._build_response(serializer.validated_data)

    def _build_response(self, validated_data):
        response = Response(
            {'detail': 'Login successfully!', 'user': validated_data['user']},
            status=status.HTTP_200_OK,
        )
        self._set_token_cookies(response, validated_data)
        return response

    def _set_token_cookies(self, response, validated_data):
        access_cookie = self._build_cookie_kwargs(_access_cookie_max_age())
        refresh_cookie = self._build_cookie_kwargs(_refresh_cookie_max_age())

        response.set_cookie(
            key='access_token',
            value=str(validated_data['access']),
            **access_cookie,
        )
        response.set_cookie(
            key='refresh_token',
            value=str(validated_data['refresh']),
            **refresh_cookie,
        )

    def _build_cookie_kwargs(self, max_age):
        return {
            'httponly': True,
            'secure': _auth_cookie_secure(),
            'samesite': _auth_cookie_samesite(),
            'max_age': max_age,
            'path': '/',
        }

class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get('refresh_token')
        if not refresh_token:
            return Response(
                {'detail': 'Invalid refresh token'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = self.get_serializer(data={'refresh': refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError:
            return Response(
                {'detail': 'Invalid refresh token'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        access_token = serializer.validated_data['access']
        response = Response(
            {'detail': 'Token refreshed'},
            status=status.HTTP_200_OK,
        )
        response.set_cookie(
            key='access_token',
            value=access_token,
            httponly=True,
            secure=_auth_cookie_secure(),
            samesite=_auth_cookie_samesite(),
            max_age=_access_cookie_max_age(),
            path='/',
        )

        return response


class LogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        self._blacklist_refresh_token(request)
        response = Response(
            {'detail': 'Log-Out successfully! All Tokens will be deleted. Refresh token is now invalid.'},
            status=status.HTTP_200_OK,
        )
        self._clear_auth_cookies(response)
        return response

    def _blacklist_refresh_token(self, request):
        refresh_token = request.COOKIES.get('refresh_token')
        if not refresh_token:
            return
        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            return

    def _clear_auth_cookies(self, response):
        response.delete_cookie(
            'access_token',
            path='/',
            samesite=_auth_cookie_samesite(),
        )
        response.delete_cookie(
            'refresh_token',
            path='/',
            samesite=_auth_cookie_samesite(),
        )