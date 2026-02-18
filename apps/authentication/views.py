from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, throttling
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import SignupAttempt
from .serializers import (
    SignupStartSerializer, SignupVerifySerializer, SignupCompleteSerializer,
    LoginSerializer, UserSerializer, ForgotPasswordSerializer, PasswordResetSerializer
)
from .services import AuthService
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError, APIException

class UnderageException(APIException):
    status_code = 422
    default_detail = "You must be at least 18 years old to use Navid AI."
    default_code = "UNDERAGE"

class SignupResendCodeView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [throttling.ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        # Mock implementation: validate token exists at least
        signup_token = request.data.get("signupToken")
        if not signup_token or not SignupAttempt.objects.filter(signup_token=signup_token).exists():
            return Response({
                "message": "Signup token expired or invalid",
                "code": "SIGNUP_TOKEN_EXPIRED",
                "details": {}
            }, status=status.HTTP_410_GONE)
        return Response(status=status.HTTP_204_NO_CONTENT)

class SignupStartView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [throttling.ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = SignupStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            attempt = AuthService.start_signup(
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"]
            )
        except DjangoValidationError as e:
            if e.message == "EMAIL_ALREADY_EXISTS":
                return Response({
                    "message": "Email already exists",
                    "code": "EMAIL_ALREADY_EXISTS",
                    "details": {}
                }, status=status.HTTP_409_CONFLICT)
            raise e

        return Response({
            "signupToken": attempt.signup_token,
            "email": attempt.email,
            "verification": {
                "channel": "email",
                "codeLength": 6,
                "expiresAt": attempt.expires_at.isoformat().replace("+00:00", "Z"),
                "resendAvailableAt": (attempt.created_at + timezone.timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
            }
        }, status=status.HTTP_201_CREATED)

class SignupVerifyView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [throttling.ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = SignupVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            attempt = AuthService.verify_code(
                signup_token=serializer.validated_data["signup_token"],
                code=serializer.validated_data["code"]
            )
        except DjangoValidationError as e:
            code = "INVALID_CODE"
            status_code = status.HTTP_400_BAD_REQUEST
            if e.message == "CODE_EXPIRED":
                code = "CODE_EXPIRED"
                status_code = status.HTTP_410_GONE
            elif e.message == "INVALID_TOKEN":
                code = "INVALID_TOKEN"
                status_code = status.HTTP_400_BAD_REQUEST

            return Response({
                "message": e.message,
                "code": code,
                "details": {}
            }, status=status_code)

        return Response({
            "signupToken": attempt.signup_token,
            "emailVerified": True
        }, status=status.HTTP_200_OK)

class SignupCompleteView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [throttling.ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = SignupCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = AuthService.complete_signup(
                signup_token=serializer.validated_data["signup_token"],
                full_name=serializer.validated_data["full_name"],
                birth_date=serializer.validated_data["birth_date"]
            )
        except DjangoValidationError as e:
            if e.message == "UNDERAGE":
                raise UnderageException()
            if e.message == "SIGNUP_TOKEN_EXPIRED":
                return Response({
                    "message": "Signup token expired",
                    "code": "SIGNUP_TOKEN_EXPIRED",
                    "details": {}
                }, status=status.HTTP_410_GONE)
            raise e

        login(request, user)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [throttling.ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"]
        )

        if not user:
            return Response({
                "message": "Invalid credentials",
                "code": "INVALID_CREDENTIALS",
                "details": {}
            }, status=status.HTTP_401_UNAUTHORIZED)

        login(request, user)
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)

class MeView(APIView):
    permission_classes = [permissions.AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        if not request.user.is_authenticated:
            return Response(None, status=status.HTTP_200_OK)
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)

class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)

class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [throttling.ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        # Implementation omitted as per blueprint (send mock email)
        return Response(status=status.HTTP_204_NO_CONTENT)

class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [throttling.ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        # Implementation omitted as per blueprint
        return Response(status=status.HTTP_204_NO_CONTENT)
