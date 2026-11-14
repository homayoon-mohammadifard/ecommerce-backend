from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import PaymentSerializer
from .services import complete_simulated_payment, create_payment
from .providers import verify_callback_signature

class PaymentCreateView(APIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        payment = create_payment(user=request.user, order_id=request.data.get("order"))
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

class SimulatedCallbackView(APIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        if not verify_callback_signature(request.body, request.headers.get("X-Payment-Signature", "")):
            return Response({"detail": "Invalid signature."}, status=status.HTTP_400_BAD_REQUEST)
        success = request.data.get("success") is True or str(request.data.get("success", "")).lower() == "true"
        payment = complete_simulated_payment(reference=request.data.get("reference"), success=success, event_id=request.data.get("event_id"))
        return Response(PaymentSerializer(payment).data)
