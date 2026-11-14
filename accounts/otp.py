
from __future__ import annotations

import hashlib
import hmac
import secrets

from django.db import connection
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from accounts.exceptions import InvalidOtp, RateLimited, SmsDeliveryError
from accounts.models import PhoneOTP
from accounts.sms import get_sms_provider
from accounts.throttling import check_otp_issue_limits, get_client_ip
from accounts.validators import validate_phone_number


GENERIC_OTP_REQUEST_MESSAGE = ("اگر شماره واجد شرایط باشد، کد تأیید ارسال می‌شود.")


def _otp_pepper() -> bytes:
    pepper = getattr(settings, "OTP_PEPPER", "") or settings.SECRET_KEY

    if not pepper:
        raise ImproperlyConfigured("OTP_PEPPER یا SECRET_KEY باید تنظیم شود.")

    return pepper.encode("utf-8")


def _otp_config(name: str, default: int, *, minimum: int = 1) -> int:
    try:
        value = int(getattr(settings, name, default))
    except (TypeError, ValueError) as exc:
        raise ImproperlyConfigured(
            f"مقدار {name} باید یک عدد صحیح باشد."
        ) from exc

    if value < minimum:
        raise ImproperlyConfigured(
            f"مقدار {name} باید حداقل {minimum} باشد."
        )

    return value


def _code_length() -> int:
    length = _otp_config("OTP_CODE_LENGTH", 6)

    if length > 9:
        raise ImproperlyConfigured(
            "OTP_CODE_LENGTH نباید بیشتر از 9 باشد."
        )

    return length


def _ttl() -> int:
    return _otp_config("OTP_TTL_SECONDS", 120)


def _max_attempts() -> int:
    return _otp_config("OTP_MAX_ATTEMPTS", 5)


def _resend_cooldown() -> int:
    return _otp_config("OTP_RESEND_COOLDOWN_SECONDS", 60, minimum=0)


def _validate_purpose(purpose: str) -> str:
    valid_purposes = PhoneOTP.Purpose.values

    if purpose not in valid_purposes:
        raise InvalidOtp()

    return purpose


def generate_otp_code() -> str:
    length = _code_length()
    return f"{secrets.randbelow(10 ** length):0{length}d}"


def hash_otp_code(phone_number: str, purpose: str, code: str) -> str:
    message = f"{phone_number}|{purpose}|{code}".encode("utf-8")

    return hmac.new(
        _otp_pepper(),
        message,
        hashlib.sha256,
    ).hexdigest()


def _active_otp_qs(phone_number: str, purpose: str):
    return PhoneOTP.objects.filter(
        phone_number=phone_number,
        purpose=purpose,
        consumed_at__isnull=True,
        superseded_at__isnull=True,
    )



def _lock_otp_key(phone_number: str, purpose: str) -> None:
    if connection.vendor != 'postgresql':
        return
    digest = hashlib.blake2b(f'{phone_number}|{purpose}'.encode(), digest_size=8).digest()
    lock_id = int.from_bytes(digest, byteorder='big', signed=True)
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_advisory_xact_lock(%s)', [lock_id])

def issue_otp(
    *,
    phone_number: str,
    purpose: str,
    payload: dict | None = None,
    request=None,
    send_message: bool = True,
) -> PhoneOTP:
    phone_number = validate_phone_number(phone_number)
    purpose = _validate_purpose(purpose)

    if payload is not None and not isinstance(payload, dict):
        raise ValueError("payload باید یک دیکشنری یا None باشد.")

    ip_address = get_client_ip(request) if request is not None else ""
    now = timezone.now()

    # اعتبارسنجی تنظیمات قبل از ایجاد رکورد.
    ttl = _ttl()
    max_attempts = _max_attempts()
    cooldown = _resend_cooldown()
    code = generate_otp_code()

    check_otp_issue_limits(
        phone_number=phone_number,
        ip_address=ip_address,
        now=now,
    )

    with transaction.atomic():
        _lock_otp_key(phone_number, purpose)
        latest = (
            _active_otp_qs(phone_number, purpose)
            .select_for_update()
            .order_by("-created_at")
            .first()
        )

        if latest is not None and latest.expires_at > now:
            elapsed = (now - latest.created_at).total_seconds()
            if elapsed < cooldown:
                raise RateLimited()

        # هر کد قبلیِ مصرف‌نشده را از چرخه اعتبار خارج کن.
        _active_otp_qs(phone_number, purpose).update(
            superseded_at=now
        )

        otp = PhoneOTP.objects.create(
            phone_number=phone_number,
            purpose=purpose,
            code_hmac=hash_otp_code(phone_number, purpose, code),
            payload=payload,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl),
            attempt_count=0,
        )

    if send_message:
        try:
            get_sms_provider().send(phone_number, f'کد تأیید شما: {code}')
        except Exception as exc:
            PhoneOTP.objects.filter(pk=otp.pk, consumed_at__isnull=True).update(superseded_at=timezone.now())
            raise SmsDeliveryError() from exc

    return otp


def verify_otp(
    *,
    phone_number: str,
    purpose: str,
    code: str,
) -> PhoneOTP:
    phone_number = validate_phone_number(phone_number)
    purpose = _validate_purpose(purpose)
    submitted = str(code).strip()
    now = timezone.now()
    max_attempts = _max_attempts()

    failure: Exception | None = None
    verified_otp: PhoneOTP | None = None

    with transaction.atomic():
        otp = (
            _active_otp_qs(phone_number, purpose)
            .select_for_update()
            .order_by("-created_at")
            .first()
        )

        if otp is None or now >= otp.expires_at:
            failure = InvalidOtp()

        elif otp.attempt_count >= max_attempts:
            failure = RateLimited()

        else:
            expected = hash_otp_code(
                phone_number,
                purpose,
                submitted,
            )

            if not hmac.compare_digest(otp.code_hmac, expected):
                # افزایش شمارنده باید commit شود؛
                # پس از این بلوک خطا را بالا می‌فرستیم.
                PhoneOTP.objects.filter(pk=otp.pk).update(
                    attempt_count=F("attempt_count") + 1
                )

                otp.refresh_from_db(fields=["attempt_count"])

                if otp.attempt_count >= max_attempts:
                    failure = RateLimited()
                else:
                    failure = InvalidOtp()

            else:
                updated = PhoneOTP.objects.filter(
                    pk=otp.pk,
                    consumed_at__isnull=True,
                    superseded_at__isnull=True,
                    expires_at__gt=now,
                    attempt_count__lt=max_attempts,
                ).update(consumed_at=now)

                if updated != 1:
                    failure = InvalidOtp()
                else:
                    otp.consumed_at = now
                    verified_otp = otp

    if failure is not None:
        raise failure

    if verified_otp is None:
        raise InvalidOtp()

    return verified_otp
