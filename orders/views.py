from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Address
from .models import Order
from .serializers import OrderSerializer
from .services import checkout


class OrderListView(APIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(user=request.user).prefetch_related("items")
        return Response(OrderSerializer(orders, many=True).data)


class OrderDetailView(APIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        order = get_object_or_404(Order.objects.prefetch_related("items"), pk=pk, user=request.user)
        return Response(OrderSerializer(order).data)


class CheckoutView(APIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        address = get_object_or_404(Address, pk=request.data.get("address"), user=request.user)
        order = checkout(user=request.user, address={"title": address.title, "receiver_name": address.receiver_name, "phone_number": address.phone_number, "province": address.province, "city": address.city, "address_details": address.address_details, "postal_code": address.postal_code})
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class CancelOrderView(APIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, user=request.user)
        if order.status != Order.Status.PENDING:
            return Response({"detail": "Only pending orders can be cancelled."}, status=status.HTTP_400_BAD_REQUEST)
        order.status = Order.Status.CANCELLED
        order.save(update_fields=("status", "updated_at"))
        return Response(OrderSerializer(order).data)
