# Target Saving API Documentation

## Overview

The Target Saving API provides comprehensive functionality for users to create, manage, and track their savings goals with specific target amounts, categories, and timeframes. The system includes automatic notifications, milestone tracking, and detailed analytics.

## Base URL
```
/api/target-saving/
```

## Authentication
All endpoints require authentication. Include the Authorization header:
```
Authorization: Bearer <your_token>
```

## Target Saving Endpoints

### 1. Get Available Categories
**GET** `/api/target-saving/targets/categories/`

Returns all available target saving categories.

**Response:**
```json
{
  "success": true,
  "categories": [
    {"value": "accommodation", "label": "Accommodation"},
    {"value": "education", "label": "Education"},
    {"value": "business", "label": "Business"},
    {"value": "japa", "label": "Japa (Relocation)"},
    {"value": "vehicle", "label": "Vehicle"},
    {"value": "wedding", "label": "Wedding"},
    {"value": "emergency", "label": "Emergency Fund"},
    {"value": "investment", "label": "Investment"},
    {"value": "travel", "label": "Travel"},
    {"value": "home_renovation", "label": "Home Renovation"},
    {"value": "medical", "label": "Medical"},
    {"value": "entertainment", "label": "Entertainment"},
    {"value": "other", "label": "Other"}
  ]
}
```

### 2. Get Available Frequencies
**GET** `/api/target-saving/targets/frequencies/`

Returns all available frequency options.

**Response:**
```json
{
  "success": true,
  "frequencies": [
    {"value": "daily", "label": "Daily"},
    {"value": "weekly", "label": "Weekly"},
    {"value": "monthly", "label": "Monthly"}
  ]
}
```

### 3. Get Deposit Days
**GET** `/api/target-saving/targets/deposit_days/`

Returns available deposit days for weekly/monthly frequency.

**Response:**
```json
{
  "success": true,
  "days": [
    {"value": "monday", "label": "Monday"},
    {"value": "tuesday", "label": "Tuesday"},
    {"value": "wednesday", "label": "Wednesday"},
    {"value": "thursday", "label": "Thursday"},
    {"value": "friday", "label": "Friday"},
    {"value": "saturday", "label": "Saturday"},
    {"value": "sunday", "label": "Sunday"}
  ]
}
```

### 4. Create Target Saving
**POST** `/api/target-saving/targets/`

Create a new target saving.

**Request Body:**
```json
{
  "name": "New Car Fund",
  "category": "vehicle",
  "target_amount": 5000000.00,
  "frequency": "monthly",
  "preferred_deposit_day": "friday",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31"
}
```

**Response:**
```json
{
  "id": "uuid-here",
  "user": "user-id",
  "name": "New Car Fund",
  "category": "vehicle",
  "category_display": "Vehicle",
  "target_amount": "5000000.00",
  "frequency": "monthly",
  "frequency_display": "Monthly",
  "preferred_deposit_day": "friday",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "current_amount": "0.00",
  "is_active": true,
  "is_completed": false,
  "progress_percentage": 0.0,
  "remaining_amount": "5000000.00",
  "days_remaining": 365,
  "is_overdue": false,
  "daily_target": "13698.63",
  "weekly_target": "95890.41",
  "monthly_target": "416666.67",
  "recent_deposits": [],
  "total_deposits": 0,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### 5. List Target Savings
**GET** `/api/target-saving/targets/`

Get all target savings for the authenticated user.

**Query Parameters:**
- `is_active` (optional): Filter by active status
- `category` (optional): Filter by category
- `is_completed` (optional): Filter by completion status

**Response:**
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "uuid-1",
      "name": "New Car Fund",
      "category": "vehicle",
      "category_display": "Vehicle",
      "target_amount": "5000000.00",
      "frequency": "monthly",
      "frequency_display": "Monthly",
      "preferred_deposit_day": "friday",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31",
      "current_amount": "1000000.00",
      "is_active": true,
      "is_completed": false,
      "progress_percentage": 20.0,
      "remaining_amount": "4000000.00",
      "days_remaining": 200,
      "is_overdue": false,
      "daily_target": "20000.00",
      "weekly_target": "140000.00",
      "monthly_target": "600000.00",
      "recent_deposits": [...],
      "total_deposits": 5,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-15T00:00:00Z"
    }
  ]
}
```

### 6. Get Target Saving Details
**GET** `/api/target-saving/targets/{id}/`

Get detailed information about a specific target saving.

