"""
Example service demonstrating usage of bank utility functions.
"""
import logging
from decimal import Decimal
from django.utils import timezone
from .models import ExampleBankModel
from .utils import generate_reference, safe_money_calculation, handle_service_error, validate_account_balance
from djmoney.money import Money

logger = logging.getLogger(__name__)


class ExampleBankService:
    """
    Example service demonstrating usage of utility functions.
    """
    
    @staticmethod
    def create_example_model(name: str, description: str = "") -> dict:
        """
        Create an example bank model instance using standardized patterns.
        
        Args:
            name: Name of the example model
            description: Description of the example model
            
        Returns:
            Dict with creation result
        """
        try:
            # Use the base model's helper method
            example_model, created = ExampleBankModel.get_or_create_with_defaults(
                defaults={'description': description, 'is_active': True},
                name=name
            )
            
            return {
                'success': True,
                'model': example_model,
                'created': created,
                'message': f"Example model {'created' if created else 'retrieved'} successfully"
            }
        except Exception as e:
            return handle_service_error("create_example_model", e, {
                'success': False,
                'model': None,
                'created': False,
                'message': f"Failed to create example model: {str(e)}"
            })
    
    @staticmethod
    def process_example_transaction(amount, percentage_rate) -> dict:
        """
        Process an example transaction using utility functions.
        
        Args:
            amount: Transaction amount (Money or Decimal)
            percentage_rate: Percentage rate to apply (Decimal or float)
            
        Returns:
            Dict with calculation result
        """
        try:
            # Generate a reference for the transaction
            reference = generate_reference("EX", "5678")
            
            # Safely calculate the percentage amount
            calculated_amount = safe_money_calculation(amount, percentage_rate)
            
            # Create a Money object for the result
            result_amount = Money(calculated_amount, 'NGN')
            
            return {
                'success': True,
                'reference': reference,
                'calculated_amount': str(result_amount),
                'timestamp': timezone.now()
            }
        except Exception as e:
            return handle_service_error("process_example_transaction", e, {
                'success': False,
                'reference': None,
                'calculated_amount': None,
                'timestamp': None,
                'message': f"Failed to process transaction: {str(e)}"
            })
    
    @staticmethod
    def check_balance_sufficiency(current_balance, required_amount) -> dict:
        """
        Check if an account has sufficient balance using utility function.
        
        Args:
            current_balance: Current account balance (Money object)
            required_amount: Required amount (Money object)
            
        Returns:
            Dict with validation result
        """
        try:
            # Use the utility function to validate balance
            is_sufficient = validate_account_balance(current_balance, required_amount)
            
            return {
                'success': True,
                'is_sufficient': is_sufficient,
                'current_balance': str(current_balance),
                'required_amount': str(required_amount)
            }
        except Exception as e:
            return handle_service_error("check_balance_sufficiency", e, {
                'success': False,
                'is_sufficient': False,
                'current_balance': str(current_balance) if current_balance else None,
                'required_amount': str(required_amount) if required_amount else None,
                'message': f"Failed to check balance sufficiency: {str(e)}"
            })