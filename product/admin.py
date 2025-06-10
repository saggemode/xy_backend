from django.contrib import admin

# Register your models here.
from .models import Product, ProductVariant, Category, SubCategory, Coupon
admin.site.register(Product)
admin.site.register(ProductVariant)
admin.site.register(Category)
admin.site.register(SubCategory)
admin.site.register(Coupon)

