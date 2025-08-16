"""
Utility module for common functions used across bank services.
"""
import logging
import uuid
from decimal import Decimal
from typing import Dict, Any, Optional
from django.utils import timezone

logger = logging.getLogger(__name__)


class BankServiceUtils:
    """
    Utility class containing common functions used across bank services.
    """
    
    @staticmethod
    def generate_reference(prefix: str = "REF", user_account_suffix: str = "0000") -> str:
        """
        Generate a standardized reference string.
        
        Args:
            prefix: Reference prefix (e.g., "BT" for bank transfer)
            user_account_suffix: Last 4 digits of user's account number
            
        Returns:
            Generated reference string
        """
        date_str = timezone.now().strftime('%Y%m%d')
        time_str = timezone.now().strftime('%H%M%S')
        unique_part = uuid.uuid4().hex[:6].upper()
        return f"{prefix}-{date_str}-{time_str}-{user_account_suffix}-{unique_part}"
    
    @staticmethod
    def safe_money_calculation(amount, percentage):
        """
        Safely calculate money amounts ensuring type consistency.
        
        Args:
            amount: The base amount (Money or Decimal)
            percentage: The percentage to apply (Decimal or float)
            
        Returns:
            Calculated amount as Decimal
        """
        # Ensure we're working with Decimal types
        if hasattr(amount, 'amount'):  # Money object
            base_amount = Decimal(str(amount.amount))
        else:  # Decimal or other numeric type
            base_amount = Decimal(str(amount))
            
        if isinstance(percentage, float):
            percentage = Decimal(str(percentage))
        else:
            percentage = Decimal(str(percentage))
            
        return (base_amount * percentage) / Decimal('100')
    
    @staticmethod
    def handle_service_error(operation: str, error: Exception, default_return=None) -> Any:
        """
        Standardized error handling for service operations.
        
        Args:
            operation: Name of the operation that failed
            error: The exception that occurred
            default_return: What to return in case of error
            
        Returns:
            default_return value or re-raises exception based on error type
        """
        logger.error(f"Error in {operation}: {str(error)}")
        
        # For critical errors, you might want to re-raise or handle differently
        if "database" in str(error).lower():
            logger.critical(f"Database error in {operation}: {str(error)}")
            # Could trigger alerts or special handling here
            
        return default_return
    
    @staticmethod
    def validate_account_balance(balance, required_amount) -> bool:
        """
        Validate that an account has sufficient balance.
        
        Args:
            balance: Current account balance (Money object)
            required_amount: Required amount (Money object)
            
        Returns:
            True if sufficient balance, False otherwise
        """
        try:
            return balance >= required_amount
        except Exception as e:
            logger.error(f"Error validating account balance: {str(e)}")
            return False

# Convenience functions for backward compatibility
def generate_reference(prefix: str = "REF", user_account_suffix: str = "0000") -> str:
    """Convenience function for reference generation."""
    return BankServiceUtils.generate_reference(prefix, user_account_suffix)

def safe_money_calculation(amount, percentage):
    """Convenience function for money calculations."""
    return BankServiceUtils.safe_money_calculation(amount, percentage)

def handle_service_error(operation: str, error: Exception, default_return=None) -> Any:
    """Convenience function for error handling."""
    return BankServiceUtils.handle_service_error(operation, error, default_return)

def validate_account_balance(balance, required_amount) -> bool:
    """Convenience function for balance validation."""
    return BankServiceUtils.validate_account_balance(balance, required_amount)