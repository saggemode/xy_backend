# 🏦 Spend and Save API Documentation

## Overview
Enhanced REST API endpoints for Spend and Save functionality with integrated notifications and analytics.

## Base URL
`/api/bank/spend-and-save/`

## Authentication
All endpoints require authentication. Include your JWT token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

---

## 📊 Account Management Endpoints

### 1. Activate Spend and Save Account
**POST** `/api/bank/spend-and-save/accounts/activate/`

**Description**: Activate Spend and Save functionality for the current user

**Request Body**:
```json
{
    "savings_percentage": 5.00,
    "fund_source": "wallet",
    "initial_amount": 1000.00,
    "wallet_amount": 500.00,
    "xysave_amount": 500.00
}
```

**Response**:
```json
{
    "message": "Spend and Save activated successfully",
    "account": {
        "account_number": "8123456789",
        "balance": "1000.00",
        "savings_percentage": 5.00,
        "is_active": true,
        "total_saved_from_spending": "0.00",
        "total_interest_earned": "0.00"
    }
}
```

**Notifications**: Sends account activation notification to user

---

### 2. Deactivate Spend and Save Account
**POST** `/api/bank/spend-and-save/accounts/deactivate/`

**Description**: Deactivate Spend and Save functionality

**Response**:
```json
{
    "message": "Spend and Save deactivated successfully",
    "account": {
        "account_number": "8123456789",
        "balance": "1500.00",
        "is_active": false
    }
}
```

**Notifications**: Sends account deactivation notification to user

---

### 3. Get Account Summary
**GET** `/api/bank/spend-and-save/accounts/summary/`

**Description**: Get comprehensive account summary

**Response**:
```json
{
    "account": {
        "account_number": "8123456789",
        "balance": "1500.00",
        "savings_percentage": 5.00,
        "is_active": true,
        "total_saved_from_spending": "500.00",
        "total_interest_earned": "25.50",
        "total_transactions_processed": 15
    },
    "settings": {
        "preferred_savings_percentage": 5.00,
        "min_transaction_threshold": "100.00",
        "default_withdrawal_destination": "wallet"
    },
    "interest_breakdown": {
        "tier_1": {"amount": 10000, "interest": 5.48},
        "tier_2": {"amount": 5000, "interest": 2.19},
        "tier_3": {"amount": 0, "interest": 0},
        "total_interest": 7.67
    }
}
```

---

### 4. Get Dashboard Data
**GET** `/api/bank/spend-and-save/accounts/dashboard/`

**Description**: Get dashboard data with charts and analytics

**Response**:
```json
{
    "account_summary": {...},
    "recent_transactions": [...],
    "savings_progress": {
        "current_week": 150.00,
        "last_week": 120.00,
        "growth_percentage": 25.0
    },
    "interest_forecast": {
        "daily": 7.67,
        "weekly": 53.69,
        "monthly": 230.10
    }
}
```

---

### 5. Withdraw from Spend and Save
**POST** `/api/bank/spend-and-save/accounts/withdraw/`

**Description**: Withdraw funds from Spend and Save account

**Request Body**:
```json
{
    "amount": 500.00,
    "destination": "wallet"
}
```

**Response**:
```json
{
    "message": "Withdrawal successful",
    "transaction": {
        "reference": "uuid-here",
        "amount": "500.00",
        "destination": "wallet",
        "balance_after": "1000.00"
    }
}
```

**Notifications**: Sends withdrawal notification to user

---

## 📈 Analytics & Reporting Endpoints

### 6. Get Weekly Summary
**GET** `/api/bank/spend-and-save/accounts/weekly_summary/`

**Description**: Get weekly savings summary

**Response**:
```json
{
    "total_spent": 3000.00,
    "total_saved": 150.00,
    "transactions_count": 12,
    "savings_rate": 5.0,
    "week_start": "2024-01-15",
    "week_end": "2024-01-22"
}
```

---

### 7. Get Savings Goals
**GET** `/api/bank/spend-and-save/accounts/savings_goals/`

**Description**: Get user's savings goals and progress

**Response**:
```json
{
    "goals": [
        {
            "name": "First ₦100",
            "icon": "💰",
            "target_amount": 100,
            "current_amount": 500,
            "progress": 100.0,
            "achieved": true,
            "remaining": 0
        },
        {
            "name": "₦500 Milestone",
            "icon": "🎯",
            "target_amount": 500,
            "current_amount": 500,
            "progress": 100.0,
            "achieved": true,
            "remaining": 0
        },
        {
            "name": "₦1,000 Goal",
            "icon": "🏆",
            "target_amount": 1000,
            "current_amount": 500,
            "progress": 50.0,
            "achieved": false,
            "remaining": 500
        }
    ],
    "total_saved": 500,
    "next_goal": {
        "name": "₦1,000 Goal",
        "icon": "🏆",
        "target_amount": 1000,
        "current_amount": 500,
        "progress": 50.0,
        "achieved": false,
        "remaining": 500
    }
}
```

