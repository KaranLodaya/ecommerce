from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Order, Payment
import random
import string

# This function sends the order confirmation email
def send_confirmation_email(order, payment_method, transaction_id=None):
    subject = f"Order Confirmation - {order.order_number}"

    message = f"""
    Dear {order.user},

    Thank you for your order! Your order number is {order.order_number}.
    
    Order Details:
    """

    for item in order.items.all():  # Assuming `order.items` gives the related order items
        message += f"{item.product.name}: Qty {item.quantity}, Price ₹{item.price}\n"
    
    message += f"""
    Subtotal: ₹{order.subtotal}
    Shipping: ₹{order.shipping}
    Total: ₹{order.total}
    
    The products will be shipped to:
    {order.shipping_address}

    Payment Method: {payment_method}
    """

    if transaction_id:
        message += f"Transaction ID: {transaction_id}"

    message += """
    You will receive further updates on your order soon.

    Thank you for shopping with us!

    Best Regards,
    UrbanCart
    """

    from_email = settings.EMAIL_HOST_USER
    recipient_list = [order.user.email]

    send_mail(subject, message, from_email, recipient_list, fail_silently=False)



# Signal receiver that listens for order status placed
@receiver(post_save, sender=Order)
def send_order_confirmation(sender, instance, created, **kwargs):
    # Ensure the order was updated, not created
    if not created:
        # Check if the status was updated to 'placed'
        if instance.status == 'placed' and instance.status != instance.__class__.objects.get(id=instance.id).status:
            # Fetch the payment method and transaction ID
            payment_method = instance.payment.payment_method if instance.payment else 'Cash on Delivery'
            transaction_id = instance.payment.transaction_id if instance.payment else None

            # Send confirmation email
            send_confirmation_email(instance, payment_method, transaction_id)






def generate_tracking_number():
    """Generate a random tracking number."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

@receiver(post_save, sender=Payment)
def create_tracking_number(sender, instance, created, **kwargs):
    """
    Signal to create a tracking number when the payment status is marked as 'completed'.
    """
    if instance.status == 'completed':
        order = instance.order
        if not order.tracking_number:  # Avoid overwriting if already exists
            order.tracking_number = generate_tracking_number()
            order.save()
            print(f"Tracking number created for order {order.order_number}: {order.tracking_number}")
