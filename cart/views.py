from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from store.models import ProductVariant
from .models import Cart, CartItem
from .serializers import CartSerializer


class CartView(APIView):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return Response(CartSerializer(cart).data)


class CartItemListView(APIView):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        variant = get_object_or_404(ProductVariant.objects.select_related("product"), pk=request.data.get("variant"), is_active=True, product__is_active=True)
        quantity = request.data.get("quantity")
        if not isinstance(quantity, int) or quantity < 1 or quantity > variant.stock_quantity:
            return Response({"detail": "Invalid quantity or insufficient stock."}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            cart, _ = Cart.objects.get_or_create(user=request.user)
            item, created = CartItem.objects.get_or_create(cart=cart, variant=variant, defaults={"quantity": quantity})
            if not created:
                if item.quantity + quantity > variant.stock_quantity:
                    return Response({"detail": "Insufficient stock."}, status=status.HTTP_400_BAD_REQUEST)
                item.quantity += quantity
                item.save(update_fields=("quantity", "updated_at"))
        return Response(CartSerializer(cart).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class CartItemDetailView(APIView):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, request, pk):
        return get_object_or_404(CartItem, pk=pk, cart__user=request.user)

    def patch(self, request, pk):
        item = self.get_object(request, pk)
        quantity = request.data.get("quantity")
        if not isinstance(quantity, int) or quantity < 1 or quantity > item.variant.stock_quantity:
            return Response({"detail": "Invalid quantity or insufficient stock."}, status=status.HTTP_400_BAD_REQUEST)
        item.quantity = quantity
        item.save(update_fields=("quantity", "updated_at"))
        return Response(CartSerializer(item.cart).data)

    def delete(self, request, pk):
        item = self.get_object(request, pk)
        cart = item.cart
        item.delete()
        return Response(CartSerializer(cart).data)


class CartClearView(APIView):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart.items.all().delete()
        return Response(CartSerializer(cart).data)
