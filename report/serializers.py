from rest_framework import serializers
from .models import Report, SalesReport
from store.models import Store

class ReportSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    reporter_name = serializers.CharField(source='reporter.username', read_only=True)

    class Meta:
        model = Report
        fields = ['id', 'reporter', 'reporter_name', 'store', 'store_name',
                 'reason', 'status', 'created_at', 'updated_at']
        read_only_fields = ['reporter', 'created_at', 'updated_at']

class SalesReportSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)

    class Meta:
        model = SalesReport
        fields = ['id', 'store', 'store_name', 'date', 'total_sales',
                 'total_orders', 'average_order_value']
        read_only_fields = ['average_order_value']
