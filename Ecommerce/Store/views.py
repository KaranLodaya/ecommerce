from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from .models import Category, Product, Cart, CartItem, Address, payment, Order
from django.contrib.auth.decorators import login_required
from decimal import Decimal, ROUND_HALF_UP
from .forms import AddressForm
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.core.exceptions import ObjectDoesNotExist  # Add this import
from django.db import IntegrityError, DatabaseError  # Add this import
from django.utils import timezone
from django.utils.crypto import get_random_string  # Add this import
from django.core.mail import send_mail
from django.conf import settings

# import stripe


# View for listing products
@login_required
def product_list(request):
    products = Product.objects.all()

    # Initialize an empty cart dictionary and cart item count
    cart = {}
    cart_item_count = 0

    if request.user.is_authenticated:
        # Get or create a cart for the logged-in user
        cart_obj, created = Cart.objects.get_or_create(user=request.user)

        # Build a dictionary with product IDs as keys and quantities as values
        cart = {item.product.id: item.quantity for item in cart_obj.items.all()}

        # Calculate the total quantity of items in the cart
        cart_item_count = sum(cart.values())

    # Add quantity to each product
    for product in products:
        product.quantity_in_cart = cart.get(
            product.id, 0
        )  # Default to 0 if not in cart

    # Pass products and cart item count to the template
    return render(
        request,
        "Store/product_list.html",
        {
            "products": products,
            "cart_item_count": cart_item_count,
        },
    )


# View for listing products by category
def product_list_by_category(request, category_id=None):
    if category_id:
        products = Product.objects.filter(category_id=category_id)
    else:
        products = Product.objects.all()
    return render(request, "Store/product_list.html", {"products": products})


# View for product details
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.user.is_authenticated:
        # Get or create a cart for the logged-in user
        cart_obj, created = Cart.objects.get_or_create(user=request.user)
        # Build a dictionary with product IDs as keys and quantities as values
        cart = {item.product.id: item.quantity for item in cart_obj.items.all()}
        # Calculate the total quantity of items in the cart
        cart_item_count = sum(cart.values())

    return render(
        request,
        "Store/product_detail.html",
        {
            "product": product,
            "cart_item_count": cart_item_count,
        },
    )


# View to add an item to the cart
@login_required
def add_to_cart(request, product_id):
    cart = get_object_or_404(Cart, user=request.user)
    product = get_object_or_404(Product, id=product_id)

    # Find the cart item
    cart_item = cart.items.filter(product=product).first()

    # import pdb;pdb.set_trace()
    if cart_item:
        cart_item.quantity += 1
        cart_item.save()
    else:
        cart_item = CartItem.objects.create(
            cart=cart, product=product, quantity=1
        )  # Add new item to the cart if it's not already present

    updated_quantity = cart_item.quantity

    # Calculate updated cart details
    total_price = sum(item.product.price * item.quantity for item in cart.items.all())
    shipping = Decimal("0.002") * total_price
    shipping = shipping.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = total_price + shipping
    cart_item_count = sum(
        item.quantity for item in cart.items.all()
    )  # Updated to reflect total quantity

    # Return updated response
    return JsonResponse(
        {
            "updated_quantity": updated_quantity,
            "total_price": total_price,
            "cart_item_count": cart_item_count,
            "shipping": shipping,
            "total": total,
        }
    )


@login_required
def remove_from_cart(request, product_id):
    cart = get_object_or_404(Cart, user=request.user)
    product = get_object_or_404(Product, id=product_id)

    # Find the cart item
    cart_item = cart.items.filter(product=product).first()

    if cart_item:
        # Decrement quantity or remove the item if it reaches 0
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
            updated_quantity = cart_item.quantity
        else:
            cart_item.delete()
            updated_quantity = 0  # Set quantity to 0 since item is deleted
    else:
        updated_quantity = 0

    # Calculate updated cart details
    total_price = sum(item.product.price * item.quantity for item in cart.items.all())
    shipping = Decimal("0.002") * total_price
    shipping = shipping.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = total_price + shipping
    cart_item_count = sum(
        item.quantity for item in cart.items.all()
    )  # Updated to reflect total quantity

    # Return updated response
    return JsonResponse(
        {
            "updated_quantity": updated_quantity,
            "total_price": total_price,
            "cart_item_count": cart_item_count,
            "shipping": shipping,
            "total": total,
        }
    )


state_shipping_fees = {
    "Maharashtra": {
        "main_cities": ["Mumbai", "Pune", "Navi Mumbai", "Thane", "Nagpur"],
        "base_fee": Decimal("75.00"),
        "remote_fee": Decimal("100.00"),
    },
    "Gujarat": {
        "main_cities": ["Ahmedabad", "Surat", "Vadodara", "Rajkot"],
        "base_fee": Decimal("60.00"),
        "remote_fee": Decimal("85.00"),
    },
}


