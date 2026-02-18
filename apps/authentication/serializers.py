from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, SignupAttempt

class SignupStartSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])

class SignupVerifySerializer(serializers.Serializer):
    signupToken = serializers.CharField(source="signup_token")
    code = serializers.CharField()

class SignupCompleteSerializer(serializers.Serializer):
    signupToken = serializers.CharField(source="signup_token")
    fullName = serializers.CharField(source="full_name")
    birthDate = serializers.DateField(source="birth_date")

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class UserSerializer(serializers.ModelSerializer):
    userId = serializers.SerializerMethodField()
    name = serializers.CharField(source="full_name")
    onboardingComplete = serializers.BooleanField(source="onboarding_complete")

    class Meta:
        model = User
        fields = ["userId", "email", "name", "onboardingComplete"]

    def get_userId(self, obj):
        return f"usr_{obj.id}"

class PasswordResetSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, validators=[validate_password])

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