**Response:**
```json
{
  "success": true,
  "target_saving": {
    "id": "uuid-here",
    "name": "New Car Fund",
    "category": "vehicle",
    "category_display": "Vehicle",
    "target_amount": "5000000.00",
    "frequency": "monthly",
    "frequency_display": "Monthly",
    "preferred_deposit_day": "friday",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "current_amount": "1000000.00",
    "is_active": true,
    "is_completed": false,
    "progress_percentage": 20.0,
    "remaining_amount": "4000000.00",
    "days_remaining": 200,
    "is_overdue": false,
    "daily_target": "20000.00",
    "weekly_target": "140000.00",
    "monthly_target": "600000.00",
    "recent_deposits": [...],
    "total_deposits": 5,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-15T00:00:00Z"
  },
  "recent_deposits": [
    {
      "id": "deposit-uuid",
      "amount": "200000.00",
      "notes": "Monthly deposit",
      "deposit_date": "2024-01-15T10:30:00Z"
    }
  ],
  "total_deposits": 5,
  "progress_percentage": 20.0,
  "remaining_amount": "4000000.00",
  "days_remaining": 200
}
```

### 7. Update Target Saving
**PUT** `/api/target-saving/targets/{id}/`

Update an existing target saving.

**Request Body:**
```json
{
  "name": "Updated Car Fund",
  "target_amount": 6000000.00,
  "end_date": "2025-06-30"
}
```

**Response:**
```json
{
  "id": "uuid-here",
  "name": "Updated Car Fund",
  "category": "vehicle",
  "category_display": "Vehicle",
  "target_amount": "6000000.00",
  "frequency": "monthly",
  "frequency_display": "Monthly",
  "preferred_deposit_day": "friday",
  "start_date": "2024-01-01",
  "end_date": "2025-06-30",
  "current_amount": "1000000.00",
  "is_active": true,
  "is_completed": false,
  "progress_percentage": 16.67,
  "remaining_amount": "5000000.00",
  "days_remaining": 545,
  "is_overdue": false,
  "daily_target": "9174.31",
  "weekly_target": "64220.17",
  "monthly_target": "277777.78",
  "recent_deposits": [...],
  "total_deposits": 5,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-20T00:00:00Z"
}
```

### 8. Make Deposit
**POST** `/api/target-saving/targets/{id}/make_deposit/`

Make a deposit to a target saving.

**Request Body:**
```json
{
  "amount": 50000.00,
  "notes": "Extra savings from bonus"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Deposit made successfully",
  "deposit": {
    "id": "deposit-uuid",
    "amount": "50000.00",
    "notes": "Extra savings from bonus",
    "deposit_date": "2024-01-20T14:30:00Z"
  },
  "target_saving": {
    "id": "target-uuid",
    "name": "New Car Fund",
    "current_amount": "1050000.00",
    "progress_percentage": 21.0,
    "is_completed": false
  }
}
```

### 9. Get Target Analytics
**GET** `/api/target-saving/targets/{id}/analytics/`

Get detailed analytics for a target saving.

**Response:**
```json
{
  "success": true,
  "analytics": {
    "total_deposits": 5,
    "average_deposit": "210000.00",
    "deposit_frequency": 3.0,
    "progress_percentage": 21.0,
    "remaining_amount": "3950000.00",
    "days_remaining": 200,
    "is_overdue": false,
    "daily_target": "19750.00",
    "weekly_target": "138250.00",
    "monthly_target": "598958.33"
  }
}
```

### 10. Get Target Deposits
**GET** `/api/target-saving/targets/{id}/deposits/`

Get all deposits for a specific target saving.

**Query Parameters:**
- `page` (optional): Page number for pagination
- `page_size` (optional): Number of items per page

**Response:**
```json
{
  "success": true,
  "deposits": [
    {
      "id": "deposit-uuid-1",
      "amount": "200000.00",
      "notes": "Monthly deposit",
      "deposit_date": "2024-01-15T10:30:00Z"
    },
    {
      "id": "deposit-uuid-2",
      "amount": "50000.00",
      "notes": "Extra savings from bonus",
      "deposit_date": "2024-01-20T14:30:00Z"
    }
  ],
  "count": 5
}
```

### 11. Export Target Deposits
**GET** `/api/target-saving/targets/{id}/export_deposits/`

Export deposits for a target saving as CSV.

**Response:** CSV file download

### 12. Deactivate Target Saving
**POST** `/api/target-saving/targets/{id}/deactivate/`

Deactivate a target saving.

