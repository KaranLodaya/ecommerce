from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from .models import Category, Product,Review, Cart, CartItem, Address, Payment, Order, OrderItem
from django.contrib.auth.decorators import login_required
from decimal import Decimal, ROUND_HALF_UP
from .forms import AddressForm, ReviewForm
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.core.exceptions import ObjectDoesNotExist  # Add this import
from django.db import IntegrityError, DatabaseError  # Add this import
from django.utils import timezone
from django.utils.crypto import get_random_string  # Add this import
from django.core.mail import send_mail
from django.conf import settings
import json 
# stripe, requests
# from requests import post
from django.core.cache import cache
from django.views.decorators.cache import cache_page



# View for listing products
# @cache_page(60 * 15)  # Cache for 15 minutes
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



def search(request):
    query = request.GET.get('q', '')
    results = []

    if query:
        results = Product.objects.filter(
            name__icontains=query
        ) | Product.objects.filter(
            description__icontains=query
        )

    data = {
        'results': [
            {
                'name': product.name,
                'description': product.description,
                'price': str(product.price),
            }
            for product in results
        ]
    }
    return JsonResponse(data)



# View for product details
@cache_page(60 * 10)
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    reviews = product.reviews.all()  # Fetch all reviews related to the product

    if request.user.is_authenticated:
        # Get or create a cart for the logged-in user
        cart_obj, created = Cart.objects.get_or_create(user=request.user)
        # Build a dictionary with product IDs as keys and quantities as values
        cart = {item.product.id: item.quantity for item in cart_obj.items.all()}
        # Calculate the total quantity of items in the cart
        cart_item_count = sum(cart.values())
    else:
        cart_item_count = 0  # If user is not logged in, set cart item count to 0

    if request.method == 'POST' and request.user.is_authenticated:
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            return redirect('product_detail', product_id=product.id)
    else:
        form = ReviewForm()  # Initialize the form for GET request

    return render(
        request,
        "Store/product_detail.html",
        {
            "product": product,
            "cart_item_count": cart_item_count,
            "reviews": reviews,
            "form": form,
        }
    )



def calculate_cart_totals(cart, address=None, state_shipping_fees=None):
    """
    Helper function to calculate the total price, shipping, and item count in the cart.
    If an address is provided, it adds area-based shipping fees to the base fee.
    Returns a dictionary with updated subtotal, shipping, total, and item count.
    """

    # First, try to fetch the cart totals from the cache
    cache_key = f"cart_totals_{cart.user.id}"
    cached_totals = cache.get(cache_key)

    # Calculate subtotal and cart item count
    subtotal = sum(item.product.price * item.quantity for item in cart.items.all())
    cart_item_count = sum(item.quantity for item in cart.items.all())

    # Calculate base shipping fee as 1% of the subtotal
    shipping = Decimal("0.002") * subtotal
    shipping = shipping.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # # If an address is selected, add area-based shipping fee
    # if address and state_shipping_fees:
    #     state = address.state
    #     city = address.city

    #     if state in state_shipping_fees:
    #         state_info = state_shipping_fees[state]
    #         if city in state_info["main_cities"]:
    #             shipping += state_info["base_fee"]
    #         else:
    #             shipping += state_info["remote_fee"]
    #     else:
    #         shipping += Decimal("150.00")  # Default fee for states not in the predefined list

    # Calculate total (subtotal + shipping)
    total = subtotal + shipping

    # Prepare the totals dictionary
    totals = {
        "subtotal": subtotal,
        "shipping": shipping,
        "total": total,
        "cart_item_count": cart_item_count
    }

    # Cache the result for 15 minutes
    cache.set(cache_key, totals, timeout=60 * 15)

    return totals

    
