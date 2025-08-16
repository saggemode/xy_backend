# Shipping Address API Documentation

## Overview
This API provides endpoints for managing shipping addresses in the system. Users can create, read, update, and delete their shipping addresses, with support for multiple addresses per user and designation of a default address.

## Base URL
```
/api/addresses/
```

## Authentication
All endpoints require authentication. Include the JWT token in the Authorization header:
```http
Authorization: Bearer your_jwt_token
```

## Endpoints

### List All Addresses
```http
GET /api/addresses/
```
Returns all shipping addresses for the authenticated user.

**Query Parameters:**
- `city`: Filter by city
- `state`: Filter by state
- `country`: Filter by country
- `is_default`: Filter by default status (true/false)
- `address_type`: Filter by address type (home, office, school, market, other, business, mailing)
- `search`: Search in address, city, state, country, postal_code, phone
- `ordering`: Order by created_at, updated_at, city, is_default (prefix with - for descending)

**Response:**
```json
[
    {
        "id": "uuid",
        "user": {
            "id": 1,
            "username": "username",
            "first_name": "First",
            "last_name": "Last",
            "email": "user@example.com"
        },
        "address": "123 Street Name",
        "city": "City Name",
        "state": "State Name",
        "postal_code": "12345",
        "country": "Country Name",
        "phone": "1234567890",
        "additional_phone": "0987654321",
        "is_default": true,
        "address_type": "home",
        "created_at": "2025-07-29T12:00:00Z",
        "updated_at": "2025-07-29T12:00:00Z",
        "full_address": "123 Street Name, City Name, State Name, 12345, Country Name",
        "latitude": 12.345678,
        "longitude": 98.765432
    }
]
```

### Create New Address
```http
POST /api/addresses/
```

**Request Body:**
```json
{
    "address": "123 Street Name",
    "city": "City Name",
    "state": "State Name",
    "postal_code": "12345",
    "country": "Country Name",
    "phone": "1234567890",
    "additional_phone": "0987654321",
    "is_default": false,
    "address_type": "home",
    "latitude": 12.345678,
    "longitude": 98.765432
}
```

**Validation Rules:**
- Maximum 3 addresses per user
- Phone number must be numeric
- Only one default address allowed per user
- Required fields: address, city, phone

### Get Single Address
```http
GET /api/addresses/{address_id}/
```

### Update Address
```http
PUT /api/addresses/{address_id}/
PATCH /api/addresses/{address_id}/
```

### Delete Address
```http
DELETE /api/addresses/{address_id}/
```

### Special Endpoints

#### Get Addresses with Coordinates
```http
GET /api/addresses/with_coordinates/
```
Returns only addresses that have both latitude and longitude set.

**Response:**
```json
{
    "count": 1,
    "results": [
        {
            "id": "uuid",
            "address": "123 Street Name",
            "latitude": 12.345678,
            "longitude": 98.765432,
            // ... other address fields
        }
    ]
}
```

#### Get Default Address
```http
GET /api/addresses/default/
```
Returns the user's default shipping address.

#### Set Address as Default
```http
POST /api/addresses/{address_id}/set_default/
```
Sets the specified address as the default address for the user.

#### Debug Information (Admin Only)
```http
GET /api/addresses/debug_info/
```
Returns debug information about the request and user (requires superuser privileges).

## Address Types
Available address types:
- `home`: Home address
- `office`: Office address
- `school`: School address
- `market`: Market address
- `other`: Other address type
- `business`: Business address
- `mailing`: Mailing address

## Rate Limiting
The API implements rate limiting using `UserRateThrottle`.

## Error Responses

### 400 Bad Request
```json
{
    "phone": ["Phone number must be numeric."],
    "non_field_errors": ["You can only have up to 3 addresses."]
}
```

### 401 Unauthorized
```json
{
    "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
    "detail": "Not authorized."
}
```

### 404 Not Found
```json
{
    "detail": "Address not found."
}
```

## Model Features
- UUID-based IDs for security
- Geocoding support (latitude/longitude)
- Automatic default address handling
- Full address formatting
- Comprehensive validation
- Timestamp tracking (created_at, updated_at)
- Phone number validation
- Multiple address types support
- Optimized database indexes
- Unique constraint enforcement for default addresses
