
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q


phone_validator = RegexValidator(regex=r"^09[0-9]{9}$",message="فرمت شماره موبایل نادرست است.",)


class UserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("شماره موبایل الزامی است.")

        phone_number = phone_number.strip()
        phone_validator(phone_number)
        extra_fields["email"] = (extra_fields.get("email") or "").strip().lower() or None

        if not password:
            raise ValueError("رمز عبور الزامی است.")

        user = self.model(
            phone_number=phone_number,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields["is_staff"] is not True:
            raise ValueError("سوپریوزر باید is_staff=True داشته باشد.")

        if extra_fields["is_superuser"] is not True:
            raise ValueError("سوپریوزر باید is_superuser=True داشته باشد.")
        if extra_fields["is_active"] is not True:
            raise ValueError("سوپریوزر باید is_active=True داشته باشد.")

        return self.create_user(phone_number=phone_number,password=password,**extra_fields,)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        MANAGER = "manager", "Manager"

    phone_number = models.CharField(max_length=11,unique=True,validators=[phone_validator],)

    email = models.EmailField(unique=True,null=True,blank=True,)

    first_name = models.CharField(
        max_length=100,
        blank=True,
    )

    last_name = models.CharField(
        max_length=100,
        blank=True,
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
    )

    is_active = models.BooleanField(default=True)
    phone_verified = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.phone_number


class PhoneOTP(models.Model):
    class Purpose(models.TextChoices):
        REGISTRATION = 'registration', 'Registration'
        PHONE_VERIFY = 'phone_verify', 'Phone verification'
    phone_number = models.CharField(max_length=11, validators=[phone_validator], db_index=True)
    purpose = models.CharField(max_length=30, choices=Purpose.choices, db_index=True)
    code_hmac = models.CharField(max_length=64)
    payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    superseded_at = models.DateTimeField(null=True, blank=True)
    attempt_count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("phone_number", "purpose"), condition=Q(consumed_at__isnull=True, superseded_at__isnull=True), name="accounts_one_active_phone_otp")]


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    title = models.CharField(max_length=80)
    receiver_name = models.CharField(max_length=120)
    phone_number = models.CharField(max_length=11, validators=[phone_validator])
    province = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    address_details = models.TextField()
    postal_code = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("user",), condition=Q(is_default=True), name="accounts_one_default_address")]

    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        return super().save(*args, **kwargs)
