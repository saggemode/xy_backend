import random
import time
import logging

logger = logging.getLogger(__name__)

class NIBSSClient:
    """Simulated NIBSS API client for development and testing."""
    
    def __init__(self):
        self.base_url = "https://api.nibss.com"  # Simulated base URL
        self.api_key = "simulated_api_key"
    
    def validate_account_number(self, account_number):
        """
        Simulate account number validation.
        In production, this would call NIBSS API to validate account details.
        """
        time.sleep(0.5)  # Simulate API delay
        
        # Simulate some validation logic
        if not account_number or len(account_number) != 10:
            return {
                'valid': False,
                'error': 'Invalid account number format'
            }
        
        # Simulate different banks based on account number patterns
        # In real implementation, this would be determined by the bank code
        bank_data = self._get_simulated_bank_data(account_number)
        
        if bank_data:
            return {
                'valid': True,
                'account_name': bank_data['account_name'],
                'bank_name': bank_data['bank_name'],
                'bank_code': bank_data['bank_code'],
                'account_number': account_number
            }
        else:
            return {
                'valid': False,
                'error': 'Account not found or invalid'
            }
    
    def _get_simulated_bank_data(self, account_number):
        """
        Simulate bank data based on account number patterns.
        In production, this would be replaced with real NIBSS API calls.
        """
        # Simulate different banks based on account number
        # This is just for demonstration - real implementation would use actual bank codes
        
        # Access Bank pattern (simulated)
        if account_number.startswith('00'):
            return {
                'account_name': 'John Doe',
                'bank_name': 'Access Bank',
                'bank_code': '044'
            }
        # GT Bank pattern (simulated)
        elif account_number.startswith('01'):
            return {
                'account_name': 'Jane Smith',
                'bank_name': 'GT Bank',
                'bank_code': '058'
            }
        # First Bank pattern (simulated)
        elif account_number.startswith('02'):
            return {
                'account_name': 'Michael Johnson',
                'bank_name': 'First Bank',
                'bank_code': '011'
            }
        # Zenith Bank pattern (simulated)
        elif account_number.startswith('03'):
            return {
                'account_name': 'Sarah Wilson',
                'bank_name': 'Zenith Bank',
                'bank_code': '057'
            }
        # UBA pattern (simulated)
        elif account_number.startswith('04'):
            return {
                'account_name': 'David Brown',
                'bank_name': 'UBA',
                'bank_code': '033'
            }
        # Ecobank pattern (simulated)
        elif account_number.startswith('05'):
            return {
                'account_name': 'Lisa Davis',
                'bank_name': 'Ecobank',
                'bank_code': '050'
            }
        # Union Bank pattern (simulated)
        elif account_number.startswith('06'):
            return {
                'account_name': 'Robert Miller',
                'bank_name': 'Union Bank',
                'bank_code': '032'
            }
        # Fidelity Bank pattern (simulated)
        elif account_number.startswith('07'):
            return {
                'account_name': 'Emma Wilson',
                'bank_name': 'Fidelity Bank',
                'bank_code': '070'
            }
        # Sterling Bank pattern (simulated)
        elif account_number.startswith('08'):
            return {
                'account_name': 'James Taylor',
                'bank_name': 'Sterling Bank',
                'bank_code': '232'
            }
        # Wema Bank pattern (simulated)
        elif account_number.startswith('09'):
            return {
                'account_name': 'Mary Anderson',
                'bank_name': 'Wema Bank',
                'bank_code': '035'
            }
        else:
            # Random bank for other patterns
            banks = [
                {'name': 'Polaris Bank', 'code': '076'},
                {'name': 'Keystone Bank', 'code': '082'},
                {'name': 'Stanbic IBTC', 'code': '221'},
                {'name': 'FCMB', 'code': '214'},
                {'name': 'Heritage Bank', 'code': '030'},
            ]
            bank = random.choice(banks)
            names = ['Alex Johnson', 'Taylor Swift', 'Chris Martin', 'Emma Stone', 'Ryan Reynolds']
            
            return {
                'account_name': random.choice(names),
                'bank_name': bank['name'],
                'bank_code': bank['code']
            }

    def send_interbank_transfer(self, sender_account, recipient_bank_code, recipient_account, amount, narration):
        """
        Simulate sending an interbank transfer via NIBSS.
        Returns a dict with status and transaction reference.
        """
        time.sleep(1)
        if random.random() < 0.95:
            return {
                "status": "success",
                "nibss_reference": f"NIBSS-{random.randint(100000, 999999)}",
                "message": "Transfer successful"
            }
        else:
            return {
                "status": "failed",
                "nibss_reference": None,
                "message": "NIBSS transfer failed"
            }

    def check_transfer_status(self, nibss_reference):
        """
        Simulate checking the status of a NIBSS transfer.
        """
        return {
            "status": "success",
            "nibss_reference": nibss_reference,
            "message": "Transfer completed"
        }

    def pay_bill(self, customer_account, biller_code, amount, bill_reference, narration):
        """
        Simulate a NIBSS e-BillsPay bill payment.
        """
        time.sleep(1)
        if random.random() < 0.97:
            return {
                "status": "success",
                "bill_reference": bill_reference or f"BILL-{random.randint(100000, 999999)}",
                "message": "Bill payment successful"
            }
        else:
            return {
                "status": "failed",
                "bill_reference": bill_reference or None,
                "message": "Bill payment failed"
            }

    def verify_bvn(self, bvn):
        """
        Simulate BVN verification via NIBSS.
        """
        time.sleep(0.5)
        if len(str(bvn)) == 11 and str(bvn).isdigit():
            return {
                "status": "success",
                "bvn": bvn,
                "message": "BVN is valid",
                "customer_name": f"Simulated User {bvn[-4:]}"
            }
        else:
            return {
                "status": "failed",
                "bvn": bvn,
                "message": "Invalid BVN"
            }

    def setup_direct_debit(self, customer_account, amount, mandate_reference):
        """
        Simulate setting up a NIBSS direct debit mandate.
        """
        time.sleep(1)
        if random.random() < 0.98:
            return {
                "status": "success",
                "mandate_reference": mandate_reference or f"MANDATE-{random.randint(100000, 999999)}",
                "message": "Direct debit mandate setup successful"
            }
        else:
            return {
                "status": "failed",
                "mandate_reference": mandate_reference or None,
                "message": "Direct debit mandate setup failed"
            } 