# View to add an item to the cart
@login_required
def add_to_cart(request, product_id):
    cart = get_object_or_404(Cart, user=request.user)
    product = get_object_or_404(Product, id=product_id)

    # Find the cart item
    cart_item = cart.items.filter(product=product).first()

    if cart_item:
        cart_item.quantity += 1
        cart_item.save()
    else:
        cart_item = CartItem.objects.create(cart=cart, product=product, quantity=1)

    updated_quantity = cart_item.quantity

    # Calculate updated cart details
    cart_totals = calculate_cart_totals(cart)

    # Invalidate cache for this user's cart
    cache.delete(f"cart_{request.user.id}")  # Invalidate the cache


    # Return updated response
    return JsonResponse({
        "updated_quantity": updated_quantity,
        "cart_item_count": cart_totals["cart_item_count"],
        "subtotal": cart_totals["subtotal"],
        "shipping": cart_totals["shipping"],
        "total": cart_totals["total"]
    })


@login_required
def remove_from_cart(request, product_id):
    cart = get_object_or_404(Cart, user=request.user)
    product = get_object_or_404(Product, id=product_id)

    # Find the cart item
    cart_item = cart.items.filter(product=product).first()

    if cart_item:
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
            updated_quantity = cart_item.quantity
        else:
            cart_item.delete()
            updated_quantity = 0
    else:
        updated_quantity = 0

    # Calculate updated cart details
    cart_totals = calculate_cart_totals(cart)

    # Invalidate cache for this user's cart
    cache.delete(f"cart_{request.user.id}")  # Invalidate the cache


    # Return updated response
    return JsonResponse({
        "updated_quantity": updated_quantity,
        "cart_item_count": cart_totals["cart_item_count"],
        "subtotal": cart_totals["subtotal"],
        "shipping": cart_totals["shipping"],
        "total": cart_totals["total"]
    })


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

    # Get the user's cart from cache or database
    cart_key = f"cart_{request.user.id}" if request.user.is_authenticated else f"cart_{request.session.session_key}"
    cart = cache.get(cart_key)

    # If cart is not in the cache, fetch from the database and cache it
    if not cart:
        cart, created = Cart.objects.get_or_create(user=request.user)
        cache.set(cart_key, cart, timeout=60*30)  # Cache for 30 minutes



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
            "subtotal": subtotal,
            "shipping": shipping,  # Default to 0 for non-AJAX requests
            "total": total,
            "addresses": addresses,
        },
    )


from django.db.models import Sum
def get_cart_item_count(request):
    cart_items = CartItem.objects.filter(cart__user=request.user)  # Replace with your cart query
    cart_item_count = cart_items.aggregate(total=Sum('quantity'))['total'] or 0
    return JsonResponse({'cart_item_count': cart_item_count})



def favourites(request):
    return render(request, 'Store/favourites.html', {})



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
        return redirect("cart_view")  # Keep user on the cart page to review the cart and address

    else:
        return redirect("cart_view")  # If not POST, just redirect back to the cart page