# View to display the cart
@login_required
def cart_view(request):
    # Get the user's cart
    cart, created = Cart.objects.get_or_create(user=request.user)

    # Get updated cart items
    cart_items = cart.items.all()

    # Calculate total quantity and subtotal price
    cart_item_count = sum(item.quantity for item in cart_items)
    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    shipping = subtotal * Decimal(0.002)

    # Retrieve all addresses for the user
    addresses = Address.objects.filter(user=request.user)

    # If an AJAX request is received with the selected address
    if (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        and request.method == "POST"
    ):

        # Get the selected address ID from the AJAX request
        selected_address_id = request.POST.get("address_id")

        # Fetch the selected address based on the provided ID
        selected_address = addresses.filter(id=selected_address_id).first()

        # Calculate shipping fee based on state and city of the selected address
        shipping = subtotal * Decimal(0.002)  # Default to 0 if no address is selected

        if selected_address:
            # zip_code = selected_address.zip_code  # Assume postal_code is the PIN code
            state = (
                selected_address.state
            )  # Assume state is available in the Address model
            city = (
                selected_address.city
            )  # Assume city is available in the Address model

            # Check the state first
            if state in state_shipping_fees:
                state_info = state_shipping_fees[state]
                # Check if the city is a major city in the state
                if city in state_info["main_cities"]:
                    shipping = shipping + state_info["base_fee"]
                else:
                    shipping = shipping + state_info["remote_fee"]
            else:
                shipping = shipping + Decimal(
                    "150.00"
                )  # Default fee for states not in the predefined list

        # Round the shipping fee to 2 decimal places
        shipping = shipping.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Calculate the final total (subtotal + shipping fee)
        total = subtotal + shipping

        # Return the updated shipping and total as a JSON response
        return JsonResponse(
            {
                "shipping": shipping,
                "total": total,
                "message": "Shipping fee updated successfully",
            }
        )

    # Round the shipping fee to 2 decimal places
    shipping = shipping.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Calculate the final total (subtotal + shipping fee)
    total = subtotal + shipping

    # If it's not an AJAX request, render the standard page with the initial data
    return render(
        request,
        "store/cart_view.html",
        {
            "cart": cart,
            "cart_items": cart_items,
            "cart_item_count": cart_item_count,
            "total_price": subtotal,
            "shipping": shipping,  # Default to 0 for non-AJAX requests
            "total": total,
            "addresses": addresses,
        },
    )


@login_required
def address(request):
    user = request.user

    # If the request method is POST (address is selected or new address is submitted)
    if request.method == "POST":
        selected_address_id = request.POST.get("selected_address")

        # If a new address is being added
        if "new_address" in request.POST:
            form = AddressForm(request.POST)
            if form.is_valid():
                cleaned_data = form.cleaned_data
                # Check for existing address
                existing_address = Address.objects.filter(
                    user=user,
                    address=cleaned_data["address"],
                    city=cleaned_data["city"],
                    state=cleaned_data["state"],
                    zip_code=cleaned_data["zip_code"],
                ).first()

                if existing_address:
                    Address.objects.filter(user=user, is_shipping=True).update(
                        is_shipping=False
                    )
                    existing_address.is_shipping = True
                    existing_address.save()
                    messages.info(
                        request,
                        "This address already exists and has been selected for shipping.",
                    )
                else:
                    new_address = form.save(commit=False)
                    new_address.user = user
                    new_address.is_shipping = True
                    Address.objects.filter(user=user, is_shipping=True).update(
                        is_shipping=False
                    )
                    new_address.save()
                    messages.success(
                        request, "New shipping address saved successfully!"
                    )

        # If an existing address is selected
        elif selected_address_id:
            existing_address = Address.objects.filter(
                id=selected_address_id, user=user
            ).first()
            if existing_address:
                Address.objects.filter(user=user, is_shipping=True).update(
                    is_shipping=False
                )
                existing_address.is_shipping = True
                existing_address.save()
                messages.success(
                    request, "Selected address has been set as shipping address."
                )

        # Optionally: Save this address to the current order (if applicable)
        order = Order.objects.filter(user=user).first()  # Removed status filter
        if order:
            order.shipping_address = (
                existing_address  # Update the order with the selected shipping address
            )
            order.save()

        # After saving, stay on the cart page (no redirection to payments yet)
        return redirect(
            "cart_view"
        )  # Keep user on the cart page to review the cart and address

    else:
        return redirect("cart_view")  # If not POST, just redirect back to the cart page


