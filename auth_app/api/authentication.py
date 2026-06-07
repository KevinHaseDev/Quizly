"""Custom authentication class for JWT that retrieves the token from cookies."""
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom authentication class that retrieves the JWT token from cookies 
    instead of the Authorization header.
    """
    def authenticate(self, request):
        raw_token = request.COOKIES.get('access_token')
        if not raw_token:
            return None
        validated_token = self.get_validated_token(raw_token.encode('utf-8'))
        return self.get_user(validated_token), validated_token
