"""
Test examples for the new account validation endpoints.
These are not actual tests but examples of how to use the API.
"""

# Example API calls for account validation:

"""
1. Validate Account Number:
POST /api/bank-transfers/validate-account/
Content-Type: application/json

{
    "account_number": "0012345678"
}

Response (Success):
{
    "account_number": "0012345678",
    "account_name": "John Doe",
    "bank_name": "Access Bank",
    "bank_code": "044",
    "is_internal": false,
    "status": "valid"
}

Response (Internal Account):
{
    "account_number": "1234567890",
    "account_name": "John Smith",
    "bank_name": "XYPay Bank",
    "bank_code": "880",
    "is_internal": true,
    "status": "valid"
}

Response (Invalid):
{
    "account_number": "123",
    "error": "Invalid account number format. Must be 10 digits.",
    "status": "invalid"
}

2. Get All Banks:
GET /api/bank-transfers/banks/

Response:
{
    "banks": [
        {
            "id": 1,
            "name": "Access Bank",
            "code": "044",
            "slug": "access-bank",
            "ussd": "*901#",
            "logo": "https://example.com/access-bank.png"
        },
        {
            "id": 2,
            "name": "GT Bank",
            "code": "058",
            "slug": "gt-bank",
            "ussd": "*737#",
            "logo": "https://example.com/gt-bank.png"
        }
    ],
    "count": 2
}

3. Create Bank Transfer (with validated account):
POST /api/bank-transfers/
Content-Type: application/json

{
    "account_number": "0012345678",
    "bank_name": "Access Bank",
    "bank_code": "044",
    "amount": "1000.00",
    "description": "Payment for services"
}

Frontend Integration Example (JavaScript):

// Function to validate account number
async function validateAccount(accountNumber) {
    try {
        const response = await fetch('/api/bank-transfers/validate-account/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + getAuthToken()
            },
            body: JSON.stringify({ account_number: accountNumber })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Account is valid - show account details
            document.getElementById('account-name').textContent = data.account_name;
            document.getElementById('bank-name').textContent = data.bank_name;
            document.getElementById('account-info').style.display = 'block';
            
            // Pre-fill bank details in transfer form
            document.getElementById('bank-name-input').value = data.bank_name;
            document.getElementById('bank-code-input').value = data.bank_code;
        } else {
            // Account is invalid - show error
            document.getElementById('error-message').textContent = data.error;
            document.getElementById('account-info').style.display = 'none';
        }
    } catch (error) {
        console.error('Error validating account:', error);
    }
}

// Function to get all banks
async function loadBanks() {
    try {
        const response = await fetch('/api/bank-transfers/banks/', {
            headers: {
                'Authorization': 'Bearer ' + getAuthToken()
            }
        });
        
        const data = await response.json();
        
        // Populate bank dropdown
        const bankSelect = document.getElementById('bank-select');
        bankSelect.innerHTML = '<option value="">Select Bank</option>';
        
        data.banks.forEach(bank => {
            const option = document.createElement('option');
            option.value = bank.code;
            option.textContent = bank.name;
            bankSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading banks:', error);
    }
}

// Event listener for account number input
document.getElementById('account-number-input').addEventListener('blur', function() {
    const accountNumber = this.value.trim();
    if (accountNumber.length === 10) {
        validateAccount(accountNumber);
    }
});
"""
