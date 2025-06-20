from django.contrib import admin

# Register your models here.
from .models import Product, ProductVariant, Category, SubCategory
admin.site.register(Product)
admin.site.register(ProductVariant)
admin.site.register(Category)
admin.site.register(SubCategory)
