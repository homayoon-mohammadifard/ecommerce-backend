from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import User


class UserManagerTests(TestCase):
    def test_create_user_hashes_password(self):
        user = User.objects.create_user(
            phone_number="09123456789",
            password="SecurePass123!",
            first_name="Ali",
        )
        self.assertNotEqual(user.password, "SecurePass123!")
        self.assertTrue(user.check_password("SecurePass123!"))
        self.assertFalse(user.check_password("wrong-password"))
        self.assertEqual(user.role, User.Role.CUSTOMER)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_missing_phone_number_is_rejected(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(phone_number="", password="SecurePass123!")

    def test_invalid_phone_format_is_rejected(self):
        with self.assertRaises(ValidationError):
            User.objects.create_user(
                phone_number="+989123456789",
                password="SecurePass123!",
            )
        with self.assertRaises(ValidationError):
            User.objects.create_user(
                phone_number="0912345678",
                password="SecurePass123!",
            )

    def test_phone_whitespace_is_trimmed_but_not_rewritten(self):
        user = User.objects.create_user(
            phone_number=" 09123456789 ",
            password="SecurePass123!",
        )
        self.assertEqual(user.phone_number, "09123456789")

    def test_duplicate_phone_number_is_rejected(self):
        User.objects.create_user(
            phone_number="09123456789",
            password="SecurePass123!",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    phone_number="09123456789",
                    password="AnotherPass123!",
                )

    def test_empty_email_is_stored_as_null(self):
        user = User.objects.create_user(
            phone_number="09123456780",
            password="SecurePass123!",
            email="",
        )
        self.assertIsNone(user.email)

    def test_create_superuser_flags(self):
        user = User.objects.create_superuser(
            phone_number="09120000000",
            password="SecurePass123!",
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_contradictory_superuser_flags_are_rejected(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                phone_number="09120000001",
                password="SecurePass123!",
                is_staff=False,
            )
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                phone_number="09120000002",
                password="SecurePass123!",
                is_superuser=False,
            )
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                phone_number="09120000003",
                password="SecurePass123!",
                is_active=False,
            )

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user(phone_number='09120000010', password='SecurePass123!', email='User@Example.com')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(phone_number='09120000011', password='SecurePass123!', email='user@example.com')
