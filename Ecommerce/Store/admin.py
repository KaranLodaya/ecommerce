from django.contrib import admin
from .models import Product, Category, Cart, CartItem, Order,Address, Payment,OrderItem

admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Cart)
admin.site.register(CartItem)

admin.site.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user','address', 'city', 'state', 'zip_code','country',)
    exclude=('is_billing', 'is_shipping')
    list_filter = ( 'city', 'state', 'country')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'user', 'payment_method', 'status', 'transaction_id', 'amount', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('transaction_id', 'order__order_number', 'user__username')
    readonly_fields = ('order', 'user', 'payment_method', 'transaction_id', 'amount', 'created_at', 'updated_at')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0  # Do not show extra empty rows
    readonly_fields = ('product', 'quantity', 'price')
    can_delete = False  # Prevent deletion of items directly in admin

class OrderAdmin(admin.ModelAdmin):
    # List display and configuration
    list_display = ('order_number', 'user', 'status', 'order_date', 'total', 'payment_status')
    list_filter = ('status', 'order_date')
    search_fields = ('order_number', 'user__username', 'user__email')
    inlines = [OrderItemInline]

    # Read-only fields
    readonly_fields = (
        'order_number', 'user', 'status','shipping_address', 'order_date', 'total', 'shipping', 'subtotal', 'tax',
        'payment_method', 'transaction_id', 'payment_amount', 'payment_status', 'payment_created_at'
    )

    # Fieldsets for organizing sections
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'status', 'order_date'),
        }),
        # ('Order Items', {
        #     'fields': (),  # Inline is used here, so this remains empty
        # }),
        ('Address', {
            'fields': ('shipping_address',),
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'shipping', 'tax', 'total'),
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'transaction_id', 'payment_amount', 'payment_status', 'payment_created_at'),
        }),
        ('Tracking', {
            'fields': ('tracking_number', 'notes'),
        }),
    )

    # Payment details as separate readonly fields
    def payment_method(self, obj):
        """Retrieve the payment method from the related Payment model."""
        return obj.payment.payment_method if hasattr(obj, 'payment') else 'No Payment Method'
    payment_method.short_description = 'Payment Method'

    def transaction_id(self, obj):
        """Retrieve the transaction ID from the related Payment model."""
        return obj.payment.transaction_id if hasattr(obj, 'payment') else 'No Transaction ID'
    transaction_id.short_description = 'Transaction ID'

    def payment_amount(self, obj):
        """Retrieve the payment amount from the related Payment model."""
        return obj.payment.amount if hasattr(obj, 'payment') else 'No Amount'
    payment_amount.short_description = 'Amount Paid/Payable'

    def payment_status(self, obj):
        """Retrieve the payment status from the related Payment model."""
        return obj.payment.status if hasattr(obj, 'payment') else 'No Payment'
    payment_status.short_description = 'Payment Status'
    payment_status.admin_order_field = 'payment__status'

    def payment_created_at(self, obj):
        """Retrieve the payment creation timestamp from the related Payment model."""
        return obj.payment.created_at if hasattr(obj, 'payment') else 'N/A'
    payment_created_at.short_description = 'Payment Created At'

# Register the admin model
admin.site.register(Order, OrderAdmin)
