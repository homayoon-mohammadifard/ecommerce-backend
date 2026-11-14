from __future__ import annotations

from typing import TypedDict
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework_simplejwt.exceptions import TokenError
from accounts.exceptions import DatabaseConflict, InvalidCredentials, InvalidOtp
from accounts.models import PhoneOTP, User
from accounts.otp import GENERIC_OTP_REQUEST_MESSAGE, issue_otp, verify_otp
from accounts.throttling import assert_login_not_blocked, clear_login_failures, get_client_ip, record_login_failure
from accounts.validators import validate_phone_number

class LoginResult(TypedDict):
    user: User
    access: str
    refresh: str

def start_registration(*, phone_number: str, password: str, request=None, first_name: str = '', last_name: str = '', email: str | None = None) -> str:
    phone_number = validate_phone_number(phone_number); validate_password(password)
    if User.objects.filter(phone_number=phone_number).exists(): return GENERIC_OTP_REQUEST_MESSAGE
    issue_otp(phone_number=phone_number, purpose=PhoneOTP.Purpose.REGISTRATION, payload={'password_hash': make_password(password), 'first_name': (first_name or '').strip(), 'last_name': (last_name or '').strip(), 'email': (email or '').strip() or None}, request=request)
    return GENERIC_OTP_REQUEST_MESSAGE

def request_otp(*, phone_number: str, purpose: str, request=None) -> str:
    phone_number = validate_phone_number(phone_number)
    if purpose not in PhoneOTP.Purpose.values: raise InvalidOtp()
    if purpose == PhoneOTP.Purpose.REGISTRATION:
        if User.objects.filter(phone_number=phone_number).exists(): return GENERIC_OTP_REQUEST_MESSAGE
        latest = PhoneOTP.objects.filter(phone_number=phone_number, purpose=purpose, consumed_at__isnull=True, superseded_at__isnull=True, expires_at__gt=timezone.now()).order_by('-created_at').first()
        if latest is not None and isinstance(latest.payload, dict): issue_otp(phone_number=phone_number, purpose=purpose, payload=latest.payload, request=request)
    elif purpose == PhoneOTP.Purpose.PHONE_VERIFY and User.objects.filter(phone_number=phone_number).exists():
        issue_otp(phone_number=phone_number, purpose=purpose, request=request)
    return GENERIC_OTP_REQUEST_MESSAGE

def complete_otp_verification(*, phone_number: str, purpose: str, code: str, request=None) -> User | None:
    if purpose not in PhoneOTP.Purpose.values: raise InvalidOtp()
    if purpose == PhoneOTP.Purpose.PHONE_VERIFY and getattr(request, 'user', None) is not None and request.user.is_authenticated and request.user.phone_number != phone_number:
        raise InvalidOtp()
    with transaction.atomic():
        otp = verify_otp(phone_number=phone_number, purpose=purpose, code=code)
        if purpose == PhoneOTP.Purpose.REGISTRATION:
            user = _create_user_from_registration_otp(otp)
            user.phone_verified = True
            user.save(update_fields=['phone_verified', 'updated_at'])
            return user
    if purpose == PhoneOTP.Purpose.PHONE_VERIFY:
        user = User.objects.filter(phone_number=otp.phone_number).first()
        if user is None: raise InvalidOtp()
        if getattr(request, 'user', None) is not None and request.user.is_authenticated and request.user.pk != user.pk:
            raise InvalidOtp()
        user.phone_verified = True
        user.save(update_fields=['phone_verified', 'updated_at'])
        return user if getattr(request, 'user', None) is not None and request.user.is_authenticated else None
    raise InvalidOtp()

def _create_user_from_registration_otp(otp: PhoneOTP) -> User:
    payload = otp.payload
    if not isinstance(payload, dict) or not isinstance(payload.get('password_hash'), str): raise InvalidOtp()
    try:
        with transaction.atomic():
            user = User.objects.filter(phone_number=otp.phone_number).first()
            if user is not None: return user
            user = User(phone_number=otp.phone_number, first_name=payload.get('first_name') or '', last_name=payload.get('last_name') or '', email=payload.get('email') or None, role=User.Role.CUSTOMER, is_active=True, is_staff=False, is_superuser=False)
            user.password = payload['password_hash']; user.save(force_insert=True); return user
    except IntegrityError:
        existing = User.objects.filter(phone_number=otp.phone_number).first()
        if existing is not None:
            return existing
        raise DatabaseConflict()

def _jwt_tokens(user: User) -> tuple[str, str]:
    try: from rest_framework_simplejwt.tokens import RefreshToken
    except ImportError as exc: raise ImproperlyConfigured('djangorestframework-simplejwt is required for JWT authentication.') from exc
    token = RefreshToken.for_user(user); return str(token.access_token), str(token)

def login_with_password(*, phone_number: str, password: str, request=None) -> LoginResult:
    phone_number = validate_phone_number(phone_number); ip_address = get_client_ip(request) if request is not None else ''
    assert_login_not_blocked(phone_number, ip_address); user = authenticate(request, phone_number=phone_number, password=password)
    if user is None or not user.is_active: record_login_failure(phone_number, ip_address); raise InvalidCredentials()
    clear_login_failures(phone_number, ip_address); access, refresh = _jwt_tokens(user); return {'user': user, 'access': access, 'refresh': refresh}

def logout_user(request=None, *, refresh_token: str | None = None) -> None:
    if not refresh_token: raise InvalidCredentials()
    try:
        from rest_framework_simplejwt.tokens import RefreshToken
        token = RefreshToken(refresh_token)
        if request is not None and str(token.get('user_id')) != str(request.user.pk):
            raise InvalidCredentials()
        token.blacklist()
    except ImportError as exc:
        raise ImproperlyConfigured('JWT blacklist support is not configured.') from exc
    except (TokenError, ValueError) as exc:
        raise InvalidCredentials() from exc
