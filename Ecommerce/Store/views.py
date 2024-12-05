from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from .models import Product, Cart, CartItem, Order
from django.contrib.auth.decorators import login_required

# View for listing products
def product_list(request):
    products = Product.objects.all()
    return render(request, 'Store/product_list.html', {'products': products})

# View for listing products by category
def product_list_by_category(request, category_id=None):
    if category_id:
        products = Product.objects.filter(category_id=category_id)
    else:
        products = Product.objects.all()
    return render(request, 'Store/product_list.html', {'products': products})

# View for product details
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'Store/product_detail.html', {'product': product})

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)

    # Get quantity from request, default to 1 if not provided
    quantity = int(request.GET.get('quantity', 1))

    # Get or create the CartItem
    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)

    if not item_created:
        # If the item already exists, update its quantity
        cart_item.quantity += quantity
        cart_item.save()

    # Recalculate the total price of the cart
    cart.calculate_total()

    return redirect('Store/cart_view')


# View to remove an item from the cart
@login_required
def remove_from_cart(request, cart_item_id):
    cart_item = get_object_or_404(CartItem, id=cart_item_id)

    if cart_item.quantity > 1:
        # If quantity is more than 1, just decrease it
        cart_item.quantity -= 1
        cart_item.save()
    else:
        # If quantity is 1, delete the cart item
        cart_item.delete()

    # Recalculate the total price of the cart
    cart_item.cart.calculate_total()

    return redirect('Store/cart_view')


# View to display the cart
@login_required
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart.calculate_total()  # Make sure total is recalculated before passing to template
    return render(request, 'Store/cart.html', {'cart': cart})


# View to place an order
@login_required
def place_order(request):
    cart = get_object_or_404(Cart, user=request.user)
    if request.method == 'POST':
        shipping_address = request.POST['shipping_address']
        order = Order.objects.create(user=request.user, cart=cart, shipping_address=shipping_address)
        cart.items.all().delete()  # Empty the cart after the order is placed
        cart.calculate_total()
        return redirect('order_confirmation', order_id=order.id)

    return render(request, 'Store/checkout.html', {'cart': cart})

# View to confirm the order
@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'Store/qorder_confirmation.html', {'order': order})
