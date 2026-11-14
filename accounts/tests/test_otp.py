import threading
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from accounts.exceptions import InvalidOtp, RateLimited, SmsDeliveryError
from accounts.models import PhoneOTP
from accounts.otp import hash_otp_code, issue_otp, verify_otp


@override_settings(SMS_PROVIDER="noop", OTP_PEPPER="test-otp-pepper")
class OtpServiceTests(TestCase):
    def _issue(self, now, phone="09123333333", purpose=PhoneOTP.Purpose.REGISTRATION, **kwargs):
        with patch("accounts.otp.timezone.now", return_value=now):
            with patch("accounts.otp.generate_otp_code", return_value=kwargs.pop("code", "123456")):
                return issue_otp(
                    phone_number=phone,
                    purpose=purpose,
                    send_message=False,
                    **kwargs,
                )

    def _verify(self, now, phone="09123333333", purpose=PhoneOTP.Purpose.REGISTRATION, code="123456"):
        with patch("accounts.otp.timezone.now", return_value=now):
            return verify_otp(phone_number=phone, purpose=purpose, code=code)

    def test_correct_otp_before_expiration_succeeds(self):
        now = timezone.now()
        otp = self._issue(now)
        self.assertNotEqual(otp.code_hmac, "123456")
        self.assertEqual(otp.code_hmac, hash_otp_code(otp.phone_number, otp.purpose, "123456"))
        verified = self._verify(now + timedelta(seconds=119))
        self.assertEqual(verified.pk, otp.pk)
        self.assertIsNotNone(verified.consumed_at)

    def test_incorrect_otp_fails(self):
        now = timezone.now()
        self._issue(now)
        with self.assertRaises(InvalidOtp):
            self._verify(now + timedelta(seconds=1), code="000000")

    def test_otp_fails_at_exactly_120_seconds(self):
        now = timezone.now()
        self._issue(now)
        with self.assertRaises(InvalidOtp):
            self._verify(now + timedelta(seconds=120))

    def test_otp_fails_after_120_seconds(self):
        now = timezone.now()
        self._issue(now)
        with self.assertRaises(InvalidOtp):
            self._verify(now + timedelta(seconds=121))

    def test_new_otp_invalidates_old_immediately(self):
        now = timezone.now()
        old = self._issue(now, code="111111")
        new = self._issue(now + timedelta(seconds=61), code="222222")
        old.refresh_from_db()
        self.assertIsNotNone(old.superseded_at)
        with self.assertRaises(InvalidOtp):
            self._verify(now + timedelta(seconds=62), code="111111")
        verified = self._verify(now + timedelta(seconds=62), code="222222")
        self.assertEqual(verified.pk, new.pk)

    def test_successful_otp_cannot_be_reused(self):
        now = timezone.now()
        self._issue(now)
        self._verify(now + timedelta(seconds=1))
        with self.assertRaises(InvalidOtp):
            self._verify(now + timedelta(seconds=2))

    def test_otp_cannot_be_used_for_another_phone_or_purpose(self):
        now = timezone.now()
        self._issue(now, phone="09123333333", purpose=PhoneOTP.Purpose.REGISTRATION)
        with self.assertRaises(InvalidOtp):
            self._verify(
                now + timedelta(seconds=1),
                phone="09124444444",
                purpose=PhoneOTP.Purpose.REGISTRATION,
            )
        with self.assertRaises(InvalidOtp):
            self._verify(
                now + timedelta(seconds=1),
                phone="09123333333",
                purpose=PhoneOTP.Purpose.PHONE_VERIFY,
            )

    def test_maximum_attempts_are_enforced(self):
        now = timezone.now()
        self._issue(now)
        for _ in range(4):
            with self.assertRaises(InvalidOtp):
                self._verify(now + timedelta(seconds=1), code="000000")
        with self.assertRaises(RateLimited):
            self._verify(now + timedelta(seconds=1), code="000000")
        with self.assertRaises(RateLimited):
            self._verify(now + timedelta(seconds=1), code="123456")

    def test_resend_cooldown_is_enforced(self):
        now = timezone.now()
        self._issue(now)
        with self.assertRaises(RateLimited):
            self._issue(now + timedelta(seconds=30), code="999999")

    def test_hourly_phone_limit_is_enforced(self):
        now = timezone.now()
        with override_settings(OTP_MAX_PER_PHONE_PER_HOUR=2, OTP_RESEND_COOLDOWN_SECONDS=0):
            self._issue(now)
            self._issue(now + timedelta(seconds=1), code="222222")
            with self.assertRaises(RateLimited):
                self._issue(now + timedelta(seconds=2), code="333333")


@override_settings(SMS_PROVIDER="noop", OTP_PEPPER="test-otp-pepper")
class ConcurrentOtpTests(TransactionTestCase):
    def test_concurrent_verification_consumes_otp_once(self):
        now = timezone.now()
        with patch("accounts.otp.timezone.now", return_value=now):
            with patch("accounts.otp.generate_otp_code", return_value="123456"):
                issue_otp(
                    phone_number="09125555555",
                    purpose=PhoneOTP.Purpose.REGISTRATION,
                    send_message=False,
                )

        results = []
        barrier = threading.Barrier(2)

        def attempt():
            barrier.wait(timeout=5)
            try:
                with patch("accounts.otp.timezone.now", return_value=now + timedelta(seconds=1)):
                    verify_otp(
                        phone_number="09125555555",
                        purpose=PhoneOTP.Purpose.REGISTRATION,
                        code="123456",
                    )
                results.append("ok")
            except InvalidOtp:
                results.append("fail")

        threads = [threading.Thread(target=attempt) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        self.assertEqual(results.count("ok"), 1)
        self.assertEqual(results.count("fail"), 1)
        self.assertEqual(
            PhoneOTP.objects.filter(
                phone_number="09125555555",
                consumed_at__isnull=False,
            ).count(),
            1,
        )


@override_settings(SMS_PROVIDER='console', OTP_PEPPER='test-otp-pepper')
class SmsDeliveryTests(TestCase):
    def test_delivery_failure_invalidates_otp(self):
        from unittest.mock import Mock
        now = timezone.now()
        provider = Mock()
        provider.send.side_effect = RuntimeError('provider unavailable')
        with patch('accounts.otp.get_sms_provider', return_value=provider), patch('accounts.otp.generate_otp_code', return_value='123456'):
            with self.assertRaises(SmsDeliveryError):
                issue_otp(phone_number='09126666666', purpose=PhoneOTP.Purpose.REGISTRATION)
        self.assertFalse(PhoneOTP.objects.filter(phone_number='09126666666', consumed_at__isnull=True, superseded_at__isnull=True).exists())
