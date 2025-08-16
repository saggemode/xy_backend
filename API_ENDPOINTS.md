# Bank API Endpoints (ViewSet-based)

## Overview
The bank app now uses Django REST Framework ViewSets for a more consistent and RESTful API structure. All endpoints support filtering, searching, and ordering.

## Base URL
`/api/bank/`

## KYC Profile Endpoints

### List KYC Profiles
- **GET** `/api/bank/kyc-profiles/`
- **Description**: Get all KYC profiles (filtered by user permissions)
- **Filters**: `is_approved`, `created_at`
- **Search**: `user__username`, `user__email`, `bvn`, `nin`
- **Ordering**: `created_at`, `updated_at`

### Create KYC Profile
- **POST** `/api/bank/kyc-profiles/`
- **Description**: Create a new KYC profile
- **Required**: User must be verified
- **Body**: `bvn` or `nin`, `date_of_birth`, `address`, etc.

### Get KYC Profile
- **GET** `/api/bank/kyc-profiles/{id}/`
- **Description**: Get specific KYC profile details

### Update KYC Profile
- **PUT/PATCH** `/api/bank/kyc-profiles/{id}/`
- **Description**: Update KYC profile (only if not approved)

### Approve KYC Profile (Admin)
- **POST** `/api/bank/kyc-profiles/{id}/approve/`
- **Description**: Approve KYC profile (admin only)
- **Permissions**: `IsAdminUser`

### Reject KYC Profile (Admin)
- **POST** `/api/bank/kyc-profiles/{id}/reject/`
- **Description**: Reject KYC profile (admin only)
- **Permissions**: `IsAdminUser`

### Upgrade KYC Level (Admin)
- **POST** `/api/bank/kyc-profiles/{id}/upgrade_kyc_level/`
- **Description**: Upgrade KYC level (admin only)
- **Permissions**: `IsAdminUser`
- **Body**: `{"kyc_level": "tier_2"}` or `{"kyc_level": "tier_3"}`

### Get My KYC Limits
- **GET** `/api/bank/kyc-profiles/my_limits/`
- **Description**: Get current user's KYC limits and level
- **Response**: KYC level, daily transaction limit, max balance limit

### Check Upgrade Eligibility
- **GET** `/api/bank/kyc-profiles/upgrade_eligibility/`
- **Description**: Check if user is eligible for tier upgrade
- **Response**: Eligibility status, score, requirements, next tier

### Request Tier Upgrade
- **POST** `/api/bank/kyc-profiles/request_upgrade/`
- **Description**: Request tier upgrade (if eligible)
- **Response**: Success status and message

### Auto-Upgrade KYC Level (Admin)
- **POST** `/api/bank/kyc-profiles/{id}/auto_upgrade/`
- **Description**: Automatically upgrade KYC level if eligible (admin only)
- **Permissions**: `IsAdminUser`

## Wallet Endpoints

### List Wallets
- **GET** `/api/bank/wallets/`
- **Description**: Get all wallets (filtered by user permissions)
- **Filters**: `balance`, `created_at`
- **Ordering**: `balance`, `created_at`

### Get Wallet
- **GET** `/api/bank/wallets/{id}/`
- **Description**: Get specific wallet details

### Get My Wallet
- **GET** `/api/bank/wallets/my_wallet/`
- **Description**: Get current user's wallet

## Transaction Endpoints

### List Transactions
- **GET** `/api/bank/transactions/`
- **Description**: Get all transactions (filtered by user permissions)
- **Filters**: `transaction_type`, `status`, `timestamp`
- **Search**: `reference`, `description`
- **Ordering**: `amount`, `timestamp`

### Get Transaction
- **GET** `/api/bank/transactions/{id}/`
- **Description**: Get specific transaction details

### Get My Transactions
- **GET** `/api/bank/transactions/my_transactions/`
- **Description**: Get current user's transactions

## Bank Transfer Endpoints

