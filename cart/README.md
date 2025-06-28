# Cart System - Production Ready

A comprehensive, production-ready shopping cart system built with Django REST Framework.

## Features

### 🛒 Core Functionality
- **User Cart Management**: Add, update, remove cart items
- **Product Variants Support**: Handle products with different variants (size, color, etc.)
- **Stock Validation**: Real-time stock availability checking
- **Soft Delete**: Preserve cart history with soft delete functionality
- **Audit Trail**: Track who created/updated cart items

### 🔧 Advanced Features
- **Bulk Operations**: Update multiple cart items at once
- **Cart Summary**: Get detailed cart totals and item counts
- **Search & Filter**: Search cart items by product name, description, store
- **Stock Validation**: Check stock availability for all cart items
- **Wishlist Integration**: Move cart items to wishlist
- **Caching**: Optimized with Redis caching for better performance

### 🛡️ Security & Validation
- **Authentication Required**: All endpoints require user authentication
- **Data Validation**: Comprehensive validation for all inputs
- **Stock Checks**: Prevent adding items beyond available stock
- **Store Consistency**: Ensure products belong to correct stores

## API Endpoints

### Base URL: `/api/cart/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List user's cart items |
| `POST` | `/` | Add item to cart |
| `GET` | `/{id}/` | Get specific cart item |
| `PUT/PATCH` | `/{id}/` | Update cart item |
| `DELETE` | `/{id}/` | Remove cart item (soft delete) |

### Custom Actions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/summary/` | Get cart summary with totals |
| `POST` | `/add_item/` | Add item with duplicate handling |
| `POST` | `/bulk_update/` | Update multiple items |
| `POST` | `/clear/` | Clear all cart items |
| `GET` | `/count/` | Get cart item count |
| `GET` | `/search/` | Search cart items |
| `POST` | `/move_to_wishlist/` | Move items to wishlist |
| `GET` | `/validate_stock/` | Check stock availability |
| `GET` | `/low_stock_items/` | Get items with low stock |

## Usage Examples

### Add Item to Cart
```bash
POST /api/cart/
{
    "product_id": "uuid",
    "store_id": "uuid",
    "variant_id": "uuid",  # optional
    "quantity": 2,
    "selected_size": "M",  # optional
    "selected_color": "Blue"  # optional
}
```

### Get Cart Summary
```bash
GET /api/cart/summary/
```

Response:
```json
{
    "total_items": 5,
    "total_price": "149.95",
    "item_count": 3,
    "store": {
        "id": "uuid",
        "name": "Store Name"
    },
    "items": [...]
}
```

### Bulk Update
```bash
POST /api/cart/bulk_update/
{
    "updates": [
        {"cart_id": "uuid", "quantity": 3},
        {"cart_id": "uuid", "quantity": 1}
    ]
}
```

## Model Structure

### Cart Model
```python
class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    selected_size = models.CharField(max_length=10, null=True, blank=True)
    selected_color = models.CharField(max_length=50, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Audit fields
    created_by = models.ForeignKey(User, related_name='created_cart_items')
    updated_by = models.ForeignKey(User, related_name='updated_cart_items')
```

## Serializers

### CartSerializer
- Full cart item details with nested product, store, and variant information
- Computed fields for unit_price and total_price
- Comprehensive validation

### CartCreateSerializer
- Specialized for creating new cart items
- Handles product_id, store_id, variant_id mapping
- Stock validation during creation

### CartUpdateSerializer
- For updating existing cart items
- Quantity and attribute updates
- Stock availability checking

## Admin Interface

The Django admin interface includes:

- **Professional Display**: Clean, organized layout with status badges
- **Advanced Filtering**: Filter by status, store, date ranges, stock levels
- **Bulk Actions**: Soft delete, restore, export to CSV, bulk quantity updates
- **Search Functionality**: Search by user, product, store names
- **Audit Information**: Track who created/updated items
- **Export Features**: Export cart data to CSV format

## Performance Optimizations

### Database Optimizations
- **Select Related**: Optimized queries with `select_related` and `prefetch_related`
- **Indexes**: Database indexes on frequently queried fields
- **Soft Delete**: Efficient filtering with `is_deleted` index

### Caching
- **Redis Caching**: Cart summary cached for 5 minutes
- **Query Optimization**: Minimized database hits

### API Optimizations
- **Pagination**: Efficient handling of large cart datasets
- **Filtering**: Server-side filtering and search
- **Bulk Operations**: Reduce API calls with bulk endpoints

## Testing

Comprehensive test coverage including:

- **Model Tests**: Cart creation, validation, soft delete, calculations
- **API Tests**: All endpoints, authentication, error handling
- **Integration Tests**: End-to-end cart operations
- **Edge Cases**: Stock validation, invalid data handling

Run tests:
```bash
python manage.py test cart.tests
```

## Security Considerations

### Authentication
- All endpoints require user authentication
- User can only access their own cart items
- Proper permission checks throughout

### Data Validation
- Input sanitization and validation
- Stock availability checking
- Store-product relationship validation
- Quantity validation (positive integers)

### Audit Trail
- Track who created/updated cart items
- Soft delete preserves data integrity
- Timestamp tracking for all operations

## Deployment Considerations

### Environment Variables
```bash
# Required for production
DEBUG=False
SECRET_KEY=your-secret-key
DATABASE_URL=your-database-url
REDIS_URL=your-redis-url  # For caching
```

### Database Migrations
```bash
python manage.py makemigrations cart
python manage.py migrate
```

### Performance Monitoring
- Monitor cart API response times
- Track database query performance
- Monitor cache hit rates
- Set up error logging and alerting

## Error Handling

The system includes comprehensive error handling:

- **Validation Errors**: Clear error messages for invalid data
- **Stock Errors**: Informative messages about stock availability
- **Authentication Errors**: Proper 401 responses for unauthenticated requests
- **Not Found Errors**: 404 responses for missing resources
- **Server Errors**: 500 responses with logging for unexpected errors

## Contributing

1. Follow Django coding standards
2. Add tests for new features
3. Update documentation
4. Ensure all tests pass
5. Follow the existing code structure

## License

This cart system is part of the larger e-commerce platform and follows the same licensing terms. 