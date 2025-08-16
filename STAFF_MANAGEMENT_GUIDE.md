# Staff Management System Guide

## Overview

The Staff Management System implements a hierarchical banking hall staff structure with role-based permissions, transaction approvals, customer escalations, and performance tracking.

## Staff Hierarchy

### 1. Teller (Level 1)
- **Max Approval Limit**: ₦50,000
- **Duties**: Basic transactions (deposits, withdrawals, check cashing)
- **Permissions**: None
- **First point of contact for customers**

### 2. Customer Service Representative (Level 2)
- **Max Approval Limit**: ₦100,000
- **Duties**: Customer inquiries, account maintenance, problem resolution
- **Permissions**: View reports, handle escalations

### 3. Personal Banker (Level 3)
- **Max Approval Limit**: ₦500,000
- **Duties**: Client relationships, financial advice, account management
- **Permissions**: KYC approval, view reports, override transactions, handle escalations

### 4. Assistant Manager (Level 4)
- **Max Approval Limit**: ₦1,000,000
- **Duties**: Support branch manager, oversee operations, handle escalations
- **Permissions**: KYC approval, staff management, view reports, override transactions, handle escalations

### 5. Manager (Level 5)
- **Max Approval Limit**: ₦5,000,000
- **Duties**: Department/function performance, operations oversight
- **Permissions**: KYC approval, staff management, view reports, override transactions, handle escalations

### 6. Branch Manager (Level 6)
- **Max Approval Limit**: ₦10,000,000
- **Duties**: Overall branch success, sales, customer satisfaction, staff management
- **Permissions**: All permissions

## Setup Instructions

### 1. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 2. Set Up Staff Roles
```bash
python manage.py setup_staff_roles
```

### 3. Create Sample Staff Members
```bash
# Create a teller
python manage.py create_sample_staff --role teller --username teller1

# Create a customer service rep
python manage.py create_sample_staff --role customer_service --username csr1

# Create a personal banker
python manage.py create_sample_staff --role personal_banker --username banker1

# Create an assistant manager
python manage.py create_sample_staff --role assistant_manager --username asst_mgr1

# Create a manager
python manage.py create_sample_staff --role manager --username manager1

# Create a branch manager
python manage.py create_sample_staff --role branch_manager --username branch_mgr1
```

## Admin Interface

### Access Staff Dashboard
- URL: `/admin/staff-dashboard/`
- Features:
  - Staff statistics and distribution
  - Recent activities
  - Pending approvals
  - Open escalations
  - Staff performance metrics
  - Role-based data access

### Admin Models
- **StaffRole**: Define roles with permissions and approval limits
- **StaffProfile**: Staff member profiles with role assignments
- **TransactionApproval**: Track transaction approval workflow
- **CustomerEscalation**: Manage customer service escalations
- **StaffActivity**: Log staff activities and performance

## API Endpoints

### Staff Roles
```
GET /api/bank/staff/roles/ - List all staff roles
GET /api/bank/staff/roles/{id}/ - Get specific role details
```

### Staff Profiles
```
GET /api/bank/staff/profiles/ - List staff profiles (filtered by permissions)
POST /api/bank/staff/profiles/ - Create staff profile (admin only)
GET /api/bank/staff/profiles/{id}/ - Get specific staff profile
PUT /api/bank/staff/profiles/{id}/ - Update staff profile
DELETE /api/bank/staff/profiles/{id}/ - Delete staff profile

# Custom endpoints
GET /api/bank/staff/profiles/my_profile/ - Get current user's profile
GET /api/bank/staff/profiles/my_subordinates/ - Get subordinates (managers only)
```

### Transaction Approvals
```
GET /api/bank/approvals/ - List approvals (filtered by permissions)
POST /api/bank/approvals/ - Create approval request
GET /api/bank/approvals/{id}/ - Get specific approval
PUT /api/bank/approvals/{id}/ - Update approval

# Custom endpoints
POST /api/bank/approvals/{id}/approve/ - Approve transaction
POST /api/bank/approvals/{id}/reject/ - Reject transaction
POST /api/bank/approvals/{id}/escalate/ - Escalate transaction
```

