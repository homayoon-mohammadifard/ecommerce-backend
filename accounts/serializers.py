from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from accounts.models import Address, PhoneOTP, User
from accounts.validators import validate_phone_number


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "phone_number",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "phone_verified",
        )
        read_only_fields = fields


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        exclude = ("user",)
        read_only_fields = ("id", "created_at", "updated_at")


class RegisterSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    first_name = serializers.CharField(required=False, allow_blank=True, default="")
    last_name = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_phone_number(self, value: str) -> str:
        return validate_phone_number(value)

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def validate(self, attrs):
        email = attrs.get("email")
        if email == "":
            attrs["email"] = None
        return attrs


class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_phone_number(self, value: str) -> str:
        return validate_phone_number(value)


class OtpRequestSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    purpose = serializers.ChoiceField(choices=PhoneOTP.Purpose.choices)

    def validate_phone_number(self, value: str) -> str:
        return validate_phone_number(value)


class OtpVerifySerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    purpose = serializers.ChoiceField(choices=PhoneOTP.Purpose.choices)
    code = serializers.CharField()

    def validate_phone_number(self, value: str) -> str:
        return validate_phone_number(value)
