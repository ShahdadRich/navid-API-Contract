from django.db import models
from django.conf import settings

class OnboardingProgress(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="onboarding_progress")
    intent = models.CharField(max_length=255, blank=True)
    goals = models.JSONField(default=list)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - Onboarding"
