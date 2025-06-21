from django.contrib import admin

# Register your models here.
from .models import Product, ProductVariant, Category, SubCategory,ProductReview,Coupon,CouponUsage,FlashSale,FlashSaleItem
admin.site.register(Product)
admin.site.register(ProductVariant)
admin.site.register(Category)
admin.site.register(SubCategory)
admin.site.register(ProductReview)
admin.site.register(Coupon) 
admin.site.register(CouponUsage)
admin.site.register(FlashSale)
admin.site.register(FlashSaleItem)