### List Bank Transfers
- **GET** `/api/bank/bank-transfers/`
- **Description**: Get all bank transfers (filtered by user permissions)
- **Filters**: `status`, `bank_name`, `created_at`
- **Search**: `recipient_name`, `account_number`, `reference`
- **Ordering**: `amount`, `created_at`

### Create Bank Transfer
- **POST** `/api/bank/bank-transfers/`
- **Description**: Create a new bank transfer
- **Required**: Sufficient wallet balance
- **Body**: `amount`, `bank_name`, `account_number`, `recipient_name`, etc.

### Get Bank Transfer
- **GET** `/api/bank/bank-transfers/{id}/`
- **Description**: Get specific bank transfer details

### Update Bank Transfer
- **PUT/PATCH** `/api/bank/bank-transfers/{id}/`
- **Description**: Update bank transfer details

### Delete Bank Transfer
- **DELETE** `/api/bank/bank-transfers/{id}/`
- **Description**: Delete bank transfer

## Bill Payment Endpoints

### List Bill Payments
- **GET** `/api/bank/bill-payments/`
- **Description**: Get all bill payments (filtered by user permissions)
- **Filters**: `status`, `service_type`, `created_at`
- **Search**: `customer_id`, `reference`, `description`
- **Ordering**: `amount`, `created_at`

### Create Bill Payment
- **POST** `/api/bank/bill-payments/`
- **Description**: Create a new bill payment
- **Required**: Sufficient wallet balance
- **Body**: `amount`, `service_type`, `customer_id`, `description`, etc.

### Get Bill Payment
- **GET** `/api/bank/bill-payments/{id}/`
- **Description**: Get specific bill payment details

### Update Bill Payment
- **PUT/PATCH** `/api/bank/bill-payments/{id}/`
- **Description**: Update bill payment details

### Delete Bill Payment
- **DELETE** `/api/bank/bill-payments/{id}/`
- **Description**: Delete bill payment

## Utility Endpoints

### Get User Status
- **GET** `/api/bank/user-status/`
- **Description**: Get comprehensive user status including verification and KYC
- **Response**: User verification status, KYC status, wallet status

## KYC Levels and Limits

### Tier 1 (Default)
- **Daily Transaction Limit**: ₦50,000
- **Maximum Account Balance**: ₦300,000
- **Requirements**: Basic KYC verification

### Tier 2
- **Daily Transaction Limit**: ₦200,000
- **Maximum Account Balance**: ₦500,000
- **Requirements**: Enhanced KYC verification

### Tier 3
- **Daily Transaction Limit**: ₦5,000,000
- **Maximum Account Balance**: Unlimited
- **Requirements**: Full KYC verification

### Automatic Validation
- All transactions are automatically validated against KYC limits
- Balance changes are validated against maximum balance limits
- Daily transaction limits are reset at midnight

## Authentication
All endpoints require authentication using JWT tokens:
- **Header**: `Authorization: Bearer <your_jwt_token>`

## Permissions
- **Regular Users**: Can only access their own data
- **Staff Users**: Can access all data and perform admin actions

## Filtering Examples
```
# Filter KYC profiles by approval status
GET /api/bank/kyc-profiles/?is_approved=true

# Search transactions by reference
GET /api/bank/transactions/?search=REF123

# Order wallets by balance (descending)
GET /api/bank/wallets/?ordering=-balance

# Filter bank transfers by status and date
GET /api/bank/bank-transfers/?status=pending&created_at__gte=2024-01-01
```

## Error Handling
All endpoints return appropriate HTTP status codes:
- `200`: Success
- `201`: Created
- `400`: Bad Request (validation errors)
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `500`: Internal Server Error

## Response Format
All responses follow the standard DRF format:
```json
{
    "count": 10,
    "next": "http://example.com/api/bank/kyc-profiles/?page=2",
    "previous": null,
    "results": [...]
}
``` 