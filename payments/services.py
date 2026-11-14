from uuid import uuid4
from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import ValidationError
from orders.models import Order
from .models import Payment, PaymentEvent

@transaction.atomic
def create_payment(*, user, order_id):
    order = Order.objects.select_for_update().filter(pk=order_id, user=user).first()
    if order is None or order.status != Order.Status.PENDING:
        raise ValidationError("Order is not payable.")
    payment, created = Payment.objects.get_or_create(order=order, defaults={"amount": order.total, "reference": f"PAY-{uuid4().hex}"})
    if not created and payment.status != Payment.Status.PENDING:
        raise ValidationError("Payment was already processed.")
    return payment

@transaction.atomic
def complete_simulated_payment(*, reference, success=True, event_id=None):
    payment = Payment.objects.select_for_update().select_related("order").filter(reference=reference).first()
    if payment is None:
        raise ValidationError("Invalid payment reference.")
    if event_id and PaymentEvent.objects.filter(event_id=event_id).exists():
        return payment
    if payment.status != Payment.Status.PENDING:
        return payment
    if event_id:
        PaymentEvent.objects.create(event_id=event_id, payment=payment, payload={"success": success})
    if success:
        for item in payment.order.items.all():
            updated = item.variant.__class__.objects.filter(pk=item.variant_id, stock_quantity__gte=item.quantity).update(stock_quantity=F("stock_quantity") - item.quantity)
            if updated != 1:
                raise ValidationError("Stock is no longer available.")
    payment.status = Payment.Status.SUCCEEDED if success else Payment.Status.FAILED
    payment.save(update_fields=("status", "updated_at"))
    if success:
        payment.order.status = Order.Status.PAID
        payment.order.save(update_fields=("status", "updated_at"))
    return payment
