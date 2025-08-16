# KYC Levels Implementation Guide

## Overview
The fintech banking system now supports three KYC (Know Your Customer) levels with different transaction and balance limits. This ensures compliance with financial regulations while providing users with appropriate access based on their verification level.

## KYC Levels

### Tier 1 (Default Level)
- **Daily Transaction Limit**: ₦50,000
- **Maximum Account Balance**: ₦300,000
- **Requirements**: Basic KYC verification (BVN or NIN)
- **Use Case**: New users, basic transactions

### Tier 2 (Enhanced Level)
- **Daily Transaction Limit**: ₦200,000
- **Maximum Account Balance**: ₦500,000
- **Requirements**: Enhanced KYC verification
- **Use Case**: Regular users, moderate transactions

### Tier 3 (Premium Level)
- **Daily Transaction Limit**: ₦5,000,000
- **Maximum Account Balance**: Unlimited
- **Requirements**: Full KYC verification
- **Use Case**: High-value users, business accounts

## Implementation Details

### Database Changes
- Added `kyc_level` field to `KYCProfile` model
- Default value: `tier_1`
- Choices: `tier_1`, `tier_2`, `tier_3`

### Model Methods
The `KYCProfile` model includes several methods for limit management:

#### `get_daily_transaction_limit()`
Returns the daily transaction limit for the current KYC level.

#### `get_max_balance_limit()`
Returns the maximum account balance limit for the current KYC level.

#### `can_transact_amount(amount)`
Validates if a user can perform a transaction of the specified amount.
- Checks daily transaction limits
- Returns `(bool, message)` tuple

#### `can_have_balance(new_balance)`
Validates if a user can have the specified balance.
- Checks maximum balance limits
- Returns `(bool, message)` tuple

### Automatic Validation

#### Transaction Validation
All bank transfers and bill payments are automatically validated against:
- User's daily transaction limit
- Current day's transaction total
- KYC approval status

#### Balance Validation
Wallet balance changes are validated against:
- User's maximum balance limit
- KYC approval status

### API Endpoints

#### For Users
- `GET /api/bank/kyc-profiles/my_limits/` - Get current limits
- `GET /api/bank/kyc-profiles/{id}/` - Get KYC profile with limits

#### For Admins
- `POST /api/bank/kyc-profiles/{id}/upgrade_kyc_level/` - Upgrade KYC level
- `POST /api/bank/kyc-profiles/{id}/approve/` - Approve KYC
- `POST /api/bank/kyc-profiles/{id}/reject/` - Reject KYC

### Admin Interface Features

#### KYC Profile Management
- **List Display**: Shows KYC level, limits, and status
- **Filters**: Filter by KYC level, approval status
- **Actions**: Bulk upgrade to Tier 2/3
- **Read-only Fields**: Daily transaction limit, max balance limit

#### Bulk Operations
- **Bulk Approve**: Approve multiple KYC profiles
- **Bulk Reject**: Reject multiple KYC profiles
- **Bulk Upgrade Tier 2**: Upgrade approved Tier 1 profiles to Tier 2
- **Bulk Upgrade Tier 3**: Upgrade approved profiles to Tier 3

### Validation Rules

#### KYC Level Upgrades
- Can only upgrade approved KYC profiles
- Cannot downgrade if user has balance exceeding new limits
- Tier 1 → Tier 2: Balance must be ≤ ₦500,000
- Tier 1/2 → Tier 3: No balance restrictions

#### Transaction Limits
- Daily limits reset at midnight
- Only successful transactions count toward daily limit
- Failed transactions don't affect daily limit

#### Balance Limits
- Real-time validation on wallet save
- Prevents balance exceeding KYC level limits
- Graceful handling for users without KYC profiles

## Usage Examples

### Creating KYC Profile
```python
# User creates KYC profile (defaults to Tier 1)
kyc_profile = KYCProfile.objects.create(
    user=user,
    bvn="12345678901",
    date_of_birth="1990-01-01",
    address="123 Main St"
)
```

### Checking Transaction Limits
```python
# Check if user can transact ₦25,000
can_transact, message = kyc_profile.can_transact_amount(25000)
if can_transact:
    # Proceed with transaction
    pass
else:
    # Handle limit exceeded
    print(message)
```

### Upgrading KYC Level
```python
# Admin upgrades user to Tier 2
kyc_profile.kyc_level = 'tier_2'
kyc_profile.save()
```

### API Usage
```bash
# Get user's KYC limits
curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/api/bank/kyc-profiles/my_limits/

# Admin upgrades KYC level
curl -X POST \
     -H "Authorization: Bearer <admin_token>" \
     -H "Content-Type: application/json" \
     -d '{"kyc_level": "tier_2"}' \
     http://localhost:8000/api/bank/kyc-profiles/{id}/upgrade_kyc_level/
```

## Security Features

### Audit Logging
All KYC level changes are logged with:
- User performing the action
- Old and new KYC levels
- Timestamp and IP address
- Action description

### Validation Checks
- Prevents downgrading users with high balances
- Validates all transactions against limits
- Ensures KYC approval before transactions

### Admin Permissions
- Only staff users can upgrade KYC levels
- Only staff users can approve/reject KYC profiles
- Regular users can only view their own limits

## Compliance Benefits

### Regulatory Compliance
- Implements tiered KYC levels as required by financial regulators
- Provides clear transaction and balance limits
- Maintains audit trail for all KYC operations

### Risk Management
- Limits exposure based on verification level
- Prevents high-value transactions without proper verification
- Automatic validation reduces manual oversight

### User Experience
- Clear limits displayed to users
- Automatic validation prevents failed transactions
- Gradual upgrade path as users provide more verification

## Future Enhancements

### Potential Additions
- **Tier 4**: For institutional clients
- **Dynamic Limits**: Based on user behavior and risk assessment
- **Temporary Limits**: For special promotions or events
- **Geographic Limits**: Different limits by region
- **Time-based Limits**: Different limits by time of day

### Integration Opportunities
- **Risk Scoring**: Integrate with external risk assessment services
- **Document Verification**: Automated document verification for higher tiers
- **Biometric Verification**: Add biometric verification for Tier 3
- **AML Integration**: Anti-money laundering checks for higher tiers 