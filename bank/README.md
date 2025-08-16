`# Bank App Documentation

## 1. Signal and Task Logic

### Signals (`signals.py`):
- **Transaction Approval Automation:**
  - When a large `Transaction` is created, an approval request is automatically generated and assigned to a staff member who can approve it.
  - Staff activities are logged for transaction processing and approvals.
- **Transaction Approval Status:**
  - When a `TransactionApproval` status changes (approved, rejected, escalated), the related transaction status is updated and staff activities are logged.
- **Customer Escalation:**
  - When a `CustomerEscalation` is created or resolved, staff activities are logged and resolution timestamps are set.
- **KYC Approval:**
  - When a `KYCProfile` is approved, staff activities are logged for the approval.
- **Staff Profile Changes:**
  - When a `StaffProfile` is created or its role changes, staff activities are logged.
- **Wallet Creation:**
  - When a `KYCProfile` is approved, a `Wallet` is automatically created for the user if one does not exist.
- **Bank Transfer Processing:**
  - When a `BankTransfer` is created with 'completed' status, it automatically deducts from sender's wallet and credits receiver's wallet (for internal transfers).
  - Creates corresponding `Transaction` records for both sender (debit) and receiver (credit).
- **Transaction Notifications:**
  - Sends HTML email notifications for all new `Transaction` records to both sender and receiver.
  - Prevents duplicate emails when sender and receiver are the same user.

### Automated Tasks (`tasks.py`):
- **Weekly Statement Email:**
  - `send_weekly_statements`: For each active user, generates a weekly account statement (PDF generation and email sending logic is present but commented out).

---

## 2. URL List and Explanations (`urls.py`)

### Wallets, Transactions, and Banking
- **`/wallets/`**  
  _ViewSet:_ `WalletViewSet`  
  _Description:_ CRUD operations for user wallets.

- **`/transactions/`**  
  _ViewSet:_ `TransactionViewSet`  
  _Description:_ CRUD operations for transactions (deposits, withdrawals, transfers, etc.).

- **`/bank-transfers/`**  
  _ViewSet:_ `BankTransferViewSet`  
  _Description:_ Initiate and manage bank transfers.
  
  **Additional Endpoints:**
  - **`POST /bank-transfers/validate-account/`** - Validate account number and return bank info + account holder name
  - **`GET /bank-transfers/banks/`** - Get list of all available banks for transfer

- **`/bill-payments/`**  
  _ViewSet:_ `BillPaymentViewSet`  
  _Description:_ Pay bills (e.g., utilities, TV, etc.).

- **`/banks/`**  
  _ViewSet:_ `BankViewSet`  
  _Description:_ List and manage supported banks.

### Staff Management
- **`/staff/roles/`**  
  _ViewSet:_ `StaffRoleViewSet`  
  _Description:_ Manage staff roles and permissions.

- **`/staff/profiles/`**  
  _ViewSet:_ `StaffProfileViewSet`  
  _Description:_ Manage staff profiles.

- **`/staff/activities/`**  
  _ViewSet:_ `StaffActivityViewSet`  
  _Description:_ Track and review staff activities.

### Transaction Approvals & Escalations
- **`/approvals/`**  
  _ViewSet:_ `TransactionApprovalViewSet`  
  _Description:_ Approve, reject, or escalate transactions that require approval.

- **`/escalations/`**  
  _ViewSet:_ `CustomerEscalationViewSet`  
  _Description:_ Manage customer service escalations.

### Utility & Statements
- **`/user-status/`**  
  _View:_ `get_user_status`  
  _Description:_ Get the current status of a user (e.g., active, suspended).

- **`/statement/pdf/`**  
  _View:_ `download_pdf_statement`  
  _Description:_ Download a PDF account statement for the user.

---

## 3. NIBSS Integration (`nibss.py`)

### Simulated NIBSS Client
The `NIBSSClient` class provides simulated NIBSS API functionality for development and testing:

- **`validate_account_number(account_number)`** - Validate account numbers and return bank info + account holder name
- **`send_interbank_transfer(...)`** - Simulate interbank transfers via NIBSS
- **`check_transfer_status(nibss_reference)`** - Check status of NIBSS transfers
- **`pay_bill(...)`** - Simulate NIBSS e-BillsPay bill payments
- **`verify_bvn(bvn)`** - Simulate BVN verification
- **`setup_direct_debit(...)`** - Simulate direct debit mandate setup

### Account Validation Patterns
The system simulates different banks based on account number patterns:
- `00` → Access Bank (John Doe)
- `01` → GT Bank (Jane Smith)
- `02` → First Bank (Michael Johnson)
- `03` → Zenith Bank (Sarah Wilson)
- `04` → UBA (David Brown)
- `05` → Ecobank (Lisa Davis)
- `06` → Union Bank (Robert Miller)
- `07` → Fidelity Bank (Emma Wilson)
- `08` → Sterling Bank (James Taylor)
- `09` → Wema Bank (Mary Anderson)
- **Others** → Random banks with random names

---

## 4. Enhanced Reference Formats

### Professional Reference Generation
All financial transactions now use professional, traceable reference formats:

- **BankTransfer Reference:** `BT-YYYYMMDD-HHMMSS-XXXX-XXXXXX`
  - Example: `BT-20240725-143052-1234-1A2B3C`
  
- **Transaction Reference:** `TX-YYYYMMDD-HHMMSS-XXXX-XXXXXX`
  - Example: `TX-20240725-143052-5678-5F6E7D`
  
- **BillPayment Reference:** `BP-YYYYMMDD-HHMMSS-XXXX-XXXXXX`
  - Example: `BP-20240725-143052-9012-9A8B7C`

### Reference Components:
- **Prefix:** Transaction type identification (`BT`, `TX`, `BP`)
- **Date:** Full date in YYYYMMDD format
- **Time:** Precise timestamp in HHMMSS format
- **Account Suffix:** Last 4 digits of user's account number for traceability
- **Unique ID:** 6-character random string for uniqueness

---

## 5. Account Validation API

### Frontend Integration
The account validation system provides real-time account verification:

**Validate Account Number:**
```javascript
POST /api/bank-transfers/validate-account/
{
    "account_number": "0012345678"
}
```

**Response (Success):**
```json
{
    "account_number": "0012345678",
    "account_name": "John Doe",
    "bank_name": "Access Bank",
    "bank_code": "044",
    "is_internal": false,
    "status": "valid"
}
```

**Response (Internal Account):**
```json
{
    "account_number": "1234567890",
    "account_name": "John Smith",
    "bank_name": "XYPay Bank",
    "bank_code": "880",
    "is_internal": true,
    "status": "valid"
}
```

**Get All Banks:**
```javascript
GET /api/bank-transfers/banks/
```

**Response:**
```json
{
    "banks": [
        {
            "id": 1,
            "name": "Access Bank",
            "code": "044",
            "slug": "access-bank",
            "ussd": "*901#",
            "logo": "https://example.com/access-bank.png"
        }
    ],
    "count": 1
}
```

---

## 6. Enhanced Models

### BankTransfer Model Updates:
- **`transfer_type`** - Distinguishes between 'intra' (internal) and 'inter' (external) transfers
- **`description`** - Optional user-provided transfer description
- **`nibss_reference`** - Stores NIBSS transaction reference for external transfers
- **Auto-generated `reference`** - Professional format with date, time, and account suffix

### Transaction Model Updates:
- **`receiver`** - ForeignKey to Wallet for linking transfer recipients
- **Auto-generated `reference`** - Professional format for all transactions

### BillPayment Model Updates:
- **Auto-generated `reference`** - Professional format for bill payments

---

## 7. Email Notifications

### Transaction Email Templates
- **Template:** `bank/transaction_email.html`
- **Features:** Professional HTML formatting with inline CSS
- **Content:** Transaction details, account information, and status
- **Recipients:** Both sender and receiver (with duplicate prevention)

### Notification Features:
- **HTML Formatting** - Professional email design
- **Conditional Rendering** - Different messages for credit/debit transactions
- **Duplicate Prevention** - Prevents spam when sender and receiver are the same
- **Status Notifications** - Covers successful, failed, and pending transactions

---

## 8. Bank Data Management

### Seeding Banks (`seed_banks.py`):
- **Primary Source:** Nigerian Banks API (`https://nigerianbanks.xyz/`)
- **Fallback Source:** Local JSON file (`seed_banks.json`)
- **Merging Strategy:** Local custom banks override API entries
- **Custom Banks:** Support for custom bank entries (e.g., XYPay Bank)

### Bank Model Features:
- **Complete Bank Information** - Name, code, slug, USSD, logo
- **Custom Bank Support** - Easy addition of new banks
- **API Integration Ready** - Designed for real NIBSS integration

---

## 9. Summary

The app provides comprehensive banking, transaction, staff, and escalation management endpoints with:

- **Real-time Account Validation** - Instant account number verification with bank info
- **Professional Reference Formats** - Traceable, unique transaction references
- **NIBSS Integration Ready** - Simulated API client for easy production transition
- **Enhanced Email Notifications** - Professional HTML transaction notifications
- **Automated Transfer Processing** - Seamless internal and external transfers
- **Comprehensive Staff Management** - Role-based permissions and activity tracking
- **Robust Bank Data Management** - Multi-source bank data with custom support

All critical banking and admin actions are exposed via clear, RESTful URLs with comprehensive documentation and examples.

---

If you need more detailed documentation for any specific view, signal, or model, just check the relevant file or ask for more details! 