@login_required
def place_order(request):
    if request.method == "POST":
        shipping_address_id = request.POST.get("shipping_address")

        # Ensure shipping_address_id is valid
        if not shipping_address_id:
            return JsonResponse(
                {"success": False, "message": "Shipping address is required."}
            )

        shipping_address = get_object_or_404(Address, id=shipping_address_id)

        # Capture the subtotal and shipping fee from the POST data
        try:
            subtotal = Decimal(request.POST.get("subtotal"))
            shipping = Decimal(request.POST.get("shipping"))
            total = subtotal + shipping
        except ValueError:
            return JsonResponse({"success": False, "message": "Invalid order total."})

        # Check if the user has an existing unpaid order
        existing_order = Order.objects.filter(user=request.user, status="pending").first()

        if existing_order:
            # Modify the existing order (cart items, shipping address, etc.)
            existing_order.shipping_address = shipping_address
            existing_order.subtotal = subtotal
            existing_order.shipping = shipping
            existing_order.total = total
            existing_order.save()

            return JsonResponse(
                {
                    "success": True,
                    "message": "Order updated successfully.",
                    "order_id": existing_order.id,
                }
            )
        else:
            # Generate the order number only when creating a new order
            order_number = f"ORD-{timezone.now().strftime('%Y%m%d%H%M%S')}"

            # Create a new order if no existing unpaid order
            order = Order.objects.create(
                user=request.user,
                shipping_address=shipping_address,
                subtotal=subtotal,
                shipping=shipping,
                total=total,
                order_number=order_number,
                status="pending",
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": "Order placed successfully.",
                    "order_id": order.id,
                }
            )

    return JsonResponse({"success": False, "message": "Invalid request."})


@login_required
def payments(request, order_id):
    # Fetch the order using the order_id
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Simulating payment success (this should be replaced with actual payment provider integration)
    payment_success = True  # This should be set based on actual payment processing

    if payment_success:
        # Update order status to 'completed' when payment is successful
        order.status = "completed"
        order.save()

        # Redirect to order confirmation page
        print(order_id)
        return redirect("order_confirmation", order_id=order.id)
    else:
        # In case payment fails, you can handle the error here (e.g., show a failure message)
        return render(request, "Store/cart_view.html", {"order": order})


# stripe.api_key = settings.STRIPE_SECRET_KEY

# def stripe_webhook(request):
#     payload = request.body
#     sig_header = request.META['HTTP_STRIPE_SIGNATURE']
#     endpoint_secret = settings.STRIPE_ENDPOINT_SECRET

#     try:
#         event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)

#         if event['type'] == 'payment_intent.succeeded':
#             payment_intent = event['data']['object']
#             order_id = payment_intent['metadata']['order_id']  # Assuming the order ID is stored in metadata
#             order = get_object_or_404(Order, id=order_id)

#             # Update order status to 'completed'
#             order.status = 'completed'
#             order.save()

#             # Send email confirmation
#             send_confirmation_email(order)

#         return JsonResponse({'status': 'success'})
#     except Exception as e:
#         return JsonResponse({'status': 'failed', 'error': str(e)})


# View to confirm the order
@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    cart = Cart.objects.filter(user=request.user, is_ordered=False).first()  # Get the user's active cart

    send_confirmation_email(order)  # Pass only the order object to the email function

    return render(
        request, "Store/order_confirmation.html", {
            "order": order,
            "cart": cart
        }
    )


def send_confirmation_email(order):
    # Set the email subject
    subject = f"Order Confirmation - {order.order_number}"
    
    cart = Cart.objects.filter(
        user=order.user, is_ordered=False
    ).first()  # Get the user's active car
   
    # Create the email message
    message = f"""
    Dear {order.user},

    Thank you for your order! Your order number is {order.order_number}.
    
    Order Details:
   
    """

    # Loop through the items in the cart and append them to the message
    for item in cart.items.all():  # Assuming `order.cart.items.all()` gives you the items in the cart
        message += f"{item.product.name}: Qt.{item.quantity}\n"
    
    message += f"""
    Subtotal: ₹{order.subtotal}

    Shipping: ₹{order.shipping}
    
    Total: ₹{order.total}
    
    The Products will be shipped to {order.shipping_address}

    You will receive further updates on your order soon.

    Thank you for shopping with us!

    Best Regards,
    UrbanCart 
    """

    # Set the from email address (configured in settings.py)
    from_email = settings.EMAIL_HOST_USER

    # Set the recipient email address (user's email address)
    recipient_list = [order.user.email]

    # Send the email
    send_mail(subject, message, from_email, recipient_list, fail_silently=False)


def contact_view(request):
    return render(request, "Store/contact.html")
