# Tier Progression System Guide

## Overview
The fintech banking system now implements a **sequential tier progression system** where users must upgrade through tiers in order: Tier 1 → Tier 2 → Tier 3. Users cannot skip tiers or upgrade directly to higher tiers.

## Tier Progression Rules

### 🔄 **Sequential Progression**
- **Tier 1 → Tier 2**: Users must be on Tier 1 to upgrade to Tier 2
- **Tier 2 → Tier 3**: Users must be on Tier 2 to upgrade to Tier 3
- **No Skipping**: Users cannot jump directly from Tier 1 to Tier 3

### 📋 **Tier 1 → Tier 2 Requirements**
- ✅ **Current Tier**: Must be on Tier 1
- ✅ **KYC Approval**: Must be approved
- ✅ **BVN or NIN**: Must have either BVN or NIN

### 📋 **Tier 2 → Tier 3 Requirements**
- ✅ **Current Tier**: Must be on Tier 2
- ✅ **KYC Approval**: Must be approved
- ✅ **Both BVN and NIN**: Must have both BVN and NIN
- ✅ **Government ID**: Must have government ID document
- ✅ **Proof of Address**: Must have proof of address document

## Implementation Details

### Model Methods

#### `can_upgrade_to_tier_2()`
Checks if user can upgrade to Tier 2:
```python
can_upgrade, message = kyc_profile.can_upgrade_to_tier_2()
```

#### `can_upgrade_to_tier_3()`
Checks if user can upgrade to Tier 3:
```python
can_upgrade, message = kyc_profile.can_upgrade_to_tier_3()
```

#### `get_upgrade_requirements(target_tier)`
Gets detailed requirements for a specific tier:
```python
requirements = kyc_profile.get_upgrade_requirements('tier_2')
```

#### `get_available_upgrades()`
Gets list of available upgrades for the user:
```python
available_upgrades = kyc_profile.get_available_upgrades()
```

### Admin Interface Features

#### Enhanced Tier Upgrade Actions
- **"Upgrade selected to Tier 2 (with validation)"**: Validates requirements before upgrade
- **"Upgrade selected to Tier 3 (with validation)"**: Validates requirements before upgrade
- **"Show tier upgrade requirements"**: Shows requirements for selected profiles
- **"Check upgrade eligibility"**: Checks eligibility for all selected profiles

#### Validation Messages
When upgrade fails, admin shows specific error messages:
- "Cannot upgrade to Tier 2. Current level is Tier 3"
- "KYC must be approved before upgrading to Tier 2"
- "BVN or NIN is required for Tier 2 upgrade"
- "Cannot upgrade to Tier 3. Current level is Tier 1. Must be on Tier 2 first."

## API Endpoints

### 🔍 **Check Tier Requirements**
```bash
GET /api/accounts/tier-upgrade/requirements/
Authorization: Bearer <user_token>

# Response:
{
    "current_tier": {
        "level": "tier_1",
        "display_name": "Tier 1",
        "limits": {
            "daily_transaction_limit": 50000,
            "max_balance_limit": 300000,
            "description": "Basic tier with limited transactions"
        },
        "is_approved": true
    },
    "available_upgrades": [
        {
            "tier": "tier_2",
            "display_name": "Tier 2",
            "requirements": {
                "current_tier": "tier_1",
                "target_tier": "tier_2",
                "requirements": [
                    "Must be on Tier 1",
                    "KYC must be approved",
                    "BVN or NIN required"
                ],
                "current_status": {
                    "is_tier_1": true,
                    "is_approved": true,
                    "has_bvn_or_nin": true
                }
            }
        }
    ],
    "next_tier_requirements": {
        "current_tier": "tier_1",
        "target_tier": "tier_2",
        "requirements": [
            "Must be on Tier 1",
            "KYC must be approved",
            "BVN or NIN required"
        ],
        "current_status": {
            "is_tier_1": true,
            "is_approved": true,
            "has_bvn_or_nin": true
        }
    },
    "upgrade_requested": false,
    "upgrade_request_date": null
}
```

### 📝 **Request Tier Upgrade**
```bash
POST /api/accounts/tier-upgrade/request/
Authorization: Bearer <user_token>
Content-Type: application/json

{
    "target_tier": "tier_2"
}

# Success Response:
{
    "message": "Upgrade request submitted successfully for tier_2",
    "target_tier": "tier_2",
    "request_date": "2024-01-15T10:30:00Z"
}

# Error Response:
{
    "error": "Cannot upgrade to Tier 3. Current level is Tier 1. Must be on Tier 2 first.",
    "requirements": {
        "current_tier": "tier_1",
        "target_tier": "tier_3",
        "requirements": [
            "Must be on Tier 2",
            "KYC must be approved",
            "Both BVN and NIN required",
            "Government ID document required",
            "Proof of address required"
        ],
        "current_status": {
            "is_tier_2": false,
            "is_approved": true,
            "has_bvn": true,
            "has_nin": false,
            "has_govt_id": false,
            "has_proof_of_address": false
        }
    }
}
```

