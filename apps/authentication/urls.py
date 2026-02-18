from django.urls import path
from .views import (
    SignupStartView, SignupResendCodeView, SignupVerifyView, SignupCompleteView,
    LoginView, MeView, LogoutView, ForgotPasswordView, ResetPasswordView
)

urlpatterns = [
    path("signup/start", SignupStartView.as_view(), name="signup-start"),
    path("signup/resend-code", SignupResendCodeView.as_view(), name="signup-resend-code"),
    path("signup/verify-code", SignupVerifyView.as_view(), name="signup-verify-code"),
    path("signup/complete-profile", SignupCompleteView.as_view(), name="signup-complete-profile"),
    path("login", LoginView.as_view(), name="login"),
    path("me", MeView.as_view(), name="me"),
    path("logout", LogoutView.as_view(), name="logout"),
    path("forgot-password", ForgotPasswordView.as_view(), name="forgot-password"),
    path("reset-password", ResetPasswordView.as_view(), name="reset-password"),
]
