from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):

    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("شماره تماس را وارد کنید.")
        if not password:
            raise ValueError('رمز عبور را وارد کنید')
        user = self.model(phone_number=phone_number,**extra_fields,)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", User.Role.MANAGER)

        return self.create_user(phone_number=phone_number,password=password,**extra_fields,)


class User(AbstractBaseUser, PermissionsMixin):

    class Role(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        MANAGER = "manager", "Manager"

    phone_number = models.CharField(max_length=15,unique=True,)
    email = models.EmailField(unique=True,null=True,blank=True,)
    first_name = models.CharField(max_length=100,blank=True,)
    last_name = models.CharField(max_length=100,blank=True,)
    role = models.CharField(max_length=20,choices=Role.choices,default=Role.CUSTOMER,)
    is_active = models.BooleanField(default=True,)
    is_staff = models.BooleanField(default=False,)
    created_at = models.DateTimeField(auto_now_add=True,)
    updated_at = models.DateTimeField(auto_now=True,)
    objects = UserManager()

    USERNAME_FIELD = "phone_number"

    def __str__(self):
        return self.phone_number