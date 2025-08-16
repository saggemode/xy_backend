# Fixed Savings API Documentation

## Overview

The Fixed Savings feature allows users to lock their funds for a fixed period and earn higher interest rates. The system automatically calculates interest rates based on the duration and pays out the matured amount to the user's XySave account.

## Interest Rate Structure

- **7-29 days**: 10% p.a
- **30-59 days**: 10% p.a  
- **60-89 days**: 12% p.a
- **90-179 days**: 15% p.a
- **180-364 days**: 18% p.a
- **365-1000 days**: 20% p.a

## Base URL

```
/bank/fixed-savings/
```

## Authentication

All endpoints require authentication. Include the Authorization header:
```
Authorization: Bearer <your_token>
```

## Endpoints

### 1. Fixed Savings Accounts

#### 1.1 List Fixed Savings Accounts
**GET** `/bank/fixed-savings/accounts/`

**Response:**
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "user": "username",
      "user_id": "uuid",
      "account_number": "FS12345678ABCDEF12",
      "amount": "100000.00",
      "source": "wallet",
      "source_display": "Wallet",
      "purpose": "education",
      "purpose_display": "Education",
      "purpose_description": "University tuition fees",
      "start_date": "2024-01-15",
      "payback_date": "2024-04-15",
      "auto_renewal_enabled": false,
      "is_active": true,
      "is_matured": false,
      "is_paid_out": false,
      "interest_rate": "15.00",
      "total_interest_earned": "0.00",
      "maturity_amount": "111780.82",
      "duration_days": 90,
      "days_remaining": 45,
      "is_mature": false,
      "can_be_paid_out": false,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z",
      "matured_at": null,
      "paid_out_at": null
    }
  ]
}
```

#### 1.2 Create Fixed Savings Account
**POST** `/bank/fixed-savings/accounts/`

**Request Body:**
```json
{
  "amount": "100000.00",
  "source": "wallet",
  "purpose": "education",
  "purpose_description": "University tuition fees",
  "start_date": "2024-01-15",
  "payback_date": "2024-04-15",
  "auto_renewal_enabled": false
}
```

**Validation Rules:**
- `amount`: Minimum ₦1,000
- `start_date`: Cannot be in the past
- `payback_date`: Must be after start_date
- Duration: 7-1000 days
- User must have sufficient funds in the specified source

**Response:**
```json
{
  "id": "uuid",
  "user": "username",
  "user_id": "uuid",
  "account_number": "FS12345678ABCDEF12",
  "amount": "100000.00",
  "source": "wallet",
  "source_display": "Wallet",
  "purpose": "education",
  "purpose_display": "Education",
  "purpose_description": "University tuition fees",
  "start_date": "2024-01-15",
  "payback_date": "2024-04-15",
  "auto_renewal_enabled": false,
  "is_active": true,
  "is_matured": false,
  "is_paid_out": false,
  "interest_rate": "15.00",
  "total_interest_earned": "0.00",
  "maturity_amount": "111780.82",
  "duration_days": 90,
  "days_remaining": 90,
  "is_mature": false,
  "can_be_paid_out": false,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "matured_at": null,
  "paid_out_at": null
}
```

#### 1.3 Get Fixed Savings Account Details
**GET** `/bank/fixed-savings/accounts/{id}/`

**Response:**
```json
{
  "id": "uuid",
  "user": "username",
  "user_id": "uuid",
  "account_number": "FS12345678ABCDEF12",
  "amount": "100000.00",
  "source": "wallet",
  "source_display": "Wallet",
  "purpose": "education",
  "purpose_display": "Education",
  "purpose_description": "University tuition fees",
  "start_date": "2024-01-15",
  "payback_date": "2024-04-15",
  "auto_renewal_enabled": false,
  "is_active": true,
  "is_matured": false,
  "is_paid_out": false,
  "interest_rate": "15.00",
  "total_interest_earned": "0.00",
  "maturity_amount": "111780.82",
  "duration_days": 90,
  "days_remaining": 45,
  "is_mature": false,
  "can_be_paid_out": false,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "matured_at": null,
  "paid_out_at": null,
  "transactions": [
    {
      "id": "uuid",
      "fixed_savings_account": "uuid",
      "transaction_type": "initial_deposit",
      "transaction_type_display": "Initial Deposit",
      "amount": "100000.00",
      "balance_before": "100000.00",
      "balance_after": "100000.00",
      "reference": "FS_INIT_uuid",
      "description": "Initial fixed savings deposit - Education",
      "interest_earned": "0.00",
      "interest_rate_applied": "15.00",
      "source_account": "wallet",
      "source_account_display": "Wallet",
      "source_transaction_id": null,
      "metadata": {},
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

#### 1.4 Pay Out Matured Fixed Savings
**POST** `/bank/fixed-savings/accounts/{id}/pay_out/`

**Response:**
```json
{
  "message": "Fixed savings paid out successfully"
}
```

#### 1.5 Auto-Renew Fixed Savings
**POST** `/bank/fixed-savings/accounts/{id}/auto_renew/`

**Response:**
```json
{
  "message": "Fixed savings auto-renewed successfully",
  "new_fixed_savings": {
    "id": "uuid",
    "user": "username",
    "account_number": "FS12345678ABCDEF13",
    "amount": "111780.82",
    "source": "xysave",
    "source_display": "XySave Account",
    "purpose": "education",
    "purpose_display": "Education",
    "purpose_description": "Auto-renewal of University tuition fees",
    "start_date": "2024-04-15",
    "payback_date": "2024-07-14",
    "auto_renewal_enabled": false,
    "is_active": true,
    "is_matured": false,
    "is_paid_out": false,
    "interest_rate": "15.00",
    "total_interest_earned": "0.00",
    "maturity_amount": "124825.82",
    "duration_days": 90,
    "days_remaining": 90,
    "is_mature": false,
    "can_be_paid_out": false,
    "created_at": "2024-04-15T10:30:00Z",
    "updated_at": "2024-04-15T10:30:00Z",
    "matured_at": null,
    "paid_out_at": null
  }
}
```

#### 1.6 Get Fixed Savings Summary
**GET** `/bank/fixed-savings/accounts/summary/`

**Response:**
```json
{
  "total_active_fixed_savings": 2,
  "total_active_amount": "₦200,000.00",
  "total_maturity_amount": "₦223,561.64",
  "total_interest_earned": "₦23,561.64",
  "matured_unpaid_count": 1,
  "matured_unpaid_amount": "111780.82"
}
```

#### 1.7 Get Fixed Savings Choices
**GET** `/bank/fixed-savings/accounts/choices/`

**Response:**
```json
{
  "purposes": [
    {"value": "education", "label": "Education"},
    {"value": "business", "label": "Business"},
    {"value": "investment", "label": "Investment"},
    {"value": "emergency", "label": "Emergency Fund"},
    {"value": "travel", "label": "Travel"},
    {"value": "wedding", "label": "Wedding"},
    {"value": "vehicle", "label": "Vehicle"},
    {"value": "home_renovation", "label": "Home Renovation"},
    {"value": "medical", "label": "Medical"},
    {"value": "retirement", "label": "Retirement"},
    {"value": "other", "label": "Other"}
  ],
  "sources": [
    {"value": "wallet", "label": "Wallet"},
    {"value": "xysave", "label": "XySave Account"},
    {"value": "both", "label": "Both Wallet and XySave"}
  ]
}
```

#### 1.8 Calculate Interest Rate
**POST** `/bank/fixed-savings/accounts/calculate_interest/`

**Request Body:**
```json
{
  "amount": "100000.00",
  "start_date": "2024-01-15",
  "payback_date": "2024-04-15"
}
```

**Response:**
```json
{
  "amount": "100000.00",
  "start_date": "2024-01-15",
  "payback_date": "2024-04-15",
  "interest_rate": "15.00",
  "maturity_amount": "₦111,780.82",
  "interest_earned": "₦11,780.82",
  "duration_days": 90
}
```

#### 1.9 Filter Fixed Savings Accounts

**GET** `/bank/fixed-savings/accounts/search/?q=education&purpose=education&source=wallet&status=active`

**Query Parameters:**
- `q`: Search query (account number, purpose description)
- `purpose`: Filter by purpose
- `source`: Filter by source
- `status`: Filter by status (active, matured, paid_out)

#### 1.10 Get Active Fixed Savings
**GET** `/bank/fixed-savings/accounts/active/`

#### 1.11 Get Matured Fixed Savings
**GET** `/bank/fixed-savings/accounts/matured/`

#### 1.12 Get Matured Unpaid Fixed Savings
**GET** `/bank/fixed-savings/accounts/matured_unpaid/`

### 2. Fixed Savings Transactions

#### 2.1 List Fixed Savings Transactions
**GET** `/bank/fixed-savings/transactions/`

**Response:**
```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "fixed_savings_account": "uuid",
      "transaction_type": "initial_deposit",
      "transaction_type_display": "Initial Deposit",
      "amount": "100000.00",
      "balance_before": "100000.00",
      "balance_after": "100000.00",
      "reference": "FS_INIT_uuid",
      "description": "Initial fixed savings deposit - Education",
      "interest_earned": "0.00",
      "interest_rate_applied": "15.00",
      "source_account": "wallet",
      "source_account_display": "Wallet",
      "source_transaction_id": null,
      "metadata": {},
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

#### 2.2 Get Transactions by Account
**GET** `/bank/fixed-savings/transactions/by_account/?account_id=uuid`

#### 2.3 Get Transactions by Type
**GET** `/bank/fixed-savings/transactions/by_type/?type=initial_deposit`

#### 2.4 Get Recent Transactions
**GET** `/bank/fixed-savings/transactions/recent/?limit=10`

### 3. Fixed Savings Settings

#### 3.1 Get User Settings
**GET** `/bank/fixed-savings/settings/my_settings/`

**Response:**
```json
{
  "id": "uuid",
  "user": "username",
  "maturity_notifications": true,
  "interest_notifications": true,
  "auto_renewal_notifications": true,
  "default_auto_renewal": false,
  "default_renewal_duration": 30,
  "default_source": "wallet",
  "default_source_display": "Wallet",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

#### 3.2 Update Notification Preferences
**POST** `/bank/fixed-savings/settings/update_notifications/`

**Request Body:**
```json
{
  "maturity_notifications": true,
  "interest_notifications": true,
  "auto_renewal_notifications": false
}
```

#### 3.3 Update User Preferences
**POST** `/bank/fixed-savings/settings/update_preferences/`

**Request Body:**
```json
{
  "default_auto_renewal": true,
  "default_renewal_duration": 60,
  "default_source": "xysave"
}
```

## Error Responses

### Validation Error
```json
{
  "error": "Insufficient funds for fixed savings"
}
```

### Not Found Error
```json
{
  "error": "Fixed savings account not found"
}
```

### Permission Error
```json
{
  "error": "You do not have permission to perform this action"
}
```

## Notification Types

The following notifications are sent for Fixed Savings events:

1. **FIXED_SAVINGS_CREATED**: When a fixed savings account is created
2. **FIXED_SAVINGS_MATURED**: When a fixed savings account matures
3. **FIXED_SAVINGS_PAID_OUT**: When a matured fixed savings is paid out
4. **FIXED_SAVINGS_INTEREST_CREDITED**: When interest is credited
5. **FIXED_SAVINGS_AUTO_RENEWAL**: When auto-renewal occurs
6. **FIXED_SAVINGS_MATURITY_REMINDER**: Reminder before maturity
7. **FIXED_SAVINGS_EARLY_WITHDRAWAL**: For early withdrawals

## SDK Examples

### JavaScript/TypeScript

```javascript
// Create fixed savings
const createFixedSavings = async (data) => {
  const response = await fetch('/bank/fixed-savings/accounts/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(data)
  });
  return response.json();
};

// Get fixed savings summary
const getFixedSavingsSummary = async () => {
  const response = await fetch('/bank/fixed-savings/accounts/summary/', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.json();
};

// Pay out matured fixed savings
const payOutFixedSavings = async (accountId) => {
  const response = await fetch(`/bank/fixed-savings/accounts/${accountId}/pay_out/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.json();
};
```

### Python

```python
import requests

class FixedSavingsAPI:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def create_fixed_savings(self, data):
        response = requests.post(
            f'{self.base_url}/bank/fixed-savings/accounts/',
            json=data,
            headers=self.headers
        )
        return response.json()
    
    def get_summary(self):
        response = requests.get(
            f'{self.base_url}/bank/fixed-savings/accounts/summary/',
            headers=self.headers
        )
        return response.json()
    
    def pay_out(self, account_id):
        response = requests.post(
            f'{self.base_url}/bank/fixed-savings/accounts/{account_id}/pay_out/',
            headers=self.headers
        )
        return response.json()
```

## Business Logic

### Interest Calculation
- Interest is calculated daily based on the annual rate
- Formula: `Daily Interest = Principal × (Annual Rate ÷ 365) × Days`
- Maturity amount includes principal plus accumulated interest

### Fund Deduction
- When creating fixed savings, funds are automatically deducted from the specified source
- For "both" source, amount is split equally between wallet and XySave
- Deduction happens atomically with account creation

### Payout Process
- Matured fixed savings are paid out to the user's XySave account
- Payout includes principal plus all accumulated interest
- Payout is irreversible once processed

### Auto-Renewal
- If enabled, matured fixed savings automatically renew for the same duration
- New fixed savings uses the maturity amount as principal
- Auto-renewal creates a new fixed savings account with new dates

## Security Considerations

1. **Authentication**: All endpoints require valid authentication
2. **Authorization**: Users can only access their own fixed savings
3. **Validation**: Comprehensive validation of all input data
4. **Atomic Operations**: Critical operations use database transactions
5. **Audit Trail**: All transactions are logged with full details

## Rate Limiting

- Standard rate limiting applies to all endpoints
- Create operations are limited to prevent abuse
- Pay out operations have additional rate limiting

## Monitoring

The system monitors:
- Fixed savings creation rates
- Maturity and payout statistics
- Interest calculation accuracy
- Auto-renewal success rates
- Notification delivery rates 