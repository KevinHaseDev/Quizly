"""Views for handling user registration, login, token refresh, and logout."""
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializer import LoginSerializer, RegistrationSerializer



class RegistrationView(APIView):
    """View for handling user registration."""
    permission_classes = [AllowAny]

    def post(self, request):
        """Handle POST request for user registration."""
        serializer = RegistrationSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {'detail': 'User created successfully!'},
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
class LoginView(TokenObtainPairView):
    """View for handling user login."""
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        """Handle POST request for user login and 
        return JWT tokens in cookies."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._build_response(serializer.validated_data)

    def _build_response(self, validated_data):
        """Build the response for a successful login, 
        setting JWT tokens in cookies."""
        response = Response(
            {'detail': 'Login successfully!', 'user': validated_data['user']},
            status=status.HTTP_200_OK,
        )
        self._set_token_cookies(response, validated_data)
        return response

    def _set_token_cookies(self, response, validated_data):
        """Set the JWT tokens in cookies."""
        response.set_cookie(
            key='access_token',
            value=str(validated_data['access']),
            httponly=True,
            secure=not settings.DEBUG,
            samesite='LAX',
        )
        response.set_cookie(
            key='refresh_token',
            value=str(validated_data['refresh']),
            httponly=True,
            secure=not settings.DEBUG,
            samesite='LAX',
        )

class CookieTokenRefreshView(TokenRefreshView):
    """View for handling JWT token refresh using cookies."""
    def post(self, request, *args, **kwargs):
        """Handle POST request for refreshing JWT tokens using cookies."""
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
            secure=not settings.DEBUG,
            samesite='LAX',
        )

        return response


class LogoutView(APIView):
    """View for handling user logout."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Handle POST request for user logout, 
        blacklisting the refresh token and clearing cookies."""
        self._blacklist_refresh_token(request)
        response = Response(
            {'detail': 'Log-Out successfully! All Tokens will be deleted. '
            'Refresh token is now invalid.'},
            status=status.HTTP_200_OK,
        )
        self._clear_auth_cookies(response)
        return response

    def _blacklist_refresh_token(self, request):
        """Blacklist the refresh token."""
        refresh_token = request.COOKIES.get('refresh_token')
        if not refresh_token:
            return
        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            return

    def _clear_auth_cookies(self, response):
        """Clear the authentication cookies."""
        response.delete_cookie('access_token', samesite='LAX')
        response.delete_cookie('refresh_token', samesite='LAX')
