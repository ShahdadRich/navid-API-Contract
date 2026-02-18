from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import OnboardingProgress
from .serializers import OnboardingProgressSerializer
from apps.authentication.serializers import UserSerializer

class OnboardingProgressView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        progress, created = OnboardingProgress.objects.get_or_create(user=request.user)
        serializer = OnboardingProgressSerializer(progress, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

class OnboardingCompleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        progress, created = OnboardingProgress.objects.get_or_create(user=request.user)
        serializer = OnboardingProgressSerializer(progress, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        user = request.user
        user.onboarding_complete = True
        user.save()

        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
