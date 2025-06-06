from django.urls import path
from .views import GetWishList, ToggleWishlist  

urlpatterns = [
    path('me/', GetWishList.as_view(), name='wishlist'),  
    path('toggle/', ToggleWishlist.as_view(), name='toggle_wishlist'),
]