from django.urls import path
from .views import PaymentCreateView, SimulatedCallbackView

urlpatterns = [
    path("", PaymentCreateView.as_view(), name="payment-create"),
    path("callback/", SimulatedCallbackView.as_view(), name="payment-callback"),
]
