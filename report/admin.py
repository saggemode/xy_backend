from django.contrib import admin

# Register your models here.
from .models import Report, SalesReport

admin.site.register(Report)
admin.site.register(SalesReport)