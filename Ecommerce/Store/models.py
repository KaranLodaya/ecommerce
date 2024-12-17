from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal, ROUND_HALF_UP


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/')
    # category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.CharField(max_length=100, default='Default Category')

    def __str__(self):
        return self.name
    



class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    def calculate_total(self):
        # """Recalculate the total price based on the cart items, including shipping."""
        # Start with the total price of all items in the cart
        total_price = sum(item.quantity * item.product.price for item in self.items.all())

        # Optionally, add shipping charges here
        shipping_cost = Decimal("0.002") * total_price
        shipping_cost = shipping_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        total_price += shipping_cost

        # Save the updated total price
        self.total_price = total_price
        self.save()

    def __str__(self):
        return f"Cart for {self.user.username}"

    def add_item(self, product, quantity=1):
        """Add an item to the cart or update the quantity if already exists."""
        cart_item, created = CartItem.objects.get_or_create(
            cart=self,
            product=product
        )
        
        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity
        
        cart_item.save()
        self.calculate_total()

    def remove_item(self, product, quantity=1):
        """Remove an item from the cart."""
        cart_item = CartItem.objects.filter(cart=self, product=product).first()
        
        if cart_item:
            cart_item.quantity -= quantity
            if cart_item.quantity <= 0:
                cart_item.delete()  # Remove the item if quantity reaches 0
            else:
                cart_item.save()
        self.calculate_total()




class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def subtotal(self):
        """Return the subtotal for this item (product price * quantity)."""
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    def save(self, *args, **kwargs):
        """Override save to ensure total price is updated after saving."""
        super().save(*args, **kwargs)
        self.cart.calculate_total()  # Recalculate total after CartItem save


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    is_billing = models.BooleanField(default=False)
    is_shipping = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user}, {self.address}, {self.city}, {self.state}, {self.zip_code}, {self.country}"




class payment(models.Model):
    pass
    

    

class Order(models.Model):
    # STATUS_CHOICES = [
    #     ('Pending', 'Pending'),
    #     ('Completed', 'Completed'),
    #     ('Cancelled', 'Cancelled'),
    # ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Associated with a user
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)  # Associated with a cart
    shipping_address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True)  # ForeignKey to Address
    # payment_status = models.CharField(max_length=50, choices=[('Pending', 'Pending'), ('Completed', 'Completed')], default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} for {self.user.username}"
