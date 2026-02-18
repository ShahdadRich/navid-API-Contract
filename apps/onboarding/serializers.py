from rest_framework import serializers
from .models import OnboardingProgress

class OnboardingProgressSerializer(serializers.ModelSerializer):
    onboardingComplete = serializers.BooleanField(source="user.onboarding_complete", read_only=True)

    class Meta:
        model = OnboardingProgress
        fields = ["intent", "goals", "onboardingComplete"]
