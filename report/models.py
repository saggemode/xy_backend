from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from store.models import Store

# Create your models here.
class Report(models.Model):
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    reason = models.TextField()
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Report by {self.reporter.username} on {self.store.name}"
    
    
class SalesReport(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    date = models.DateField()
    total_sales = models.DecimalField(max_digits=12, decimal_places=2)
    total_orders = models.PositiveIntegerField()
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Sales Report for {self.store.name} on {self.date}"
    