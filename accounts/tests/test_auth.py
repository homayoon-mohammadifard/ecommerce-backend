from django.core.management import call_command
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from unittest.mock import patch

from accounts.models import User
from accounts.throttling import record_login_failure


@override_settings(SMS_PROVIDER="noop")
class RegistrationLoginTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        cache.clear()

    def _register(self, **kwargs):
        payload = {
            "phone_number": "09121111111",
            "password": "SecurePass123!",
            "first_name": "Sara",
            "last_name": "Ahmadi",
        }
        payload.update(kwargs)
        with patch("accounts.otp.generate_otp_code", return_value="123456"):
            return self.client.post("/api/auth/register/", payload, format="json")

    def _verify(self, phone="09121111111", code="123456", purpose="registration"):
        return self.client.post(
            "/api/auth/otp/verify/",
            {"phone_number": phone, "purpose": purpose, "code": code},
            format="json",
        )

    def test_successful_registration_requires_otp(self):
        response = self._register()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(phone_number="09121111111").exists())
        verify = self._verify()
        self.assertEqual(verify.status_code, 200)
        user = User.objects.get(phone_number="09121111111")
        self.assertEqual(user.role, User.Role.CUSTOMER)
        self.assertFalse(user.is_staff)
        self.assertTrue(user.phone_verified)
        self.assertTrue(user.check_password("SecurePass123!"))
        self.assertIn("user", verify.data)
        self.assertNotIn("password", verify.data["user"])

    def test_invalid_phone_number(self):
        response = self._register(phone_number="0912")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.exists())

    def test_duplicate_registration_is_generic(self):
        User.objects.create_user(
            phone_number="09121111111",
            password="SecurePass123!",
        )
        response = self._register()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(phone_number="09121111111").count(), 1)

    def test_weak_password_is_rejected(self):
        response = self._register(password="123")
        self.assertEqual(response.status_code, 400)

    def test_privileged_fields_from_public_input_are_ignored(self):
        with patch("accounts.otp.generate_otp_code", return_value="123456"):
            response = self.client.post(
                "/api/auth/register/",
                {
                    "phone_number": "09121111111",
                    "password": "SecurePass123!",
                    "role": "manager",
                    "is_staff": True,
                    "is_superuser": True,
                    "is_active": False,
                },
                format="json",
            )
        self.assertEqual(response.status_code, 200)
        verify = self._verify()
        self.assertEqual(verify.status_code, 200)
        user = User.objects.get(phone_number="09121111111")
        self.assertEqual(user.role, User.Role.CUSTOMER)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_successful_login(self):
        User.objects.create_user(
            phone_number="09121111111",
            password="SecurePass123!",
        )
        response = self.client.post(
            "/api/auth/login/",
            {"phone_number": "09121111111", "password": "SecurePass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["phone_number"], "09121111111")
        self.assertNotIn("password", response.data["user"])
        me = self.client.get("/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        self.assertEqual(me.status_code, 200)

    def test_incorrect_password(self):
        User.objects.create_user(
            phone_number="09121111111",
            password="SecurePass123!",
        )
        response = self.client.post(
            "/api/auth/login/",
            {"phone_number": "09121111111", "password": "WrongPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "invalid_credentials")

    def test_inactive_user_login_is_rejected(self):
        user = User.objects.create_user(
            phone_number="09121111111",
            password="SecurePass123!",
        )
        user.is_active = False
        user.save(update_fields=["is_active"])
        response = self.client.post(
            "/api/auth/login/",
            {"phone_number": "09121111111", "password": "SecurePass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "invalid_credentials")

    def test_login_rate_limit(self):
        User.objects.create_user(
            phone_number="09121111111",
            password="SecurePass123!",
        )
        for _ in range(5):
            record_login_failure("09121111111", "127.0.0.1")
        response = self.client.post(
            "/api/auth/login/",
            {"phone_number": "09121111111", "password": "SecurePass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 429)

    def test_sensitive_fields_are_not_exposed(self):
        User.objects.create_user(
            phone_number="09121111111",
            password="SecurePass123!",
        )
        response = self.client.post(
            "/api/auth/login/",
            {"phone_number": "09121111111", "password": "SecurePass123!"},
            format="json",
        )
        payload = str(response.content)
        self.assertNotIn("SecurePass123!", payload)
        self.assertNotIn(User.objects.get().password, payload)

    def test_manage_py_check_passes(self):
        call_command("check")
