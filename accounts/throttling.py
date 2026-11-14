from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from accounts.exceptions import RateLimited
from accounts.models import PhoneOTP


def get_client_ip(request) -> str:
    return request.META.get("REMOTE_ADDR") or ""


def _login_window() -> int:
    return int(getattr(settings, "LOGIN_FAILURE_WINDOW_SECONDS", 15 * 60))


def _login_max() -> int:
    return int(getattr(settings, "LOGIN_MAX_FAILURES", 5))


def login_failure_keys(phone_number: str, ip_address: str) -> tuple[str, str]:
    return (
        f"login-fail:phone:{phone_number}",
        f"login-fail:ip:{ip_address}",
    )


def assert_login_not_blocked(phone_number: str, ip_address: str) -> None:
    phone_key, ip_key = login_failure_keys(phone_number, ip_address)
    phone_count = cache.get(phone_key, 0)
    ip_count = cache.get(ip_key, 0)
    if phone_count >= _login_max() or ip_count >= _login_max() * 2:
        raise RateLimited()


def record_login_failure(phone_number: str, ip_address: str) -> None:
    window = _login_window()
    phone_key, ip_key = login_failure_keys(phone_number, ip_address)
    if cache.add(phone_key, 1, window):
        pass
    else:
        try:
            cache.incr(phone_key)
        except ValueError:
            cache.set(phone_key, 1, window)
    if cache.add(ip_key, 1, window):
        pass
    else:
        try:
            cache.incr(ip_key)
        except ValueError:
            cache.set(ip_key, 1, window)


def clear_login_failures(phone_number: str, ip_address: str) -> None:
    phone_key, ip_key = login_failure_keys(phone_number, ip_address)
    cache.delete_many([phone_key, ip_key])


def check_otp_issue_limits(*, phone_number: str, ip_address: str, now=None) -> None:
    now = now or timezone.now()
    hour_ago = now - timedelta(hours=1)
    per_phone = int(getattr(settings, "OTP_MAX_PER_PHONE_PER_HOUR", 5))
    per_ip = int(getattr(settings, "OTP_MAX_PER_IP_PER_HOUR", 10))

    phone_count = PhoneOTP.objects.filter(
        phone_number=phone_number,
        created_at__gte=hour_ago,
    ).count()
    if phone_count >= per_phone:
        raise RateLimited()

    if ip_address:
        ip_key = f"otp-issue:ip:{ip_address}"
        count = cache.get(ip_key, 0)
        if count >= per_ip:
            raise RateLimited()
        if cache.add(ip_key, 1, 60 * 60):
            pass
        else:
            try:
                cache.incr(ip_key)
            except ValueError:
                cache.set(ip_key, 1, 60 * 60)