**Response:**
```json
{
  "success": true,
  "message": "Target saving deactivated successfully"
}
```

### 13. Get Target Summary
**GET** `/api/target-saving/targets/summary/`

Get summary statistics for all target savings.

**Response:**
```json
{
  "success": true,
  "summary": {
    "total_targets": 3,
    "active_targets": 2,
    "completed_targets": 1,
    "overdue_targets": 0,
    "total_target_amount": "15000000.00",
    "total_current_amount": "3500000.00",
    "total_progress_percentage": 23.33,
    "category_breakdown": [
      {
        "category": "vehicle",
        "count": 2,
        "total_target": "11000000.00",
        "total_current": "2500000.00"
      },
      {
        "category": "education",
        "count": 1,
        "total_target": "4000000.00",
        "total_current": "1000000.00"
      }
    ]
  }
}
```

### 14. Get Overdue Targets
**GET** `/api/target-saving/targets/overdue/`

Get all overdue target savings.

**Response:**
```json
{
  "success": true,
  "overdue_targets": [
    {
      "id": "uuid-here",
      "name": "Overdue Target",
      "category": "vehicle",
      "category_display": "Vehicle",
      "target_amount": "5000000.00",
      "current_amount": "2000000.00",
      "progress_percentage": 40.0,
      "end_date": "2023-12-31",
      "is_overdue": true
    }
  ],
  "count": 1
}
```

### 15. Get Completed Targets
**GET** `/api/target-saving/targets/completed/`

Get all completed target savings.

**Response:**
```json
{
  "success": true,
  "completed_targets": [
    {
      "id": "uuid-here",
      "name": "Completed Target",
      "category": "education",
      "category_display": "Education",
      "target_amount": "1000000.00",
      "current_amount": "1000000.00",
      "progress_percentage": 100.0,
      "is_completed": true
    }
  ],
  "count": 1
}
```

### 16. Send Reminder
**POST** `/api/target-saving/targets/send_reminder/`

Send a reminder notification for a target saving.

**Request Body:**
```json
{
  "target_id": "target-uuid",
  "reminder_type": "weekly"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Weekly reminder sent successfully"
}
```

### 17. Get Target Notifications
**GET** `/api/target-saving/targets/notifications/`

Get target saving related notifications.

**Response:**
```json
{
  "success": true,
  "notifications": [
    {
      "id": "notification-uuid",
      "title": "🎯 New Target Saving Created!",
      "message": "Your target 'New Car Fund' has been created successfully. Target amount: ₦5,000,000.00, End date: December 31, 2024",
      "notification_type": "target_saving_created",
      "level": "success",
      "isRead": false,
      "created_at": "2024-01-01T00:00:00Z",
      "extra_data": {
        "target_id": "target-uuid",
        "target_name": "New Car Fund",
        "target_amount": 5000000.0,
        "category": "vehicle",
        "frequency": "monthly",
        "end_date": "2024-12-31",
        "action_url": "/target-savings/target-uuid"
      }
    }
  ],
  "count": 5
}
```

## Deposit Endpoints

### 1. Get Deposit Analytics
**GET** `/api/target-saving/deposits/analytics/`

Get analytics across all deposits.

**Query Parameters:**
- `start_date` (optional): Filter from date (YYYY-MM-DD)
- `end_date` (optional): Filter to date (YYYY-MM-DD)

**Response:**
```json
{
  "success": true,
  "analytics": {
    "total_deposits": 15,
    "total_amount": "3500000.00",
    "average_deposit": "233333.33",
    "monthly_breakdown": [
      {
        "month": 1,
        "count": 5,
        "total": "1000000.00"
      },
      {
        "month": 2,
        "count": 3,
        "total": "750000.00"
      }
    ],
    "target_breakdown": [
      {
        "target_saving__name": "New Car Fund",
        "target_saving__category": "vehicle",
        "count": 8,
        "total": "2000000.00"
      },
      {
        "target_saving__name": "Education Fund",
        "target_saving__category": "education",
        "count": 7,
        "total": "1500000.00"
      }
    ]
  }
}
```

### 2. Export All Deposits
**GET** `/api/target-saving/deposits/export/`

Export all deposits as CSV.

**Query Parameters:**
- `start_date` (optional): Filter from date (YYYY-MM-DD)
- `end_date` (optional): Filter to date (YYYY-MM-DD)

**Response:** CSV file download

## Notification Types

The target saving system sends the following notification types:

