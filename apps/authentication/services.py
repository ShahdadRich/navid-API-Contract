import secrets
import string
from datetime import timedelta, date
from typing import Optional
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from .models import SignupAttempt, User

def generate_signup_token() -> str:
    """Generates a secure signup token."""
    return "st_" + secrets.token_urlsafe(16)

class AuthService:
    """Service layer for authentication logic."""

    @staticmethod
    def start_signup(email: str, password: str) -> SignupAttempt:
        """
        Starts the signup process by creating a SignupAttempt.
        Raises ValidationError if email already exists.
        """
        if User.objects.filter(email=email).exists():
            raise ValidationError("EMAIL_ALREADY_EXISTS")

        # Invalidate old attempts for this email
        SignupAttempt.objects.filter(email=email).delete()

        signup_token = generate_signup_token()
        verification_code = "123456" # Mock code as requested
        expires_at = timezone.now() + timedelta(minutes=15)

        signup_attempt = SignupAttempt.objects.create(
            email=email,
            encrypted_password=make_password(password),
            verification_code=verification_code,
            signup_token=signup_token,
            expires_at=expires_at
        )

        return signup_attempt

    @staticmethod
    def verify_code(signup_token: str, code: str) -> SignupAttempt:
        """
        Verifies the signup code against the token.
        Raises ValidationError if token is invalid, expired or code is wrong.
        """
        try:
            attempt = SignupAttempt.objects.get(signup_token=signup_token)
        except SignupAttempt.DoesNotExist:
            raise ValidationError("INVALID_TOKEN")

        if attempt.expires_at < timezone.now():
            raise ValidationError("CODE_EXPIRED")

        if attempt.verification_code != code:
            raise ValidationError("INVALID_CODE")

        return attempt

    @staticmethod
    def complete_signup(signup_token: str, full_name: str, birth_date: date) -> User:
        """
        Completes the signup process by creating a User from a SignupAttempt.
        Raises ValidationError if token is expired or user is underage.
        """
        try:
            attempt = SignupAttempt.objects.get(signup_token=signup_token)
        except SignupAttempt.DoesNotExist:
            raise ValidationError("SIGNUP_TOKEN_EXPIRED")

        if attempt.expires_at < timezone.now():
            raise ValidationError("SIGNUP_TOKEN_EXPIRED")

        # Age check
        today = timezone.now().date()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        if age < 18:
            raise ValidationError("UNDERAGE")

        # Create user
        user = User.objects.create_user(
            email=attempt.email,
            password=None,
            full_name=full_name,
            birth_date=birth_date
        )
        user.password = attempt.encrypted_password
        user.save()

        # Delete attempt
        attempt.delete()

        return user
