from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from accounts.auth_service import (
    complete_otp_verification,
    login_with_password,
    logout_user,
    request_otp,
    start_registration,
)
from accounts.exceptions import AuthServiceError
from accounts.serializers import (
    AddressSerializer,
    LoginSerializer,
    OtpRequestSerializer,
    OtpVerifySerializer,
    RegisterSerializer,
    UserPublicSerializer,
)


def _error_response(exc: AuthServiceError) -> Response:
    return Response(
        {"detail": exc.message, "code": exc.code},
        status=exc.status_code,
    )


class RegisterView(APIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            message = start_registration(request=request, **serializer.validated_data)
        except AuthServiceError as exc:
            return _error_response(exc)
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": message}, status=status.HTTP_200_OK)


class LoginView(APIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = login_with_password(request=request, **serializer.validated_data)
            user = result["user"]
        except AuthServiceError as exc:
            return _error_response(exc)
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"user": UserPublicSerializer(user).data, "access": result["access"], "refresh": result["refresh"]}, status=status.HTTP_200_OK)


class LogoutView(APIView):
    serializer_class = OtpVerifySerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            logout_user(request, refresh_token=request.data.get("refresh"))
        except ImproperlyConfigured as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"detail": "خروج انجام شد."}, status=status.HTTP_200_OK)


class MeView(APIView):
    serializer_class = UserPublicSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"user": UserPublicSerializer(request.user).data})


class AddressListCreateView(APIView):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = AddressSerializer(request.user.addresses.all(), many=True).data
        return Response(data)

    def post(self, request):
        serializer = AddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        address = serializer.save(user=request.user)
        return Response(AddressSerializer(address).data, status=status.HTTP_201_CREATED)


class AddressDetailView(APIView):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        from accounts.models import Address
        return get_object_or_404(Address, pk=pk, user=request.user)

    def get(self, request, pk):
        return Response(AddressSerializer(self.get_object(request, pk)).data)

    def put(self, request, pk):
        address = self.get_object(request, pk)
        serializer = AddressSerializer(address, data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(AddressSerializer(serializer.save()).data)

    def delete(self, request, pk):
        self.get_object(request, pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OtpRequestView(APIView):
    serializer_class = OtpRequestSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OtpRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            message = request_otp(request=request, **serializer.validated_data)
        except AuthServiceError as exc:
            return _error_response(exc)
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": message}, status=status.HTTP_200_OK)


class OtpVerifyView(APIView):
    serializer_class = OtpVerifySerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OtpVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = complete_otp_verification(request=request, **serializer.validated_data)
        except AuthServiceError as exc:
            return _error_response(exc)
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        body = {"detail": "تأیید انجام شد."}
        if user is not None:
            body["user"] = UserPublicSerializer(user).data
        return Response(body, status=status.HTTP_200_OK)


@extend_schema(exclude=True)
@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfCookieView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"detail": "CSRF cookie set."})
