from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from .models import Category,Product, Cart, CartItem, Address, payment, Order
from django.contrib.auth.decorators import login_required
from decimal import Decimal, ROUND_HALF_UP
from .forms import AddressForm
from django.contrib import messages  
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _  


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
        product.quantity_in_cart = cart.get(product.id, 0)  # Default to 0 if not in cart

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






# View to display the cart
@login_required
def cart_view(request):
    # Get the user's cart
    cart, created = Cart.objects.get_or_create(user=request.user)

    # Get updated cart items
    cart_items = cart.items.all()

    # Calculate total quantity and total price
    cart_item_count = sum(item.quantity for item in cart_items)  # Updated to reflect total quantity
    total_price = sum(item.product.price * item.quantity for item in cart_items)
    shipping = Decimal("0.002") * total_price
    shipping = shipping.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = total_price + shipping

    addresses = Address.objects.filter(user=request.user)

    # Retrieve the most recent order or create one if it doesn't exist
    order = Order.objects.filter(user=request.user).last()  # Removed status filter

    # Get the user's selected or saved address
    selected_address = None
    if order:
        selected_address = order.shipping_address  # Display the selected shipping address

    # Pass the cart items, total price, addresses, and the selected address to the template
    return render(
        request,
        "store/cart_view.html",
        {
            "cart": cart,
            "cart_items": cart_items,
            "cart_item_count": cart_item_count,
            "total_price": total_price,
            "shipping": shipping,
            "total": total,
            "addresses": addresses,  # Pass the addresses to the template
            "selected_address": selected_address,  # Pass the selected address to the template
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
                    address=cleaned_data['address'],
                    city=cleaned_data['city'],
                    state=cleaned_data['state'],
                    zip_code=cleaned_data['zip_code']
                ).first()

                if existing_address:
                    Address.objects.filter(user=user, is_shipping=True).update(is_shipping=False)
                    existing_address.is_shipping = True
                    existing_address.save()
                    messages.info(request, "This address already exists and has been selected for shipping.")
                else:
                    new_address = form.save(commit=False)
                    new_address.user = user
                    new_address.is_shipping = True
                    Address.objects.filter(user=user, is_shipping=True).update(is_shipping=False)
                    new_address.save()
                    messages.success(request, "New shipping address saved successfully!")

        # If an existing address is selected
        elif selected_address_id:
            existing_address = Address.objects.filter(id=selected_address_id, user=user).first()
            if existing_address:
                Address.objects.filter(user=user, is_shipping=True).update(is_shipping=False)
                existing_address.is_shipping = True
                existing_address.save()
                messages.success(request, "Selected address has been set as shipping address.")

        # Optionally: Save this address to the current order (if applicable)
        order = Order.objects.filter(user=user).first()  # Removed status filter
        if order:
            order.shipping_address = existing_address  # Update the order with the selected shipping address
            order.save()

        # After saving, stay on the cart page (no redirection to payments yet)
        return redirect('cart_view')  # Keep user on the cart page to review the cart and address

    else:
        return redirect('cart_view')  # If not POST, just redirect back to the cart page



    







def payments(request):
    products = Product.objects.all()
    return render(request, "Store/payments.html", {"products": products})





# View to place an order
@login_required
def place_order(request):
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.items.all()

    # Calculate total quantity and total price
    cart_item_count = sum(item.quantity for item in cart_items)
    total_price = sum(item.product.price * item.quantity for item in cart_items)
    shipping = Decimal("0.002") * total_price
    shipping = shipping.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = total_price + shipping

    # Handle normal POST request for placing the order
    if request.method == "POST":
        shipping_address_id = request.POST.get("shipping_address", "")

        # Check if the user provided a valid shipping address
        if not shipping_address_id:
            return JsonResponse(
                {"success": False, "message": "Shipping address is required."}
            )

        # Ensure the address is valid and belongs to the logged-in user
        shipping_address = get_object_or_404(Address, id=shipping_address_id, user=request.user)

        # Create the order and associate it with the selected shipping address
        order = Order.objects.create(
            user=request.user, cart=cart, shipping_address=shipping_address
        )

        # Empty the cart and recalculate the total
        cart.items.all().delete()
        cart.calculate_total()

        return redirect("order_confirmation", order_id=order.id)

    # Render the checkout page for initial load
    return render(
        request,
        "store/checkout.html",
        {
            "cart": cart,
            "cart_items": cart_items,
            "cart_item_count": cart_item_count,
            "total_price": total_price,
            "shipping": shipping,
            "total": total,
        },
    )





# View to confirm the order
@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "Store/order_confirmation.html", {"order": order})


def contact_view(request):
    return render(request, "Store/contact.html")
