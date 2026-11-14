from decimal import Decimal
from uuid import uuid4

from django.db import transaction
from rest_framework.exceptions import ValidationError

from cart.models import Cart
from .models import Order, OrderItem


@transaction.atomic
def checkout(*, user, address):
    cart = Cart.objects.select_for_update().prefetch_related("items__variant__product").filter(user=user).first()
    if not cart or not cart.items.exists():
        raise ValidationError("Cart is empty.")
    subtotal = Decimal("0")
    items = []
    for item in cart.items.all():
        variant = item.variant
        if not variant.is_active or not variant.product.is_active or item.quantity > variant.stock_quantity:
            raise ValidationError("A cart item is unavailable or out of stock.")
        line_total = variant.price * item.quantity
        subtotal += line_total
        items.append((item, variant, line_total))
    order = Order.objects.create(user=user, order_number=f"ORD-{uuid4().hex[:20].upper()}", shipping_address=address, subtotal=subtotal, total=subtotal)
    OrderItem.objects.bulk_create([OrderItem(order=order, variant=variant, product_name=variant.product.name, sku=variant.sku, variant_attributes=variant.attributes, unit_price=variant.price, quantity=item.quantity, line_total=line_total) for item, variant, line_total in items])
    cart.items.all().delete()
    return order
