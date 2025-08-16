# Store API Documentation

This documentation provides details about all the endpoints available in the Store API.

## Base URL
```
/api/v1/store/
```

## Authentication
All endpoints require authentication using JWT (JSON Web Token). Include the token in the Authorization header:
```
Authorization: Bearer <your_token>
```

## Endpoints

### Store Management

#### 1. Create Store
- **Endpoint**: `POST /stores/`
- **Description**: Create a new store/business
- **Auth**: Required
- **Request Body**:
```json
{
    "name": "My Store",
    "description": "Store description",
    "store_type": "retail",
    "email": "store@example.com",
    "phone": "1234567890",
    "address": "Store address"
}
```
- **Success Response**: `201 Created`
- **Note**: Automatically links with user's wallet and XySave account if available

#### 2. List Stores
- **Endpoint**: `GET /stores/`
- **Description**: Get list of all stores owned by the authenticated user
- **Auth**: Required
- **Query Parameters**:
  - `page`: Page number for pagination
  - `store_type`: Filter by store type
  - `is_active`: Filter by active status
- **Success Response**: `200 OK`

#### 3. Get Store Details
- **Endpoint**: `GET /stores/{store_id}/`
- **Description**: Get detailed information about a specific store
- **Auth**: Required
- **Success Response**: `200 OK`

#### 4. Update Store
- **Endpoint**: `PUT/PATCH /stores/{store_id}/`
- **Description**: Update store information
- **Auth**: Required
- **Request Body**: Same as create store
- **Success Response**: `200 OK`

#### 5. Delete Store
- **Endpoint**: `DELETE /stores/{store_id}/`
- **Description**: Delete/deactivate a store
- **Auth**: Required
- **Success Response**: `204 No Content`

### Store Financial Management

#### 1. Get Store Balance
- **Endpoint**: `GET /stores/{store_id}/balance/`
- **Description**: Get combined balance from linked wallet and XySave account
- **Auth**: Required
- **Success Response**: `200 OK`
```json
{
    "total_balance": "100000.00",
    "wallet_balance": "75000.00",
    "xysave_balance": "25000.00",
    "currency": "NGN"
}
```

#### 2. Store Transactions
- **Endpoint**: `GET /stores/{store_id}/transactions/`
- **Description**: Get store transaction history
- **Auth**: Required
- **Query Parameters**:
  - `page`: Page number
  - `from_date`: Filter from date
  - `to_date`: Filter to date
  - `transaction_type`: Filter by type
- **Success Response**: `200 OK`

#### 3. Settlement Settings
- **Endpoint**: `PUT /stores/{store_id}/settlement-settings/`
- **Description**: Update store settlement settings
- **Auth**: Required
- **Request Body**:
```json
{
    "settlement_frequency": "weekly",
    "settlement_day": "monday",
    "minimum_settlement_amount": "10000.00"
}
```
- **Success Response**: `200 OK`

### Store Verification

#### 1. Submit Verification
- **Endpoint**: `POST /stores/{store_id}/verify/`
- **Description**: Submit store for verification
- **Auth**: Required
- **Request Body**:
```json
{
    "registration_number": "REG123456",
    "tax_id": "TAX123456",
    "verification_documents": ["doc1", "doc2"]
}
```
- **Success Response**: `202 Accepted`

#### 2. Verification Status
- **Endpoint**: `GET /stores/{store_id}/verification-status/`
- **Description**: Check store verification status
- **Auth**: Required
- **Success Response**: `200 OK`

### Store Analytics

#### 1. Sales Analytics
- **Endpoint**: `GET /stores/{store_id}/analytics/sales/`
- **Description**: Get store sales analytics
- **Auth**: Required
- **Query Parameters**:
  - `period`: daily/weekly/monthly/yearly
  - `from_date`: Start date
  - `to_date`: End date
- **Success Response**: `200 OK`

#### 2. Customer Analytics
- **Endpoint**: `GET /stores/{store_id}/analytics/customers/`
- **Description**: Get store customer analytics
- **Auth**: Required
- **Success Response**: `200 OK`

### Store Settings

#### 1. Update Settings
- **Endpoint**: `PUT /stores/{store_id}/settings/`
- **Description**: Update store settings
- **Auth**: Required
- **Request Body**:
```json
{
    "notification_preferences": {
        "email": true,
        "sms": false,
        "push": true
    },
    "business_hours": {
        "monday": ["9:00", "17:00"],
        "tuesday": ["9:00", "17:00"]
        // ... other days
    }
}
```
- **Success Response**: `200 OK`

## Error Responses

All endpoints may return the following errors:

- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

## Rate Limiting

API requests are limited to:
- 100 requests per minute for regular users
- 1000 requests per minute for verified businesses

## Webhook Notifications

Stores can receive webhook notifications for various events:
- New transactions
- Settlement completions
- Verification status changes
- Balance updates

To configure webhooks, use the store settings endpoint.
