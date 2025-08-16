"""
Constants for the bank application.
"""

# Bank Transfer Statuses
class TransferStatus:
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    REVERSED = 'reversed'
    APPROVAL_REQUIRED = 'approval_required'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    
    CHOICES = [
        (PENDING, 'Pending'),
        (PROCESSING, 'Processing'),
        (COMPLETED, 'Completed'),
        (FAILED, 'Failed'),
        (CANCELLED, 'Cancelled'),
        (REVERSED, 'Reversed'),
        (APPROVAL_REQUIRED, 'Approval Required'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
    ]

# Transfer Types
class TransferType:
    INTERNAL = 'intra'
    EXTERNAL = 'inter'
    BULK = 'bulk'
    SCHEDULED = 'scheduled'
    RECURRING = 'recurring'
    
    CHOICES = [
        (INTERNAL, 'Internal Transfer'),
        (EXTERNAL, 'External Transfer'),
        (BULK, 'Bulk Transfer'),
        (SCHEDULED, 'Scheduled Transfer'),
        (RECURRING, 'Recurring Transfer'),
    ]

# Transaction Types
class TransactionType:
    CREDIT = 'credit'
    DEBIT = 'debit'
    FEE = 'fee'
    VAT = 'vat'
    LEVY = 'levy'
    REVERSAL = 'reversal'
    
    CHOICES = [
        (CREDIT, 'Credit'),
        (DEBIT, 'Debit'),
        (FEE, 'Fee'),
        (VAT, 'VAT'),
        (LEVY, 'Levy'),
        (REVERSAL, 'Reversal'),
    ]

# Error Codes for Banking Operations
class ErrorCodes:
    # Transaction Errors
    INSUFFICIENT_FUNDS = 'ERR_INSUFFICIENT_FUNDS'
    INVALID_ACCOUNT = 'ERR_INVALID_ACCOUNT'
    ACCOUNT_BLOCKED = 'ERR_ACCOUNT_BLOCKED'
    DAILY_LIMIT_EXCEEDED = 'ERR_DAILY_LIMIT_EXCEEDED'
    TRANSACTION_FAILED = 'ERR_TRANSACTION_FAILED'
    
    # Authentication/Authorization Errors
    INVALID_PIN = 'ERR_INVALID_PIN'
    EXPIRED_TOKEN = 'ERR_EXPIRED_TOKEN'
    UNAUTHORIZED = 'ERR_UNAUTHORIZED'
    
    # Network/System Errors
    NETWORK_ERROR = 'ERR_NETWORK'
    TIMEOUT = 'ERR_TIMEOUT'
    SYSTEM_ERROR = 'ERR_SYSTEM'
    
    # Bank-specific Errors
    BANK_NOT_AVAILABLE = 'ERR_BANK_UNAVAILABLE'
    INVALID_BANK_CODE = 'ERR_INVALID_BANK'
    
    CHOICES = [
        (INSUFFICIENT_FUNDS, 'Insufficient Funds'),
        (INVALID_ACCOUNT, 'Invalid Account'),
        (ACCOUNT_BLOCKED, 'Account Blocked'),
        (DAILY_LIMIT_EXCEEDED, 'Daily Limit Exceeded'),
        (TRANSACTION_FAILED, 'Transaction Failed'),
        (INVALID_PIN, 'Invalid PIN'),
        (EXPIRED_TOKEN, 'Expired Token'),
        (UNAUTHORIZED, 'Unauthorized'),
        (NETWORK_ERROR, 'Network Error'),
        (TIMEOUT, 'Request Timeout'),
        (SYSTEM_ERROR, 'System Error'),
        (BANK_NOT_AVAILABLE, 'Bank Not Available'),
        (INVALID_BANK_CODE, 'Invalid Bank Code'),
    ]

# Security Levels
class SecurityLevel:
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'
    
    CHOICES = [
        (LOW, 'Low'),
        (MEDIUM, 'Medium'),
        (HIGH, 'High'),
        (CRITICAL, 'Critical'),
    ]

# Fraud Detection Flags
class FraudFlag:
    NORMAL = 'normal'
    SUSPICIOUS = 'suspicious'
    HIGH_RISK = 'high_risk'
    BLOCKED = 'blocked'
    
    CHOICES = [
        (NORMAL, 'Normal'),
        (SUSPICIOUS, 'Suspicious'),
        (HIGH_RISK, 'High Risk'),
        (BLOCKED, 'Blocked'),
    ]

# Transfer Limits (in NGN)
class TransferLimits:
    # Default limits
    DEFAULT_DAILY_LIMIT = 1000000  # 1M NGN
    DEFAULT_WEEKLY_LIMIT = 5000000  # 5M NGN
    DEFAULT_MONTHLY_LIMIT = 20000000  # 20M NGN
    
    # High-value transfer thresholds
    HIGH_VALUE_THRESHOLD = 500000  # 500K NGN - requires 2FA
    STAFF_APPROVAL_THRESHOLD = 1000000  # 1M NGN - requires staff approval
    
    # Velocity limits
    MAX_TRANSFERS_PER_HOUR = 10
    MAX_TRANSFERS_PER_DAY = 50
    MAX_AMOUNT_PER_HOUR = 500000  # 500K NGN
    MAX_AMOUNT_PER_DAY = 2000000  # 2M NGN

# Fee Structure (in NGN)
class FeeStructure:
    # Internal transfer fees
    INTERNAL_FEE_PERCENT = 0.0  # 0%
    INTERNAL_FEE_FIXED = 0.0  # 0 NGN
    
    # External transfer fees
    EXTERNAL_FEE_PERCENT = 0.5  # 0.5%
    EXTERNAL_FEE_FIXED = 50.0  # 50 NGN
    
    # VAT rate
    VAT_RATE = 7.5  # 7.5%
    
    # Levy rate
    LEVY_RATE = 0.5  # 0.5%

# Retry Configuration
class RetryConfig:
    MAX_RETRIES = 3
    INITIAL_DELAY = 1  # seconds
    MAX_DELAY = 60  # seconds
    BACKOFF_MULTIPLIER = 2

# Circuit Breaker Configuration
class CircuitBreakerConfig:
    FAILURE_THRESHOLD = 5
    RECOVERY_TIMEOUT = 60  # seconds
    EXPECTED_EXCEPTION = Exception

# API Response Codes
class ResponseCodes:
    SUCCESS = 'SUCCESS'
    INSUFFICIENT_BALANCE = 'INSUFFICIENT_BALANCE'
    INVALID_ACCOUNT = 'INVALID_ACCOUNT'
    TRANSACTION_LIMIT_EXCEEDED = 'TRANSACTION_LIMIT_EXCEEDED'
    FRAUD_DETECTED = 'FRAUD_DETECTED'
    APPROVAL_REQUIRED = 'APPROVAL_REQUIRED'
    TWO_FA_REQUIRED = 'TWO_FA_REQUIRED'
    EXTERNAL_SERVICE_UNAVAILABLE = 'EXTERNAL_SERVICE_UNAVAILABLE'
    IDEMPOTENCY_KEY_REQUIRED = 'IDEMPOTENCY_KEY_REQUIRED'
    DUPLICATE_TRANSACTION = 'DUPLICATE_TRANSACTION'

# Notification Types
class NotificationType:
    TRANSFER_SUCCESS = 'transfer_success'
    TRANSFER_FAILED = 'transfer_failed'
    TRANSFER_PENDING = 'transfer_pending'
    APPROVAL_REQUIRED = 'approval_required'
    APPROVAL_GRANTED = 'approval_granted'
    APPROVAL_DENIED = 'approval_denied'
    TWO_FA_REQUIRED = 'two_fa_required'
    FRAUD_ALERT = 'fraud_alert'
    LIMIT_WARNING = 'limit_warning'
    SECURITY_ALERT = 'security_alert'

# Audit Event Types
class AuditEventType:
    TRANSFER_CREATED = 'transfer_created'
    TRANSFER_COMPLETED = 'transfer_completed'
    TRANSFER_FAILED = 'transfer_failed'
    TRANSFER_REVERSED = 'transfer_reversed'
    APPROVAL_REQUESTED = 'approval_requested'
    APPROVAL_GRANTED = 'approval_granted'
    APPROVAL_DENIED = 'approval_denied'
    TWO_FA_TRIGGERED = 'two_fa_triggered'
    FRAUD_DETECTED = 'fraud_detected'
    LIMIT_EXCEEDED = 'limit_exceeded'
    SECURITY_VIOLATION = 'security_violation'

# Device Fingerprinting
class DeviceFingerprint:
    BROWSER = 'browser'
    MOBILE_APP = 'mobile_app'
    API = 'api'
    WEBHOOK = 'webhook'
    
    CHOICES = [
        (BROWSER, 'Browser'),
        (MOBILE_APP, 'Mobile App'),
        (API, 'API'),
        (WEBHOOK, 'Webhook'),
    ]

# IP Whitelist Status
class IPWhitelistStatus:
    ALLOWED = 'allowed'
    BLOCKED = 'blocked'
    PENDING = 'pending'
    
    CHOICES = [
        (ALLOWED, 'Allowed'),
        (BLOCKED, 'Blocked'),
        (PENDING, 'Pending'),
    ]

# Scheduled Transfer Frequencies
class ScheduledFrequency:
    ONCE = 'once'
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'
    YEARLY = 'yearly'
    
    CHOICES = [
        (ONCE, 'Once'),
        (DAILY, 'Daily'),
        (WEEKLY, 'Weekly'),
        (MONTHLY, 'Monthly'),
        (YEARLY, 'Yearly'),
    ]

# Bulk Transfer Status
class BulkTransferStatus:
    PENDING = 'pending'
    PROCESSING = 'processing'
    PARTIAL_COMPLETED = 'partial_completed'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    
    CHOICES = [
        (PENDING, 'Pending'),
        (PROCESSING, 'Processing'),
        (PARTIAL_COMPLETED, 'Partially Completed'),
        (COMPLETED, 'Completed'),
        (FAILED, 'Failed'),
        (CANCELLED, 'Cancelled'),
    ]

# Escrow Status
class EscrowStatus:
    PENDING = 'pending'
    FUNDED = 'funded'
    RELEASED = 'released'
    REFUNDED = 'refunded'
    EXPIRED = 'expired'
    
    CHOICES = [
        (PENDING, 'Pending'),
        (FUNDED, 'Funded'),
        (RELEASED, 'Released'),
        (REFUNDED, 'Refunded'),
        (EXPIRED, 'Expired'),
    ] 