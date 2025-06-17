from django.contrib import admin

# Register your models here.
from .models import Order, OrderItem, Payment

admin.site.register([Order, OrderItem, Payment])