---

### 8. Send Weekly Summary Notification
**POST** `/api/bank/spend-and-save/accounts/send_weekly_summary/`

**Description**: Manually trigger weekly summary notification

**Response**:
```json
{
    "message": "Weekly summary notification sent successfully",
    "weekly_stats": {
        "total_spent": 3000.00,
        "total_saved": 150.00,
        "transactions_count": 12
    }
}
```

**Notifications**: Sends weekly summary notification to user

---

## 🔔 Notification Endpoints

### 9. Get Spend and Save Notifications
**GET** `/api/bank/spend-and-save/accounts/notifications/`

**Description**: Get user's Spend and Save related notifications

**Response**:
```json
{
    "notifications": [
        {
            "id": "uuid-here",
            "title": "🎉 Spend and Save Activated!",
            "message": "Your Spend and Save account has been successfully activated...",
            "notification_type": "account_update",
            "level": "success",
            "isRead": false,
            "created_at": "2024-01-22T10:30:00Z",
            "extra_data": {
                "account_number": "8123456789",
                "savings_percentage": 5.0,
                "action_url": "/spend-and-save/dashboard"
            }
        }
    ],
    "unread_count": 3
}
```

---

## 📊 Transaction Analytics

### 10. Get Transaction Analytics
**GET** `/api/bank/spend-and-save/transactions/analytics/`

**Query Parameters**:
- `days` (optional): Number of days to analyze (default: 30)

**Response**:
```json
{
    "period": {
        "start_date": "2023-12-23",
        "end_date": "2024-01-22",
        "days": 30
    },
    "summary": {
        "total_saved": 750.00,
        "total_withdrawn": 200.00,
        "total_interest": 25.50,
        "net_savings": 575.50,
        "total_transactions": 45
    },
    "daily_breakdown": [
        {
            "date": "2024-01-22",
            "saved": 25.00,
            "withdrawn": 0,
            "interest": 0.85,
            "transactions": 3
        }
    ]
}
```

---

### 11. Export Transaction History
**GET** `/api/bank/spend-and-save/transactions/export/`

**Description**: Export transaction history as CSV

**Query Parameters**:
- `days` (optional): Number of days to export (default: 90)

**Response**: CSV file download

---

## 💰 Interest Management

### 12. Calculate Interest
**POST** `/api/bank/spend-and-save/interest/calculate_interest/`

**Description**: Calculate interest for current user

**Response**:
```json
{
    "interest_amount": "7.67",
    "breakdown": {
        "tier_1": {"amount": 10000, "interest": 5.48},
        "tier_2": {"amount": 5000, "interest": 2.19},
        "tier_3": {"amount": 0, "interest": 0}
    },
    "total_balance": "15000.00"
}
```

---

### 13. Credit Interest
**POST** `/api/bank/spend-and-save/interest/credit_interest/`

**Description**: Credit calculated interest to account

**Response**:
```json
{
    "message": "Interest credited successfully",
    "interest_amount": "7.67",
    "new_balance": "15007.67"
}
```

**Notifications**: Sends interest credited notification to user

---

### 14. Get Interest Forecast
**GET** `/api/bank/spend-and-save/interest/interest_forecast/`

**Query Parameters**:
- `days` (optional): Number of days to forecast (default: 30)

**Response**:
```json
{
    "forecast": {
        "daily": "7.67",
        "weekly": "53.69",
        "monthly": "230.10",
        "yearly": "2798.55"
    },
    "breakdown": {
        "tier_1": {"rate": 20, "amount": 10000, "daily_interest": 5.48},
        "tier_2": {"rate": 16, "amount": 5000, "daily_interest": 2.19},
        "tier_3": {"rate": 8, "amount": 0, "daily_interest": 0}
    }
}
```

---

### 15. Get Tiered Rates Info
**GET** `/api/bank/spend-and-save/interest/tiered_rates_info/`

**Description**: Get information about tiered interest rates

**Response**:
```json
{
    "tier_1": {
        "rate": 20,
        "daily_rate": 0.000548,
        "description": "First ₦10,000 at 20% p.a",
        "example": "₦10,000 earns ₦5.48 daily interest"
    },
    "tier_2": {
        "rate": 16,
        "daily_rate": 0.000438,
        "description": "Next ₦90,000 at 16% p.a",
        "example": "₦50,000 earns ₦21.92 daily interest"
    },
    "tier_3": {
        "rate": 8,
        "daily_rate": 0.000219,
        "description": "Above ₦100,000 at 8% p.a",
        "example": "₦50,000 earns ₦10.95 daily interest"
    },
    "calculation_method": "Daily interest is calculated and credited automatically",
    "payout_frequency": "Daily at 11:00 AM",
    "minimum_balance": "No minimum balance required"
}
```

---

## ⚙️ Settings Management

### 16. Update Settings
**PATCH** `/api/bank/spend-and-save/settings/update_settings/`

