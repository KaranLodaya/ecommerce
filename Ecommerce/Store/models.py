from django.db import models
from django.contrib.auth.models import User

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
    category = models.CharField(max_length=100)

    def __str__(self):
        return self.name
    


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # Associated with a user
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def calculate_total(self):
        """Recalculate the total price based on the cart items."""
        self.total_price = sum(item.subtotal() for item in self.items.all())
        self.save()

    def __str__(self):
        return f"Cart for {self.user.username}"

    def add_item(self, product, quantity=1):
        """Add an item to the cart or update the quantity if already exists."""
        # Create or get the CartItem
        cart_item, created = CartItem.objects.get_or_create(
            cart=self,
            product=product
        )
        
        # If the item already exists, just update the quantity
        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity
        
        # Save the updated CartItem and calculate total
        cart_item.save()
        self.calculate_total()

    def remove_item(self, product):
        """Remove an item from the cart."""
        try:
            cart_item = CartItem.objects.get(cart=self, product=product)
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
            else:
                cart_item.delete()
            # Recalculate the total price after removal
            self.calculate_total()
        except CartItem.DoesNotExist:
            pass


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
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


class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Associated with a user
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)  # Associated with a cart
    shipping_address = models.TextField()
    payment_status = models.CharField(max_length=50, choices=[('Pending', 'Pending'), ('Completed', 'Completed')], default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} for {self.user.username}"
