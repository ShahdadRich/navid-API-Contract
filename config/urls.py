from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.authentication.urls")),
    path("api/v1/onboarding/", include("apps.onboarding.urls")),
    path("api/v1/chat/", include("apps.chat.urls")),
]
