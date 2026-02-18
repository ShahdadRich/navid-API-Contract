from django.urls import path
from .views import OnboardingProgressView, OnboardingCompleteView

urlpatterns = [
    path("progress", OnboardingProgressView.as_view(), name="onboarding-progress"),
    path("complete", OnboardingCompleteView.as_view(), name="onboarding-complete"),
]