**Description**: Update Spend and Save settings

**Request Body**:
```json
{
    "preferred_savings_percentage": 7.50,
    "min_transaction_threshold": "200.00",
    "default_withdrawal_destination": "xysave"
}
```

**Response**:
```json
{
    "message": "Settings updated successfully",
    "settings": {
        "preferred_savings_percentage": 7.50,
        "min_transaction_threshold": "200.00",
        "default_withdrawal_destination": "xysave"
    }
}
```

---

## 📈 Statistics (Admin Only)

### 17. Get Overview Statistics
**GET** `/api/bank/spend-and-save/statistics/overview/`

**Description**: Get overview statistics (admin/staff only)

**Response**:
```json
{
    "total_users": 1250,
    "active_accounts": 980,
    "total_saved_amount": "125000.00",
    "total_interest_paid": "6250.00",
    "average_savings_percentage": 5.25,
    "total_transactions_processed": 15420,
    "daily_interest_payouts": 980,
    "monthly_growth_rate": 15.5
}
```

---

### 18. Process Daily Interest
**POST** `/api/bank/spend-and-save/statistics/process_daily_interest/`

**Description**: Process daily interest payout for all active accounts (admin only)

**Response**:
```json
{
    "message": "Processed daily interest for 980 accounts",
    "processed_count": 980
}
```

---

## 🔄 Processing Endpoints

### 19. Process Spending Transaction
**POST** `/api/bank/spend-and-save/transactions/process_spending/`

**Description**: Process a spending transaction for auto-save

**Request Body**:
```json
{
    "transaction_id": 12345,
    "amount": 1000.00,
    "description": "Grocery shopping"
}
```

**Response**:
```json
{
    "message": "Auto-save processed successfully",
    "saved_amount": "50.00",
    "savings_percentage": 5.00,
    "new_balance": "1050.00"
}
```

**Notifications**: Sends automatic save notification to user

---

## 🎯 Notification Types

The system sends the following types of notifications:

1. **Account Activation** - When Spend and Save is activated
2. **Account Deactivation** - When Spend and Save is deactivated
3. **Automatic Save** - When money is automatically saved from spending
4. **Savings Milestones** - When reaching ₦100, ₦500, ₦1,000, etc.
5. **Interest Credited** - When daily interest is credited
6. **Withdrawal** - When funds are withdrawn
7. **Weekly Summary** - Weekly savings summary
8. **Goal Achievement** - When savings goals are reached

---

## 📱 Mobile App Integration

### WebSocket Notifications
For real-time notifications, connect to the WebSocket endpoint:
```
ws://your-domain/ws/notifications/
```

### Push Notifications
For mobile push notifications, use the notification preferences endpoint:
```
GET /api/notifications/preferences/
```

---

## 🔒 Security Features

- All endpoints require authentication
- Rate limiting applied to all endpoints
- Input validation and sanitization
- Audit logging for all transactions
- CSRF protection enabled

---

## 📊 Error Responses

### Standard Error Format
```json
{
    "error": "Error message here",
    "code": "ERROR_CODE",
    "details": {
        "field": "Additional error details"
    }
}
```

### Common Error Codes
- `ACCOUNT_NOT_FOUND` - Spend and Save account not found
- `INSUFFICIENT_BALANCE` - Insufficient balance for operation
- `ACCOUNT_NOT_ACTIVE` - Account is not active
- `INVALID_AMOUNT` - Invalid amount provided
- `ACCESS_DENIED` - User doesn't have permission

---

## 🚀 Getting Started

1. **Activate Spend and Save**:
   ```bash
   curl -X POST /api/bank/spend-and-save/accounts/activate/ \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"savings_percentage": 5.00, "fund_source": "wallet"}'
   ```

2. **Get Account Summary**:
   ```bash
   curl -X GET /api/bank/spend-and-save/accounts/summary/ \
     -H "Authorization: Bearer <token>"
   ```

3. **Get Notifications**:
   ```bash
   curl -X GET /api/bank/spend-and-save/accounts/notifications/ \
     -H "Authorization: Bearer <token>"
   ```

---

## 📈 Analytics Examples

### Weekly Progress Tracking
```javascript
// Get weekly summary
const weeklySummary = await fetch('/api/bank/spend-and-save/accounts/weekly_summary/');
const data = await weeklySummary.json();

// Display savings progress
console.log(`This week you saved ₦${data.total_saved} from ₦${data.total_spent} spending`);
```

### Goal Tracking
```javascript
// Get savings goals
const goals = await fetch('/api/bank/spend-and-save/accounts/savings_goals/');
const goalData = await goals.json();

// Show next goal
const nextGoal = goalData.next_goal;
console.log(`Next goal: ${nextGoal.name} - ${nextGoal.progress}% complete`);
```

---

This enhanced API provides comprehensive functionality for Spend and Save operations with integrated notifications, analytics, and reporting features. 