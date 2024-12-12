from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from . import views
from django.contrib.auth.views import LoginView
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('products/', views.product_list, name='product_list'),  # List all products
    path('category/<int:category_id>/', views.product_list_by_category, name='product_list_by_category'),  # List products by category
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),  # Product details page
    path('add_to_cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),  # Add product to cart
    path('remove_from_cart/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),      # Remove product from cart
    path('cart/', views.cart_view, name='cart_view'),  # View cart
    path('checkout/', views.place_order, name='place_order'),  # Place an order
    path('order-confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),  # Order confirmation page
    path('contact/', views.contact_view, name='contact'), # contact.
    # path('signup/', include('django.contrib.auth.urls')),  # URL pattern for sign-up page
    # path('signup/', views.sign_up, name='signup'),  # URL pattern for sign-up page
    # path('login/', views.login_view, name='login'),
    # path('logout/', views.logout_view, name='logout'),
]+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
