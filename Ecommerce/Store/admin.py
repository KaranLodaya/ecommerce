from django.contrib import admin
from .models import Product, Category, Cart, CartItem, Order,Address, payment,OrderItem

admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(payment)
admin.site.register(Address)

class AddressAdmin(admin.ModelAdmin):
    list_display = ('user','address', 'city', 'state', 'zip_code','country',)
    exclude=('is_billing', 'is_shipping')
    list_filter = ( 'city', 'state', 'country')

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0  # Do not show extra empty rows
    readonly_fields = ('product', 'quantity', 'price')
    can_delete = False  # Prevent deletion of items directly in admin

class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'payment_status', 'order_date', 'total')
    list_filter = ('status', 'payment_status', 'order_date')
    search_fields = ('order_number', 'user__username')
    inlines = [OrderItemInline]


admin.site.register(Order, OrderAdmin)
