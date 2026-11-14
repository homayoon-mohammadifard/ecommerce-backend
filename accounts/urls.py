from django.urls import path

from accounts.views import (
    CsrfCookieView,
    AddressDetailView,
    AddressListCreateView,
    LoginView,
    LogoutView,
    MeView,
    OtpRequestView,
    OtpVerifyView,
    RegisterView,
)

urlpatterns = [
    path("csrf/", CsrfCookieView.as_view(), name="auth-csrf"),
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("addresses/", AddressListCreateView.as_view(), name="address-list-create"),
    path("addresses/<int:pk>/", AddressDetailView.as_view(), name="address-detail"),
    path("otp/request/", OtpRequestView.as_view(), name="auth-otp-request"),
    path("otp/verify/", OtpVerifyView.as_view(), name="auth-otp-verify"),
]
