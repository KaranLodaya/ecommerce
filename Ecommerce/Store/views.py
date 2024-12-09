from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
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

    # Get or create the user's cart
    cart, created = Cart.objects.get_or_create(user=request.user)

    # Add the item to the cart
    cart.add_item(product)

    # Get updated cart items
    cart_items = cart.items.all()

    # Calculate the total quantity of items in the cart
    total_item_count = sum(item.quantity for item in cart_items)

    # Return the updated cart as JSON for frontend update
    return JsonResponse({
        'cart_item_count': total_item_count,
        'total_price': cart.total_price,
    })


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

    # Calculate updated cart details
    total_price = sum(item.product.price * item.quantity for item in cart.items.all())
    cart_item_count = cart.items.count()

    # Return updated response
    return JsonResponse({
        "updated_quantity": updated_quantity,
        "total_price": total_price,
        "cart_item_count": cart_item_count,
    })
   

# View to display the cart
@login_required
def cart_view(request):
    # Get the user's cart
    cart, created = Cart.objects.get_or_create(user=request.user)

     # Get updated cart items
    cart_items = cart.items.all()

    # Calculate the total quantity of items in the cart
    total_item_count = sum(item.quantity for item in cart_items)
    
    # Pass the cart items and total price to the template
    return render(request, 'store/cart_view.html', {
        'cart': cart,
        'cart_items': cart.items.all(),
        'cart_item_count': total_item_count,
    })




# View to place an order
@login_required
def place_order(request):
    cart = get_object_or_404(Cart, user=request.user)

    if request.method == 'POST':
        shipping_address = request.POST.get('shipping_address', '')

        if not shipping_address:
            return JsonResponse({'success': False, 'message': 'Shipping address is required.'})

        order = Order.objects.create(user=request.user, cart=cart, shipping_address=shipping_address)

        # Empty the cart and recalculate total
        cart.items.all().delete()
        cart.calculate_total()

        return redirect('order_confirmation', order_id=order.id)

    return render(request, 'store/checkout.html', {'cart': cart})

# View to confirm the order
@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'Store/order_confirmation.html', {'order': order})

def contact_view(request):
    return render(request, 'Store/contact.html')
