from django.contrib import admin

# Register your models here.
from .models import Store, StoreAnalytics, StoreStaff

admin.site.register(Store)
admin.site.register(StoreAnalytics)
admin.site.register(StoreStaff)
