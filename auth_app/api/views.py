from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializer import LoginSerializer, RegistrationSerializer

class RegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {'detail': 'User created successfully!'},
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
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
        response.set_cookie(
            key='access_token',
            value=str(validated_data['access']),
            httponly=True,
            secure=True,
            samesite='LAX',
        )
        response.set_cookie(
            key='refresh_token',
            value=str(validated_data['refresh']),
            httponly=True,
            secure=True,
            samesite='LAX',
        )

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
            secure=True,
            samesite='LAX',
        )

        return response