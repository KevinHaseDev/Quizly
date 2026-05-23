from django.urls import path

from .views import CookieTokenRefreshView, LoginView, LogoutView, RegistrationView


urlpatterns = [
    path('register/', RegistrationView.as_view(), name='register'),
    path('registration/', RegistrationView.as_view(), name='registration'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/', LoginView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
]