@login_required
def place_order(request):
    if request.method == "POST":
        shipping_address_id = request.POST.get("shipping_address")
        print(shipping_address_id)
        updated_items = json.loads(request.POST.get("updated_items", "[]"))  # Parse the updated items from JSON

        # Ensure shipping_address_id is valid
        if not shipping_address_id:
            print("no shipping address id")
            return JsonResponse(
                {"success": False, "message": "Shipping address is required."}
            )

        shipping_address = get_object_or_404(Address, id=shipping_address_id)
        print(shipping_address)
       
        # Check for an active cart
        cart = Cart.objects.filter(user=request.user, is_ordered=False).first()

        if cart:
            print("Active cart found. Creating a new order.")
            # Fetch cart items and check if cart is not empty
            cart_items = CartItem.objects.filter(cart=cart)
            if not cart_items.exists():
                return JsonResponse({"success": False, "message": "No items in the cart."})

            # Calculate subtotal and total
            subtotal = sum(item.subtotal() for item in cart_items)
            shipping = Decimal(request.POST.get("shipping", 0))
            total = subtotal + shipping

            # Create a new order
            order_number = f"ORD-{timezone.now().strftime('%Y%m%d%H%M%S')}"
            order = Order.objects.create(
                user=request.user,
                shipping_address=shipping_address,
                subtotal=subtotal,
                shipping=shipping,
                total=total,
                order_number=order_number,
                status="pending",
            )

            # Create order items
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.price,
                )

            # Mark the cart as ordered
            cart.is_ordered = True
            cart.save()

             # Create a new Payment instance linked to this order
            payment = Payment.objects.create(
                user=request.user,
                order=order,
                amount=total,
                payment_method='', 
                status='pending',  # Initial payment status
            )

            print(f"New order created: {order.order_number}")
            return JsonResponse({"success": True, "message": "Order placed successfully.", "order_id": order.id})

        else: #no active, check for pending order
            pending_order = Order.objects.filter(user=request.user, status="Pending")

            print("no active cart found, checking for pending order")
            if pending_order:
                pending_order = pending_order.first()
                print("Pending order found. Updating order details.")

                # Update the existing order with the new address and totals
                subtotal = Decimal(request.POST.get("subtotal", 0))
                shipping = Decimal(request.POST.get("shipping", 0))
                total = subtotal + shipping

                pending_order.shipping_address = shipping_address
                pending_order.subtotal = subtotal
                pending_order.shipping = shipping
                pending_order.total = total
                pending_order.save()

                # Now handle updating the order items
                for item in updated_items:
                    product_id = item['product_id']
                    quantity = item['quantity']
                    
                    # Find the corresponding order item
                    order_item = OrderItem.objects.filter(order=pending_order, product_id=product_id).first()
                    if order_item:
                            # Update the order item quantity
                            order_item.quantity = quantity
                            order_item.save()
                    else:
                        # If the item is not found in the order, create a new order item
                        if quantity > 0:
                            product = Product.objects.get(id=product_id)
                            price = product.price  # Assuming `price` is a field in the Product model

                            # Create new order item and associate with the pending order
                            OrderItem.objects.create(
                                order=pending_order,
                                product_id=product_id,
                                quantity=quantity,
                                price=price  # Pass the price here
                            )
                            print(f"Added new item with product ID {product_id} to the order.")


                    # After updating the items, remove any order items that are no longer in the updated list
                    # Get a list of all product_ids from the updated items
                    updated_product_ids = [item['product_id'] for item in updated_items]

                    # Remove items from the order that are not in the updated list
                    order_items_to_remove = OrderItem.objects.filter(order=pending_order).exclude(product_id__in=updated_product_ids)
                    order_items_to_remove.delete()

                    # Create or update the payment for the pending order
                    payment = Payment.objects.filter(order=pending_order).first()
                    if payment:
                        payment.amount = total
                        payment.status = 'pending'  # Update payment status if needed
                        payment.save()
                    else:
                        payment = Payment.objects.create(
                            user=request.user,
                            order=pending_order,
                            amount=total,
                            payment_method='cash_on_delivery',  # Assuming 'cash_on_delivery'
                            status='pending',
                        )

                print(f"Updated order: {pending_order.order_number}")

                return JsonResponse(
                    {"success": True, "message": "Order updated successfully.", "order_id": pending_order.id}
                )

            # No active cart and no pending order
            print("No active cart or pending order found.")
            return JsonResponse({"success": False, "message": "Your cart is empty, and no pending order exists."})

    return JsonResponse({"success": False, "message": "Invalid request."})







@login_required
def payments(request, order_id):
    # Fetch the order using the order_id
    order = get_object_or_404(Order, id=order_id)

    # Check for the related payment object
    payment = Payment.objects.filter(order=order).first()  # Get the payment associated with the order

    # If payment exists, check the payment status
    if payment:
        if payment.status == 'completed':
            # Redirect if the payment is already completed
            return redirect('order_confirmation', order_id=order.id)

    # If the request is GET, render the payment page
    if request.method == 'GET':
        return render(request, 'Store/payments.html', {'order': order})

    # If the request is POST, process the payment action
    elif request.method == 'POST':
        # Get the payment method from the request
        payment_method = request.POST.get('payment_method')

        if payment_method == 'card':
            return handle_card_payment(request)
        elif payment_method == 'cod':
            return handle_cod_payment(request, order_id)
        elif payment_method == 'google_pay':
            return handle_google_pay(request)
        # elif payment_method == 'stripe':  # Stripe UPI payment
        #     return create_payment_intent(request, order)
        else:
            return JsonResponse({'status': 'failure', 'message': 'Invalid payment method'})

    # If the request method is neither GET nor POST
    return HttpResponseBadRequest("Invalid request method.")
    


