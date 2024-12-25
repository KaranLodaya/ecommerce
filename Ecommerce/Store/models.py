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
    
class Review(models.Model):
    product = models.ForeignKey(Product, related_name="reviews", on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 6)])  # 1 to 5 star ratings
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Review by {self.user.username} for {self.product.name}'


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    is_ordered = models.BooleanField(default=False)
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
        return f" {self.address}, {self.city}, {self.state}, {self.zip_code}, {self.country}"




class payment(models.Model):
    pass
    

    

class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Placed', 'Placed'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    shipping_address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    order_number = models.CharField(max_length=255, unique=True)
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Order {self.order_number} for {self.user.username}"
    


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)  # Assuming you have a Product model
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Order {self.order.order_number}"
