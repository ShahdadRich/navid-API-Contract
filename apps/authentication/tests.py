from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.core.cache import cache
from .models import User, SignupAttempt
from django.utils import timezone
from datetime import date

class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        cache.clear()

    def test_signup_flow(self):
        # 1. Start Signup
        response = self.client.post("/api/v1/auth/signup/start", {
            "email": "test@example.com",
            "password": "StrongPassword123!"
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        signup_token = response.data["signupToken"]
        self.assertEqual(response.data["email"], "test@example.com")

        # 2. Verify Code
        response = self.client.post("/api/v1/auth/signup/verify-code", {
            "signupToken": signup_token,
            "code": "123456"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["emailVerified"])

        # 3. Complete Profile - Underage
        response = self.client.post("/api/v1/auth/signup/complete-profile", {
            "signupToken": signup_token,
            "fullName": "Young User",
            "birthDate": str(date.today().replace(year=date.today().year - 17))
        })
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["code"], "UNDERAGE")

        # 4. Complete Profile - Success
        response = self.client.post("/api/v1/auth/signup/complete-profile", {
            "signupToken": signup_token,
            "fullName": "Adult User",
            "birthDate": "1990-01-01"
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Adult User")
        self.assertEqual(response.data["onboardingComplete"], False)

        # Verify user created
        user = User.objects.get(email="test@example.com")
        self.assertEqual(user.full_name, "Adult User")

        # 5. Session Check (Me)
        response = self.client.get("/api/v1/auth/me")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "test@example.com")

        # 6. Logout
        response = self.client.post("/api/v1/auth/logout")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # 7. Me after logout
        response = self.client.get("/api/v1/auth/me")
        self.assertEqual(response.data, None)

    def test_validation_error_format(self):
        # Invalid email
        response = self.client.post("/api/v1/auth/signup/start", {
            "email": "not-an-email",
            "password": "password"
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("message", response.data)
        self.assertEqual(response.data["code"], "VALIDATION_ERROR")
        self.assertIn("email", response.data["details"])

    def test_login(self):
        User.objects.create_user(email="login@example.com", password="password123", full_name="Login User")

        response = self.client.post("/api/v1/auth/login", {
            "email": "login@example.com",
            "password": "password123"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "login@example.com")

    def test_onboarding(self):
        user = User.objects.create_user(email="onboarding@example.com", password="password123", full_name="Onboarding User")
        self.client.force_authenticate(user=user)

        # Patch progress
        response = self.client.patch("/api/v1/onboarding/progress", {
            "intent": "work",
            "goals": ["code"]
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["intent"], "work")

        # Complete onboarding
        response = self.client.post("/api/v1/onboarding/complete", {
            "intent": "work",
            "goals": ["code", "data"]
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["onboardingComplete"], True)

        user.refresh_from_db()
        self.assertTrue(user.onboarding_complete)