### ✅ **Check Upgrade Eligibility**
```bash
GET /api/accounts/tier-upgrade/eligibility/
Authorization: Bearer <user_token>

# Response:
{
    "current_tier": "tier_1",
    "current_tier_display": "Tier 1",
    "eligibility": {
        "tier_2": {
            "eligible": true,
            "message": "Eligible for Tier 2 upgrade",
            "requirements": {
                "current_tier": "tier_1",
                "target_tier": "tier_2",
                "requirements": [
                    "Must be on Tier 1",
                    "KYC must be approved",
                    "BVN or NIN required"
                ],
                "current_status": {
                    "is_tier_1": true,
                    "is_approved": true,
                    "has_bvn_or_nin": true
                }
            }
        },
        "tier_3": {
            "eligible": false,
            "message": "Cannot upgrade to Tier 3. Current level is Tier 1. Must be on Tier 2 first.",
            "requirements": null
        }
    },
    "available_upgrades": [
        {
            "tier": "tier_2",
            "display_name": "Tier 2",
            "requirements": {
                "current_tier": "tier_1",
                "target_tier": "tier_2",
                "requirements": [
                    "Must be on Tier 1",
                    "KYC must be approved",
                    "BVN or NIN required"
                ],
                "current_status": {
                    "is_tier_1": true,
                    "is_approved": true,
                    "has_bvn_or_nin": true
                }
            }
        }
    ]
}
```

## Admin Usage Examples

### 📊 **Bulk Tier Upgrade with Validation**
1. Go to Django Admin → KYC Profiles
2. Select multiple profiles
3. Choose "Upgrade selected to Tier 2 (with validation)"
4. System will:
   - Upgrade eligible profiles
   - Show error messages for ineligible profiles
   - Display success count

### 📋 **Check Requirements**
1. Select KYC profiles
2. Choose "Show tier upgrade requirements"
3. View detailed requirements for each profile

### ✅ **Check Eligibility**
1. Select KYC profiles
2. Choose "Check upgrade eligibility"
3. Get summary of eligible vs ineligible profiles

## User Experience Flow

### 🔄 **Tier 1 User Journey**
1. **Complete KYC**: User completes basic KYC (Tier 1)
2. **Check Requirements**: User checks Tier 2 requirements
3. **Provide Documents**: User adds BVN/NIN if missing
4. **Request Upgrade**: User requests Tier 2 upgrade
5. **Admin Approval**: Admin approves upgrade
6. **Tier 2 Active**: User now has Tier 2 limits

### 🔄 **Tier 2 User Journey**
1. **Check Requirements**: User checks Tier 3 requirements
2. **Provide Documents**: User adds missing documents (both BVN/NIN, govt ID, proof of address)
3. **Request Upgrade**: User requests Tier 3 upgrade
4. **Admin Approval**: Admin approves upgrade
5. **Tier 3 Active**: User now has Tier 3 limits

## Error Handling

### ❌ **Common Error Scenarios**
- **Wrong Current Tier**: "Cannot upgrade to Tier 2. Current level is Tier 3"
- **Not Approved**: "KYC must be approved before upgrading to Tier 2"
- **Missing Documents**: "BVN or NIN is required for Tier 2 upgrade"
- **Skipping Tiers**: "Cannot upgrade to Tier 3. Current level is Tier 1. Must be on Tier 2 first."

### ✅ **Success Scenarios**
- **Valid Tier 1 → Tier 2**: "Successfully upgraded to Tier 2"
- **Valid Tier 2 → Tier 3**: "Successfully upgraded to Tier 3"

## Benefits

### 🛡️ **Security & Compliance**
- Enforces regulatory tier progression
- Prevents unauthorized tier skipping
- Maintains audit trail of upgrades

### 👥 **User Experience**
- Clear requirements for each tier
- Progressive enhancement of limits
- Transparent upgrade process

### 🔧 **Admin Control**
- Validation prevents invalid upgrades
- Detailed error messages for troubleshooting
- Bulk operations with validation

## Future Enhancements

### 🚀 **Potential Additions**
- **Automatic Eligibility Checks**: Periodic checks for eligible users
- **Notification System**: Notify users when they become eligible
- **Tier Downgrade Protection**: Prevent downgrades for users with high balances
- **Tier Expiry**: Automatic tier downgrade after inactivity
- **Tier Benefits Display**: Show benefits of each tier level

### 📊 **Analytics**
- **Upgrade Success Rates**: Track successful vs failed upgrades
- **Requirement Analysis**: Most common missing requirements
- **User Journey Mapping**: Track user progression through tiers 