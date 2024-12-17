from django.contrib import admin
from .models import Product, Category, Cart, CartItem, Order,Address, payment

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

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['user', 'shipping_address', 'status']