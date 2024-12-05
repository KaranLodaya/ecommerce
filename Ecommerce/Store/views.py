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

# View to add an item to the cart
@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)

    if not item_created:
        cart_item.quantity += 1
        cart_item.save()

    cart.calculate_total()
    return redirect('cart_view')

# View to remove an item from the cart
@login_required
def remove_from_cart(request, cart_item_id):
    cart_item = get_object_or_404(CartItem, id=cart_item_id)
    cart_item.delete()
    cart_item.cart.calculate_total()
    return redirect('cart_view')

# View to display the cart
@login_required
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    return render(request, 'cart.html', {'cart': cart})

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

    return render(request, 'checkout.html', {'cart': cart})

# View to confirm the order
@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_confirmation.html', {'order': order})
