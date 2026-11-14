from django.contrib.admin.sites import site
from django.test import TestCase
from django.urls import reverse

from accounts.admin import CustomUserAdmin
from accounts.models import PhoneOTP, User


class AdminConfigTests(TestCase):
    def test_user_admin_uses_phone_number_not_username(self):
        admin = site._registry[User]
        self.assertIsInstance(admin, CustomUserAdmin)
        self.assertEqual(admin.ordering, ("phone_number",))
        self.assertIn("phone_number", admin.list_display)
        self.assertIn("phone_number", admin.search_fields)
        add_fields = admin.add_fieldsets[0][1]["fields"]
        self.assertIn("phone_number", add_fields)
        self.assertNotIn("username", add_fields)

    def test_admin_add_page_loads(self):
        user = User.objects.create_superuser(
            phone_number="09120000009",
            password="SecurePass123!",
        )
        self.client.force_login(user)
        url = reverse("admin:accounts_user_add")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "phone_number")
        self.assertNotContains(response, 'name="username"')

    def test_phone_otp_admin_is_read_only(self):
        admin = site._registry[PhoneOTP]
        request = type("Request", (), {"user": User()})()
        self.assertFalse(admin.has_add_permission(request))
        self.assertFalse(admin.has_change_permission(request))
