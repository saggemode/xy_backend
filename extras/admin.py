from django.contrib import admin

# Register your models here.

from .models import Address, UserVerification


admin.site.register(Address)
admin.site.register(UserVerification)   