# Handle Cash on Delivery (COD) Payment
def handle_cod_payment(request, order_id):

    order = get_object_or_404(Order, id=order_id)
    payment = Payment.objects.filter(order=order).first()

    if payment:
        payment.payment_method = 'cash_on_delivery'
        payment.status = 'pending'
        payment.save()
        order.status = 'Placed'
        order.save()
        print("order status - placed")

    
    return JsonResponse({'status': 'success', 'message': 'COD payment selected'})







# Handle Google pay Payment
def handle_google_pay(request):
    # Extract UPI payment details from the request
    payment_data = json.loads(request.body)

    # Verify UPI payment by checking the token (you can extend this for other UPI methods)
    if payment_data.get('paymentMethodData', {}).get('tokenizationData', {}).get('token') == 'expected_token':
        return JsonResponse({'status': 'success', 'message': 'UPI payment successful'})
    else:
        return JsonResponse({'status': 'failure', 'message': 'UPI payment failed'})


# Handle Card Payment
def handle_card_payment(request):
    # Extract payment details from the request
    payment_data = json.loads(request.body)

    # Extract card details (e.g., card number, expiry date, CVV)
    card_number = payment_data.get('card_number', '')
    card_expiry = payment_data.get('expiry_date', '')
    card_cvv = payment_data.get('cvv', '')

    # Simulate card verification (replace this with actual gateway integration)
    if card_number == 'expected_card_number' and card_expiry == '12/25' and card_cvv == '123':
        # If the payment is successful, return a success response
        return JsonResponse({'status': 'success', 'message': 'Card payment successful'})
    else:
        # If payment verification fails, return a failure response
        return JsonResponse({'status': 'failure', 'message': 'Card payment failed'})




def payment_response(request):
    if request.method == "GET":
        payment_status = request.GET.get("paymentStatus")
        order_id = request.GET.get("orderId")

        if payment_status == "SUCCESS":
            # Update order status in your database
            return HttpResponse("Payment Successful!")
        else:
            return HttpResponse("Payment Failed!")





# View to confirm the order
@login_required
def order_confirmation(request , order_id):
    # Fetch the latest completed order for the user
    order = get_object_or_404(Order, id=order_id)

    if not order:
        # If no completed order exists, return a 404 or redirect
        return render(request, "Store/no_order_found.html", status=404)

    # Send confirmation email for the latest completed order
    # send_confirmation_email(order)

    # Pass the order to the template for rendering
    return render(request, 'Store/order_confirmation.html', {'order': order})





def send_confirmation_email(order, payment_method, transaction_id=None):
    # Set the email subject
    subject = f"Order Confirmation - {order.order_number}"

    # Create the email message
    message = f"""
    Dear {order.user},

    Thank you for your order! Your order number is {order.order_number}.
    
    Order Details:
    """

    # Fetch the order items and add their details to the message
    for item in order.items.all():  # Assuming `order.items` gives the related order items
        message += f"{item.product.name}: Qty {item.quantity}, Price ₹{item.price}\n"
    
    # Add the subtotal, shipping, and total to the email message
    message += f"""
    Subtotal: ₹{order.subtotal}
    Shipping: ₹{order.shipping}
    Total: ₹{order.total}
    
    The products will be shipped to:
    {order.shipping_address}

    Payment Method: {payment_method}
    """

    # Add the transaction ID if available (not for Cash on Delivery)
    if payment_method != 'cash_on_delivery' and transaction_id:
        message += f"Transaction ID: {transaction_id}\n"
    else:
        message += "No transaction ID (Cash on Delivery)\n"

    # Add the closing message
    message += """
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




@login_required
def order_history(request):
    # Fetch only completed orders for the logged-in user
    completed_orders = Order.objects.filter(user=request.user, status='Completed').order_by('-order_date')  # Most recent first
    
    # Pass the completed orders to the template
    return render(request, 'Store/order_history.html', {'orders': completed_orders})


@login_required
def order_detail(request, order_id):
    # Fetch the order based on the order ID
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Fetch the order items associated with this order
    order_items = order.items.all()

    return render(request, 'order_detail.html', {'order': order, 'order_items': order_items})



def contact_view(request):
    return render(request, "Store/contact.html")
