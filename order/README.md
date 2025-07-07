 # Order Management System

A comprehensive order management system for multi-vendor e-commerce platforms with full CRUD operations, status management, payment processing, and analytics.

## 📋 Table of Contents

- [Overview](#overview)
- [Models](#models)
- [API Endpoints](#api-endpoints)
- [Authentication & Permissions](#authentication--permissions)
- [Features](#features)
- [Usage Examples](#usage-examples)
- [Error Handling](#error-handling)

## 🎯 Overview

The Order Management System provides a complete solution for handling orders, order items, and payments in an e-commerce platform. It includes:

- **Order lifecycle management** (pending → confirmed → shipped → delivered)
- **Payment processing** with multiple payment methods
- **Comprehensive analytics** and reporting
- **Real-time notifications** for status changes
- **Advanced filtering and search** capabilities
- **Caching** for performance optimization

## 🗄️ Models

### Order
- **Primary order entity** with status tracking
- **Financial calculations** (subtotal, tax, shipping, discounts)
- **Shipping and billing** address management
- **Audit trail** with timestamps

### OrderItem
- **Individual products** within an order
- **Price preservation** at time of order
- **Variant support** for different product options
- **Quantity and pricing** calculations

### Payment
- **Payment transaction** tracking
- **Multiple payment methods** support
- **Status management** (pending → paid → refunded)
- **Gateway integration** support

## 🔌 API Endpoints

### OrderViewSet Endpoints

#### Standard CRUD Operations

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| `GET` | `/api/orders/` | List all orders (filtered by user) | Query params | Order list |
| `POST` | `/api/orders/` | Create new order | Order data | Created order |
| `GET` | `/api/orders/{id}/` | Get specific order | - | Order details |
| `PUT` | `/api/orders/{id}/` | Update order completely | Order data | Updated order |
| `PATCH` | `/api/orders/{id}/` | Partially update order | Partial data | Updated order |
| `DELETE` | `/api/orders/{id}/` | Delete order permanently | - | Success message |

#### Order Status Management

| Method | Endpoint | Description | Status Change |
|--------|----------|-------------|---------------|
| `PATCH` | `/api/orders/{id}/confirm_order/` | Confirm an order | PENDING → CONFIRMED |
| `PATCH` | `/api/orders/{id}/ship_order/` | Ship an order | CONFIRMED/PROCESSING → SHIPPED |
| `PATCH` | `/api/orders/{id}/deliver_order/` | Deliver an order | SHIPPED → DELIVERED |
| `PATCH` | `/api/orders/{id}/cancel_order/` | Cancel an order | Any → CANCELLED |
| `PATCH` | `/api/orders/{id}/refund_order/` | Refund an order | DELIVERED/SHIPPED → REFUNDED |

#### Order Queries & Analytics

| Method | Endpoint | Description | Caching |
|--------|----------|-------------|---------|
| `GET` | `/api/orders/my_orders/` | Current user's orders | 5 minutes |
| `GET` | `/api/orders/recent_orders/` | Orders from last 30 days | - |
| `GET` | `/api/orders/pending_orders/` | All pending orders | - |
| `GET` | `/api/orders/order_stats/` | Comprehensive statistics | 10 minutes |

#### Bulk Operations

| Method | Endpoint | Description | Request Body |
|--------|----------|-------------|--------------|
| `POST` | `/api/orders/bulk_update_status/` | Bulk update order status | `{"order_ids": [...], "status": "..."}` |

### OrderItemViewSet Endpoints

#### Standard CRUD Operations

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| `GET` | `/api/order-items/` | List all order items | Query params | OrderItem list |
| `POST` | `/api/order-items/` | Create new order item | OrderItem data | Created item |
| `GET` | `/api/order-items/{id}/` | Get specific order item | - | OrderItem details |
| `PUT` | `/api/order-items/{id}/` | Update order item completely | OrderItem data | Updated item |
| `PATCH` | `/api/order-items/{id}/` | Partially update order item | Partial data | Updated item |
| `DELETE` | `/api/order-items/{id}/` | Delete order item | - | Success message |

#### Order Item Queries

| Method | Endpoint | Description | Query Params |
|--------|----------|-------------|--------------|
| `GET` | `/api/order-items/by_order/` | Get items for specific order | `order_id={id}` |

### PaymentViewSet Endpoints

#### Standard CRUD Operations

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| `GET` | `/api/payments/` | List all payments | Query params | Payment list |
| `POST` | `/api/payments/` | Create new payment | Payment data | Created payment |
| `GET` | `/api/payments/{id}/` | Get specific payment | - | Payment details |
| `PUT` | `/api/payments/{id}/` | Update payment completely | Payment data | Updated payment |
| `PATCH` | `/api/payments/{id}/` | Partially update payment | Partial data | Updated payment |
| `DELETE` | `/api/payments/{id}/` | Delete payment | - | Success message |

#### Payment Processing

| Method | Endpoint | Description | Status Change |
|--------|----------|-------------|---------------|
| `POST` | `/api/payments/{id}/process_payment/` | Process a payment | PENDING → PAID |
| `POST` | `/api/payments/{id}/refund_payment/` | Refund a payment | PAID → REFUNDED |

#### Payment Analytics

| Method | Endpoint | Description | Caching |
|--------|----------|-------------|---------|
| `GET` | `/api/payments/payment_stats/` | Comprehensive payment statistics | 10 minutes |

## 🔐 Authentication & Permissions

### Permission Levels

- **Authenticated Users**: Can access their own orders/items/payments
- **Staff Users**: Can access all orders/items/payments
- **Admin Users**: Can delete orders and perform administrative actions

### Permission Matrix

| Action | Regular User | Staff User | Admin User |
|--------|--------------|------------|------------|
| View own orders | ✅ | ✅ | ✅ |
| View all orders | ❌ | ✅ | ✅ |
| Create orders | ✅ | ✅ | ✅ |
| Update orders | ✅ | ✅ | ✅ |
| Delete orders | ❌ | ❌ | ✅ |
| Process payments | ✅ | ✅ | ✅ |
| View analytics | ✅ | ✅ | ✅ |

## ✨ Features

### Advanced Filtering & Search

All list endpoints support:

```python
# Filtering
GET /api/orders/?status=pending&payment_status=paid&store=1

# Search
GET /api/orders/?search=ORD-20240115-1234

# Ordering
GET /api/orders/?ordering=-created_at&ordering=total_amount

# Pagination
GET /api/orders/?page=1&page_size=20
```

### Caching Strategy

- **User orders**: 5-minute cache
- **Order statistics**: 10-minute cache
- **Payment statistics**: 10-minute cache
- **Cache invalidation**: Automatic on data changes

### Real-time Notifications

Automatic notifications are created for:

- Order confirmation
- Shipping updates
- Delivery confirmations
- Order cancellations
- Refunds
- Payment processing

### Order Status Flow

```
PENDING → CONFIRMED → PROCESSING → SHIPPED → OUT_FOR_DELIVERY → DELIVERED
    ↓
CANCELLED (at any point)
    ↓
REFUNDED (if delivered/shipped)
```

## 📝 Usage Examples

### Creating an Order

```python
# POST /api/orders/
{
    "store": "store-uuid",
    "customer_id": "CUST123",
    "payment_method": "credit_card",
    "shipping_address": "address-uuid",
    "shipping_method": "standard",
    "notes": "Please deliver after 6 PM",
    "items": [
        {
            "product": "product-uuid",
            "variant": "variant-uuid",
            "quantity": 2,
            "unit_price": "29.99"
        }
    ]
}
```

### Confirming an Order

```python
# PATCH /api/orders/{order-id}/confirm_order/
# No request body needed
```

### Getting Order Statistics

```python
# GET /api/orders/order_stats/
# Response includes:
{
    "total_orders": 150,
    "pending_orders": 25,
    "processing_orders": 10,
    "shipped_orders": 45,
    "delivered_orders": 60,
    "cancelled_orders": 5,
    "refunded_orders": 5,
    "total_revenue": "15000.00",
    "average_order_value": "100.00",
    "orders_by_status": {
        "pending": 25,
        "confirmed": 10,
        "shipped": 45,
        "delivered": 60
    },
    "orders_by_month": {
        "2024-01": 50,
        "2024-02": 45,
        "2024-03": 55
    },
    "recent_orders": [...]
}
```

### Processing a Payment

```python
# POST /api/payments/{payment-id}/process_payment/
# No request body needed
```

### Bulk Status Update

```python
# POST /api/orders/bulk_update_status/
{
    "order_ids": ["order-uuid-1", "order-uuid-2"],
    "status": "confirmed"
}
```

## 🚨 Error Handling

### Standard Error Responses

```python
# 400 Bad Request
{
    "error": "Validation failed",
    "details": {
        "field_name": ["Error message"]
    }
}

# 401 Unauthorized
{
    "error": "Authentication required"
}

# 403 Forbidden
{
    "error": "Insufficient permissions"
}

# 404 Not Found
{
    "error": "Order not found"
}

# 500 Internal Server Error
{
    "error": "Failed to process request",
    "details": "Error description"
}
```

### Business Logic Errors

```python
# Order cannot be cancelled
{
    "error": "Order cannot be cancelled in its current status"
}

# Insufficient stock
{
    "error": "Insufficient stock. Available: 5"
}

# Payment cannot be processed
{
    "error": "Payment cannot be processed with current status"
}
```

## 🔧 Configuration

### Settings

```python
# Cache settings
CACHE_TIMEOUT = 300  # 5 minutes for user orders
STATS_CACHE_TIMEOUT = 600  # 10 minutes for statistics

# Pagination
PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Search
SEARCH_FIELDS = [
    'order_number', 'tracking_number', 'payment_reference'
]

# Filtering
FILTER_FIELDS = [
    'status', 'payment_status', 'payment_method', 'shipping_method'
]
```

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname

# Cache
REDIS_URL=redis://localhost:6379/0

# Logging
LOG_LEVEL=INFO
```

## 📊 Monitoring & Logging

### Log Levels

- **INFO**: Order creation, status changes, successful operations
- **WARNING**: Business rule violations, retry attempts
- **ERROR**: Failed operations, system errors
- **DEBUG**: Detailed operation tracing

### Key Metrics

- Order creation rate
- Status transition times
- Payment success rate
- Average order value
- Customer satisfaction scores

## 🚀 Performance Optimization

### Database Optimization

- **Indexes**: On frequently queried fields
- **Select Related**: For nested data fetching
- **Query Optimization**: Minimal database hits

### Caching Strategy

- **Redis**: For session and cache storage
- **Cache Keys**: User-specific and time-based
- **Cache Invalidation**: Automatic on data changes

### API Optimization

- **Pagination**: Large dataset handling
- **Filtering**: Server-side data reduction
- **Compression**: Response size optimization

## 🔄 Versioning

### API Versioning

- **URL Versioning**: `/api/v1/orders/`
- **Header Versioning**: `Accept: application/vnd.api+json;version=1`
- **Backward Compatibility**: Maintained across versions

### Migration Strategy

- **Database Migrations**: Automatic schema updates
- **Data Migrations**: Safe data transformation
- **Rollback Support**: Emergency rollback procedures

## 📚 Additional Resources

- [Django REST Framework Documentation](https://www.django-rest-framework.org/)
- [Order Management Best Practices](https://docs.example.com/order-best-practices)
- [API Testing Guide](https://docs.example.com/api-testing)
- [Performance Tuning Guide](https://docs.example.com/performance-tuning)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.