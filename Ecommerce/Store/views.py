from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from .models import Product, Cart, CartItem, Order
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.models import User


# View for listing products
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
    return render(request, "Store/product_list.html", {
        "products": products,
        "cart_item_count": cart_item_count,
    })


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

    return render(request, "Store/product_detail.html", {"product": product, "cart_item_count": cart_item_count,})


# View to add an item to the cart
@login_required
def add_to_cart(request, product_id):
    cart = get_object_or_404(Cart, user=request.user)
    product = get_object_or_404(Product, id=product_id)

    # Find the cart item
    cart_item = cart.items.filter(product=product).first()
    print(cart, product, cart_item)


    # import pdb;pdb.set_trace()
    if cart_item:
        cart_item.quantity += 1
        cart_item.save()
    else:
        cart_item = CartItem.objects.create(cart=cart, product=product, quantity=1) # Add new item to the cart if it's not already present
    
    updated_quantity = cart_item.quantity
    
    # Calculate updated cart details
    total_price = sum(item.product.price * item.quantity for item in cart.items.all())
    cart_item_count = sum(item.quantity for item in cart.items.all())  # Updated to reflect total quantity

    # Return updated response
    return JsonResponse(
        {
            "updated_quantity": updated_quantity,
            "total_price": total_price,
            "cart_item_count": cart_item_count,
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
    cart_item_count = sum(item.quantity for item in cart.items.all())  # Updated to reflect total quantity

    # Return updated response
    return JsonResponse(
        {
            "updated_quantity": updated_quantity,
            "total_price": total_price,
            "cart_item_count": cart_item_count,
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
    cart_item_count = sum(item.quantity for item in cart.items.all())  # Updated to reflect total quantity
    total_price = sum(item.product.price * item.quantity for item in cart_items)

    # Pass the cart items and total price to the template
    return render(
        request,
        "store/cart_view.html",
        {
            "cart": cart,
            "cart_items": cart_items,
            "cart_item_count": cart_item_count,
            "total_price": total_price,
        },
    )



# View to place an order
@login_required
def place_order(request):
    cart = get_object_or_404(Cart, user=request.user)

    if request.method == "POST":
        shipping_address = request.POST.get("shipping_address", "")

        if not shipping_address:
            return JsonResponse(
                {"success": False, "message": "Shipping address is required."}
            )

        order = Order.objects.create(
            user=request.user, cart=cart, shipping_address=shipping_address
        )

        # Empty the cart and recalculate total
        cart.items.all().delete()
        cart.calculate_total()

        return redirect("order_confirmation", order_id=order.id)

    return render(request, "store/checkout.html", {"cart": cart})


# View to confirm the order
@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "Store/order_confirmation.html", {"order": order})


def contact_view(request):
    return render(request, "Store/contact.html")


from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect
import re

def sign_up(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email').lower()  # Normalize email to lowercase
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')  # Add confirm password field

        # Check if the required fields are present
        if not email or not password or not name or not confirm_password:
            messages.error(request, "All fields are required!")
            return render(request, 'store/signup.html')

        # Check if the email is valid (basic validation)
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            messages.error(request, "Invalid email address!")
            return render(request, 'store/signup.html')

        # Check if the email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists!")
            return render(request, 'store/signup.html')

        # Password length check (optional)
        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long!")
            return render(request, 'store/signup.html')

        # Check if passwords match
        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return render(request, 'store/signup.html')

        try:
            # Create the user
            user = User.objects.create_user(username=name, email=email, password=password)
            user.first_name = name
            user.save()

            # Create a cart for the new user
            Cart.objects.create(user=user)

            messages.success(request, 'Account created successfully!')
            return redirect('product_list')  # Redirect to product list page after successful signup

        except Exception as e:
            messages.error(request, f"An error occurred: {e}")
            return render(request, 'store/signup.html')

    return render(request, 'store/signup.html')  # Render the signup form if it's a GET request


def login_view(request):
    if request.method == 'POST':
        # Get the username (name) and password from the form
        name = request.POST.get('name')
        password = request.POST.get('password')

        # Check if both the username and password are provided
        if not name or not password:
            messages.error(request, "Name and password are required!")
            return render(request, 'store/login.html')

        # Authenticate the user using the username and password
        user = authenticate(request, username=name, password=password)

        if user is not None:
            # Successful login
            login(request, user)

            # Ensure the user has a cart
            if not Cart.objects.filter(user=user).exists():
                Cart.objects.create(user=user)

            messages.success(request, "Login successful!")
            return redirect('product_list')  # Redirect to the product list or homepage
        else:
            # Failed login attempt (invalid credentials)
            messages.error(request, "Invalid name or password.")
            return render(request, 'store/login.html')

    return render(request, 'store/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')  # Redirect to login page after logout