### 1. Target Saving Created
- **Type:** `target_saving_created`
- **Level:** `success`
- **Triggered:** When a new target saving is created

### 2. Target Saving Updated
- **Type:** `target_saving_updated`
- **Level:** `info`
- **Triggered:** When a target saving is updated

### 3. Target Saving Completed
- **Type:** `target_saving_completed`
- **Level:** `success`
- **Triggered:** When a target saving reaches 100% progress

### 4. Target Saving Deposit
- **Type:** `target_saving_deposit`
- **Level:** `success`
- **Triggered:** When a deposit is made to a target saving

### 5. Target Saving Milestone
- **Type:** `target_saving_milestone`
- **Level:** `success`
- **Triggered:** When progress reaches 25%, 50%, 75%, or 90%

### 6. Target Saving Overdue
- **Type:** `target_saving_overdue`
- **Level:** `warning`
- **Triggered:** When a target saving passes its end date without completion

### 7. Target Saving Reminder
- **Type:** `target_saving_reminder`
- **Level:** `info` or `warning`
- **Triggered:** For weekly/monthly reminders or deadline approaching

## Error Responses

### Validation Error
```json
{
  "success": false,
  "message": "Validation error",
  "errors": {
    "target_amount": ["Target amount must be greater than zero"],
    "end_date": ["End date must be after start date"]
  }
}
```

### Not Found Error
```json
{
  "success": false,
  "message": "Target saving not found"
}
```

### Permission Error
```json
{
  "success": false,
  "message": "You do not have permission to access this target saving"
}
```

## Validation Rules

### Target Saving Creation
- **name:** Required, 3-255 characters
- **category:** Required, must be from predefined choices
- **target_amount:** Required, > 0, max 1 billion
- **frequency:** Required, must be daily/weekly/monthly
- **preferred_deposit_day:** Required for weekly/monthly frequency
- **start_date:** Required, cannot be in the past
- **end_date:** Required, must be after start_date, max 10 years

### Deposit Creation
- **amount:** Required, > 0, max 100 million
- **notes:** Optional, max 1000 characters

## Rate Limiting

- **Create Target:** 10 per hour
- **Make Deposit:** 50 per hour
- **Get Analytics:** 100 per hour
- **Export Data:** 10 per hour

## Webhook Events (Optional)

The system can send webhook notifications for the following events:
- `target_saving.created`
- `target_saving.updated`
- `target_saving.completed`
- `target_saving.deposit_made`
- `target_saving.milestone_reached`
- `target_saving.overdue`

## SDK Examples

### JavaScript/TypeScript
```javascript
// Create a new target saving
const response = await fetch('/api/target-saving/targets/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    name: 'Vacation Fund',
    category: 'travel',
    target_amount: 2000000.00,
    frequency: 'weekly',
    preferred_deposit_day: 'monday',
    start_date: '2024-01-01',
    end_date: '2024-12-31'
  })
});

// Make a deposit
const depositResponse = await fetch('/api/target-saving/targets/{id}/make_deposit/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    amount: 50000.00,
    notes: 'Weekly savings'
  })
});
```

### Python
```python
import requests

# Create a new target saving
response = requests.post(
    'https://api.example.com/api/target-saving/targets/',
    headers={'Authorization': f'Bearer {token}'},
    json={
        'name': 'Vacation Fund',
        'category': 'travel',
        'target_amount': 2000000.00,
        'frequency': 'weekly',
        'preferred_deposit_day': 'monday',
        'start_date': '2024-01-01',
        'end_date': '2024-12-31'
    }
)

# Make a deposit
deposit_response = requests.post(
    f'https://api.example.com/api/target-saving/targets/{target_id}/make_deposit/',
    headers={'Authorization': f'Bearer {token}'},
    json={
        'amount': 50000.00,
        'notes': 'Weekly savings'
    }
)
```

## Integration Notes

1. **Notifications:** All target saving events automatically create notifications in the notification system
2. **Milestones:** Progress milestones (25%, 50%, 75%, 90%) are automatically tracked and notified
3. **Overdue Tracking:** The system automatically identifies overdue targets
4. **Analytics:** Real-time analytics are calculated for each target and across all targets
5. **Export:** CSV export functionality is available for deposits and analytics
6. **Validation:** Comprehensive validation ensures data integrity
7. **Security:** All endpoints require authentication and validate user ownership

## Support

For API support and questions:
- Email: api-support@example.com
- Documentation: https://docs.example.com/target-saving-api
- Status: https://status.example.com 