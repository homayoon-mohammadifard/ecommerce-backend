from __future__ import annotations

import sys
from typing import Protocol

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class SmsProvider(Protocol):
    def send(self, phone_number: str, message: str) -> None:
        ...


class ConsoleSmsProvider:
    def send(self, phone_number: str, message: str) -> None:
        sys.stdout.write(f"[SMS console] to={phone_number}\n{message}\n")
        sys.stdout.flush()


class NoOpSmsProvider:
    """Test provider. Does not deliver messages."""

    def send(self, phone_number: str, message: str) -> None:
        return None


def get_sms_provider() -> SmsProvider:
    name = getattr(settings, "SMS_PROVIDER", "console")
    providers: dict[str, type] = {
        "console": ConsoleSmsProvider,
        "noop": NoOpSmsProvider,
    }
    provider_cls = providers.get(name)
    if provider_cls is None:
        raise ImproperlyConfigured(
            "SMS_PROVIDER نامعتبر است. مقدارهای پشتیبانی‌شده: console, noop. "
            "برای ارسال واقعی باید ارائه‌دهندهٔ SMS جداگانه با اعتبارنامهٔ محیطی پیاده‌سازی شود."
        )
    return provider_cls()
