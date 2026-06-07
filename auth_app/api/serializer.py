"""Serializers for user registration and login using JWT."""
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()

class RegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration with password confirmation."""
    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        """Meta class defining the model and fields for registration."""
        model = User
        fields = ['username', 'email', 'password', 'confirmed_password']
        extra_kwargs = {
            'password': {
                'write_only': True
            },
            'email': {
                'required': True
            }
        }

    def validate_confirmed_password(self, value):
        """Validate that the confirmed password 
        matches the original password."""
        password = self.initial_data.get('password')
        if password and value and password != value:
            raise serializers.ValidationError('Passwords do not match')
        return value

    def validate_email(self, value):
        """Validate that the email is unique."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email already exists')
        return value

    def create(self, validated_data):
        """Create a new user with the validated data."""
        validated_data.pop('confirmed_password')
        pw = validated_data.pop('password')

        account = User(**validated_data)
        account.set_password(pw)
        account.save()
        return account
    
class LoginSerializer(TokenObtainPairSerializer):
    """Serializer for user login using JWT."""
    def validate(self, attrs):
        """Validate the user credentials and 
        return the token along with user info."""
        data = super().validate(attrs)
        data['user'] = {
            'id': self.user.pk,
            'username': self.user.get_username(),
            'email': self.user.email,
        }
        return data