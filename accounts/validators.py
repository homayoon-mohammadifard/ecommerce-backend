import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

IRAN_MOBILE_REGEX = r"^09[0-9]{9}$"
IRAN_MOBILE_PATTERN = re.compile(IRAN_MOBILE_REGEX)

PHONE_NUMBER_INVALID_MESSAGE = "فرمت شماره موبایل نادرست است."


phone_validator = RegexValidator(regex=IRAN_MOBILE_REGEX,message=PHONE_NUMBER_INVALID_MESSAGE,)


def normalize_phone_number(value: str | None) -> str:
    if value is None:
        raise ValidationError("شماره موبایل الزامی است.", code="required")
    return str(value).strip()


def validate_phone_number(value: str | None) -> str:
    phone_number = normalize_phone_number(value)
    if not phone_number:
        raise ValidationError("شماره موبایل الزامی است.", code="required")
    if IRAN_MOBILE_PATTERN.fullmatch(phone_number) is None:
        raise ValidationError(PHONE_NUMBER_INVALID_MESSAGE, code="invalid_phone")
    return phone_number