### Customer Escalations
```
GET /api/bank/escalations/ - List escalations (filtered by permissions)
POST /api/bank/escalations/ - Create escalation
GET /api/bank/escalations/{id}/ - Get specific escalation
PUT /api/bank/escalations/{id}/ - Update escalation

# Custom endpoints
POST /api/bank/escalations/{id}/assign_to_self/ - Assign to current user
POST /api/bank/escalations/{id}/resolve/ - Resolve escalation
```

### Staff Activities
```
GET /api/bank/staff/activities/ - List activities (filtered by permissions)
GET /api/bank/staff/activities/{id}/ - Get specific activity

# Custom endpoints
GET /api/bank/staff/activities/my_activities/ - Get current user's activities
```

## Workflow Examples

### Transaction Approval Workflow
1. **Large Transaction Created**: System automatically creates approval request
2. **Approval Request**: Assigned to appropriate staff member based on amount
3. **Review Process**: Staff reviews transaction details
4. **Decision**: Approve, reject, or escalate to higher authority
5. **Action**: Transaction status updated based on decision
6. **Logging**: Activity logged for performance tracking

### Customer Escalation Workflow
1. **Escalation Created**: Staff creates escalation for customer issue
2. **Assignment**: Escalation assigned to appropriate staff member
3. **Investigation**: Staff investigates and works on resolution
4. **Resolution**: Issue resolved and documented
5. **Closure**: Escalation marked as resolved/closed
6. **Logging**: Activity logged for performance tracking

## Permission System

### Role-Based Access Control
- **Tellers**: Basic transaction processing only
- **Customer Service**: Customer support + basic reports
- **Personal Bankers**: KYC approval + financial advice + transaction override
- **Assistant Managers**: Staff management + higher approval limits
- **Managers**: Full department oversight + high-value approvals
- **Branch Managers**: Complete branch management + highest approval limits

### Data Access Rules
- Staff can only see their own profile and activities
- Managers can see subordinates' profiles and activities
- Branch managers can see all staff data
- Transaction approvals visible to requesters and approvers
- Escalations visible to creators, assignees, and escalation handlers

## Performance Tracking

### Activity Types
- `transaction_processed`: Transaction approvals/rejections
- `kyc_approved`: KYC verification approvals
- `escalation_handled`: Customer escalation resolution
- `customer_served`: Customer service interactions
- `report_generated`: Report generation activities
- `staff_managed`: Staff management activities

### Metrics
- Activities per day/week/month
- Approval success rate
- Escalation resolution time
- Customer satisfaction scores
- Staff productivity indicators

## Security Features

### Audit Trail
- All staff activities logged with timestamps
- Transaction approval history maintained
- Escalation resolution tracking
- Role changes and permission updates logged

### Access Control
- Role-based API access
- Admin interface permission filtering
- Data visibility based on hierarchy
- Secure authentication required

## Integration Points

### With Existing Systems
- **KYC System**: Staff can approve KYC verifications
- **Transaction System**: Automatic approval requests for large transactions
- **Customer Service**: Escalation management integration
- **Reporting System**: Role-based report access

### External Integrations
- **HR System**: Staff profile synchronization
- **Time Tracking**: Activity logging integration
- **Performance Management**: Metrics export capabilities

## Troubleshooting

### Common Issues
1. **Permission Denied**: Check user's role and permissions
2. **Approval Limit Exceeded**: Verify transaction amount vs. role limits
3. **Staff Profile Missing**: Create staff profile for user
4. **Role Not Found**: Run setup_staff_roles command

### Debug Commands
```bash
# Check staff roles
python manage.py shell -c "from bank.models import StaffRole; print(StaffRole.objects.all())"

# Check staff profiles
python manage.py shell -c "from bank.models import StaffProfile; print(StaffProfile.objects.all())"

# Check pending approvals
python manage.py shell -c "from bank.models import TransactionApproval; print(TransactionApproval.objects.filter(status='pending'))"
```

## Best Practices

### Staff Management
- Regularly review and update role permissions
- Monitor staff performance metrics
- Maintain clear escalation paths
- Document approval workflows

### Security
- Regularly audit staff activities
- Review and update access permissions
- Monitor for unusual activity patterns
- Maintain secure authentication

### Performance
- Set realistic approval limits
- Establish clear escalation criteria
- Monitor resolution times
- Provide staff training on workflows

## Support

For technical support or questions about the Staff Management System:
- Check the admin dashboard for system status
- Review activity logs for troubleshooting
- Contact system administrators for role/permission changes
- Refer to API documentation for integration questions 