"""
Bank services for handling bank-related business logic.
"""
import logging
import requests
import os
import secrets
import uuid
import statistics
from typing import List, Dict, Optional
from django.conf import settings
from django.db import models
from django.utils import timezone
from .models import Bank, Wallet, BankTransfer

logger = logging.getLogger(__name__)

class BankAccountService:
    """
    Service for handling bank account verification and search operations.
    """
    
    @staticmethod
    def search_banks_by_account_number(account_number: str) -> List[Dict]:
        """
        Search for banks that have a specific account number.
        
        Args:
            account_number (str): The account number to search for
            
        Returns:
            List[Dict]: List of banks with account details
        """
        if not account_number or not account_number.isdigit() or len(account_number) < 10:
            return []
        
        try:
            # In production, you would integrate with NIBSS API or individual bank APIs
            # For now, we'll use a mock implementation
            
            # Get all available banks from database
            banks = Bank.objects.all()
            
            matching_banks = []
            
            for bank in banks:
                # Mock verification - in real scenario, call bank API
                if BankAccountService._verify_account_with_bank(bank.code, account_number):
                    matching_banks.append({
                        'bank_code': bank.code,
                        'bank_name': bank.name,
                        'account_number': account_number,
                        'account_name': BankAccountService._get_account_name(bank.code, account_number),
                        'is_verified': True,
                        'verification_method': 'api' if settings.DEBUG else 'nibss'
                    })
            
            return matching_banks
            
        except Exception as e:
            logger.error(f"Error searching banks by account number: {str(e)}")
            return []
    
    @staticmethod
    def _verify_account_with_bank(bank_code: str, account_number: str) -> bool:
        """
        Verify if account exists in a specific bank.
        
        Args:
            bank_code (str): Bank code
            account_number (str): Account number
            
        Returns:
            bool: True if account exists, False otherwise
        """
        try:
            # Mock verification logic
            # In production, this would call the actual bank API or NIBSS API
            
            # Simple mock: if account number ends with certain digits, it exists in certain banks
            last_digit = int(account_number[-1])
            
            # Mock mapping: certain account numbers exist in certain banks
            bank_verification_map = {
                '044': last_digit in [0, 1, 2],  # Access Bank
                '058': last_digit in [3, 4, 5],  # GT Bank
                '011': last_digit in [6, 7],     # First Bank
                '032': last_digit in [8],        # Union Bank
                '033': last_digit in [9],        # UBA
                '057': last_digit in [0, 5],     # Zenith Bank
                '030': last_digit in [1, 6],     # Heritage Bank
                '070': last_digit in [2, 7],     # Fidelity Bank
                '050': last_digit in [0, 3, 6],  # Ecobank
                '076': last_digit in [1, 4, 7],  # Polaris Bank
                '082': last_digit in [2, 5, 8],  # Keystone Bank
                '084': last_digit in [0, 2, 4],  # Unity Bank
                '085': last_digit in [1, 3, 5],  # First City Monument Bank
                '100': last_digit in [6, 7, 8],  # Suntrust Bank
                '101': last_digit in [9, 0, 1],  # Providus Bank
                '102': last_digit in [2, 3, 4],  # Titan Trust Bank
                '103': last_digit in [5, 6, 7],  # Globus Bank
                '104': last_digit in [8, 9, 0],  # Parallex Bank
                '105': last_digit in [1, 2, 3],  # Premium Trust Bank
                '106': last_digit in [4, 5, 6],  # Keystone Bank
            }
            
            return bank_verification_map.get(bank_code, False)
            
        except Exception as e:
            logger.error(f"Error verifying account with bank {bank_code}: {str(e)}")
            return False
    
    @staticmethod
    def _get_account_name(bank_code: str, account_number: str) -> str:
        """
        Get account holder name for a given bank and account number.
        
        Args:
            bank_code (str): Bank code
            account_number (str): Account number
            
        Returns:
            str: Account holder name (mock implementation)
        """
        try:
            # Mock account names - in production, this would come from bank API
            # For now, we'll generate a mock name based on account number
            
            # Use last 4 digits to create a mock name
            last_four = account_number[-4:]
            
            # Mock names based on account number pattern
            mock_names = [
                "John Doe",
                "Jane Smith",
                "Michael Johnson",
                "Sarah Williams",
                "David Brown",
                "Lisa Davis",
                "Robert Wilson",
                "Mary Miller",
                "James Taylor",
                "Patricia Anderson"
            ]
            
            # Use account number to select a name
            name_index = int(last_four) % len(mock_names)
            return mock_names[name_index]
            
        except Exception as e:
            logger.error(f"Error getting account name: {str(e)}")
            return f"Account Holder {account_number[-4:]}"
    
    @staticmethod
    def verify_account_with_nibss(bank_code: str, account_number: str) -> Dict:
        """
        Verify account with NIBSS API (production implementation).
        
        Args:
            bank_code (str): Bank code
            account_number (str): Account number
            
        Returns:
            Dict: Verification result
        """
        try:
            # This is where you would integrate with NIBSS API
            # For now, return mock data
            
            # In production, you would:
            # 1. Call NIBSS API with bank_code and account_number
            # 2. Get real account holder name
            # 3. Verify account exists
            
            return {
                'is_valid': True,
                'account_name': BankAccountService._get_account_name(bank_code, account_number),
                'bank_code': bank_code,
                'account_number': account_number,
                'verification_method': 'nibss'
            }
            
        except Exception as e:
            logger.error(f"Error verifying account with NIBSS: {str(e)}")
            return {
                'is_valid': False,
                'error': str(e),
                'verification_method': 'nibss'
            }
    
    @staticmethod
    def get_all_banks() -> List[Dict]:
        """
        Get all available banks.
        
        Returns:
            List[Dict]: List of all banks
        """
        try:
            banks = Bank.objects.all().order_by('name')
            return [
                {
                    'bank_code': bank.code,
                    'bank_name': bank.name,
                    'is_active': bank.is_active
                }
                for bank in banks
            ]
        except Exception as e:
            logger.error(f"Error getting all banks: {str(e)}")
            return []

class FraudDetectionService:
    """
    Service for fraud detection and risk assessment.
    Implements real-time ML-based transaction monitoring and fraud detection.
    """
    
    # Time windows for pattern analysis (in minutes)
    SHORT_WINDOW = 5  # 5 minutes
    MEDIUM_WINDOW = 60  # 1 hour
    LONG_WINDOW = 1440  # 24 hours
    
    # Thresholds for different fraud patterns
    VELOCITY_THRESHOLD = 5  # Max transactions per SHORT_WINDOW
    AMOUNT_VARIANCE_THRESHOLD = 3.0  # Standard deviations from mean
    SUSPICIOUS_COUNTRY_CODES = {'NG', 'GH', 'KE', 'ZA'}  # High-risk countries
    
    @staticmethod
    def analyze_transaction_patterns(user, amount: float, recipient_account: str, 
                                  ip_address: str, device_fingerprint: str) -> Dict:
        """
        Analyze transaction patterns in real-time using ML-based detection.
        
        Args:
            user: User making the transfer
            amount: Transfer amount
            recipient_account: Recipient account number
            ip_address: IP address of the request
            device_fingerprint: Device fingerprint
            
        Returns:
            Dict: Analysis results with risk factors
        """
        try:
            risk_factors = []
            risk_score = 0
            
            # 1. Velocity Check - Unusual number of transactions in short time
            recent_txns = BankTransfer.objects.filter(
                user=user,
                created_at__gte=timezone.now() - timezone.timedelta(minutes=FraudDetectionService.SHORT_WINDOW)
            ).count()
            
            if recent_txns >= FraudDetectionService.VELOCITY_THRESHOLD:
                risk_factors.append({
                    'type': 'velocity_alert',
                    'severity': 'high',
                    'details': f'Unusual transaction frequency: {recent_txns} transactions in {FraudDetectionService.SHORT_WINDOW} minutes'
                })
                risk_score += 30
            
            # 2. Amount Pattern Analysis
            user_transactions = BankTransfer.objects.filter(
                user=user,
                status='completed',
                created_at__gte=timezone.now() - timezone.timedelta(minutes=FraudDetectionService.LONG_WINDOW)
            ).values_list('amount', flat=True)
            
            if user_transactions:
                mean_amount = statistics.mean(user_transactions)
                std_dev = statistics.stdev(user_transactions) if len(user_transactions) > 1 else mean_amount
                
                if amount > mean_amount + (std_dev * FraudDetectionService.AMOUNT_VARIANCE_THRESHOLD):
                    risk_factors.append({
                        'type': 'amount_anomaly',
                        'severity': 'medium',
                        'details': 'Transaction amount significantly higher than user pattern'
                    })
                    risk_score += 20
            
            # 3. Location/IP Analysis
            try:
                import geoip2.database
                reader = geoip2.database.Reader('path/to/GeoLite2-Country.mmdb')
                ip_info = reader.country(ip_address)
                
                if ip_info.country.iso_code in FraudDetectionService.SUSPICIOUS_COUNTRY_CODES:
                    risk_factors.append({
                        'type': 'location_risk',
                        'severity': 'medium',
                        'details': f'Transaction from high-risk location: {ip_info.country.name}'
                    })
                    risk_score += 25
            except Exception as e:
                logger.warning(f"Error in IP geolocation: {str(e)}")
            
            # 4. Device Switching Pattern
            recent_devices = BankTransfer.objects.filter(
                user=user,
                created_at__gte=timezone.now() - timezone.timedelta(minutes=FraudDetectionService.MEDIUM_WINDOW)
            ).values_list('device_fingerprint', flat=True).distinct()
            
            if len(recent_devices) > 2:
                risk_factors.append({
                    'type': 'device_switching',
                    'severity': 'high',
                    'details': 'Multiple devices used in short time period'
                })
                risk_score += 35
            
            # 5. Recipient Risk Analysis
            recipient_history = BankTransfer.objects.filter(
                recipient_account=recipient_account,
                status='completed'
            ).values('user').distinct().count()
            
            if recipient_history > 10:
                risk_factors.append({
                    'type': 'recipient_pattern',
                    'severity': 'low',
                    'details': 'Recipient account has unusual number of different senders'
                })
                risk_score += 15
            
            return {
                'risk_score': min(risk_score, 100),
                'risk_factors': risk_factors,
                'timestamp': timezone.now().isoformat(),
                'requires_review': risk_score > 70,
                'analysis_id': str(uuid.uuid4())
            }
            
        except Exception as e:
            logger.error(f"Error in transaction pattern analysis: {str(e)}")
            return {
                'risk_score': 50,  # Default medium risk on error
                'risk_factors': [{
                    'type': 'analysis_error',
                    'severity': 'medium',
                    'details': 'Error in pattern analysis'
                }],
                'requires_review': True  # Err on the side of caution
            }
    
    @staticmethod
    def calculate_fraud_score(user, amount, recipient_account, recipient_bank_code, device_fingerprint, ip_address) -> Dict:
        """
        Calculate comprehensive fraud score using ML-based pattern analysis.
        
        Args:
            user: User making the transfer
            amount: Transfer amount
            recipient_account: Recipient account number
            recipient_bank_code: Recipient bank code
            device_fingerprint: Device fingerprint
            ip_address: IP address
            
        Returns:
            Dict: Fraud analysis result with score and risk factors
        """
        try:
            # Get real-time pattern analysis
            pattern_analysis = FraudDetectionService.analyze_transaction_patterns(
                user, amount, recipient_account, ip_address, device_fingerprint
            )
            
            # Initialize base score from pattern analysis
            score = pattern_analysis['risk_score']
            
            # Check if amount is unusually high for the user
            try:
                avg_transfer = BankTransfer.objects.filter(
                    user=user,
                    status='completed'
                ).aggregate(avg_amount=models.Avg('amount'))['avg_amount'] or 0
                
                if amount > (avg_transfer * 3):  # If amount is 3x higher than average
                    score += 20
                if amount > (avg_transfer * 5):  # If amount is 5x higher than average
                    score += 20
            except Exception as e:
                logger.warning(f"Error calculating average transfer: {str(e)}")
            
            # Check if recipient is new
            try:
                previous_transfers = BankTransfer.objects.filter(
                    user=user,
                    recipient_account=recipient_account,
                    bank_code=recipient_bank_code,
                    status='completed'
                ).count()
                
                if previous_transfers == 0:  # New recipient
                    score += 15
            except Exception as e:
                logger.warning(f"Error checking previous transfers: {str(e)}")
            
            # Check device fingerprint
            try:
                device_transfers = BankTransfer.objects.filter(
                    user=user,
                    device_fingerprint=device_fingerprint
                ).count()
                
                if device_transfers == 0:  # New device
                    score += 25
            except Exception as e:
                logger.warning(f"Error checking device transfers: {str(e)}")
            
            # Check IP address
            try:
                ip_transfers = BankTransfer.objects.filter(
                    user=user,
                    ip_address=ip_address
                ).count()
                
                if ip_transfers == 0:  # New IP
                    score += 20
            except Exception as e:
                logger.warning(f"Error checking IP transfers: {str(e)}")
            
            return min(score, 100)  # Cap score at 100
            
        except Exception as e:
            logger.error(f"Error calculating fraud score: {str(e)}")
            return 50  # Return medium risk score on error
    
    @staticmethod
    def should_require_2fa(user, amount, fraud_score) -> bool:
        """
        Determine if 2FA should be required for a transfer.
        
        Args:
            user: User making the transfer
            amount: Transfer amount
            fraud_score: Calculated fraud score
            
        Returns:
            bool: True if 2FA should be required
        """
        try:
            # Get user's average transfer amount
            avg_transfer = BankTransfer.objects.filter(
                user=user,
                status='completed'
            ).aggregate(avg_amount=models.Avg('amount'))['avg_amount'] or 0
            
            # Require 2FA if:
            # 1. Fraud score is high (>70)
            # 2. Amount is significantly higher than average (>3x)
            # 3. Amount is large (>1M NGN)
            return (
                fraud_score > 70 or
                amount > (avg_transfer * 3) or
                amount > 1000000  # 1M NGN
            )
            
        except Exception as e:
            logger.error(f"Error determining 2FA requirement: {str(e)}")
            return True  # Require 2FA on error to be safe
    
    @staticmethod
    def should_require_approval(user, amount, fraud_score) -> bool:
        """
        Determine if staff approval should be required for a transfer.
        
        Args:
            user: User making the transfer
            amount: Transfer amount
            fraud_score: Calculated fraud score
            
        Returns:
            bool: True if staff approval should be required
        """
        try:
            # Get user's average transfer amount
            avg_transfer = BankTransfer.objects.filter(
                user=user,
                status='completed'
            ).aggregate(avg_amount=models.Avg('amount'))['avg_amount'] or 0
            
            # Require approval if:
            # 1. Fraud score is very high (>85)
            # 2. Amount is very high (>5M NGN)
            # 3. Amount is significantly higher than average (>5x)
            return (
                fraud_score > 85 or
                amount > 5000000 or  # 5M NGN
                amount > (avg_transfer * 5)
            )
            
        except Exception as e:
            logger.error(f"Error determining approval requirement: {str(e)}")
            return True  # Require approval on error to be safe
    
    @staticmethod
    def _get_fraud_flags(user, amount, recipient_account) -> List[str]:
        """
        Get list of fraud flags for a transfer.
        
        Args:
            user: User making the transfer
            amount: Transfer amount
            recipient_account: Recipient account number
            
        Returns:
            List[str]: List of fraud flags
        """
        flags = []
        
        try:
            # Check if amount is unusually high
            avg_transfer = BankTransfer.objects.filter(
                user=user,
                status='completed'
            ).aggregate(avg_amount=models.Avg('amount'))['avg_amount'] or 0
            
            if amount > (avg_transfer * 3):
                flags.append('unusual_amount')
            
            # Check if recipient is new
            if not BankTransfer.objects.filter(
                user=user,
                recipient_account=recipient_account,
                status='completed'
            ).exists():
                flags.append('new_recipient')
            
            # Check for multiple transfers in short time
            recent_transfers = BankTransfer.objects.filter(
                user=user,
                created_at__gte=timezone.now() - timezone.timedelta(minutes=5)
            ).count()
            
            if recent_transfers > 3:
                flags.append('rapid_transfers')
            
            return flags
            
        except Exception as e:
            logger.error(f"Error getting fraud flags: {str(e)}")
            return ['error_checking_flags']


class TwoFactorAuthService:
    """
    Service for handling two-factor authentication.
    """
    
    @staticmethod
    def generate_2fa_code() -> str:
        """
        Generate a random 6-digit 2FA code.
        
        Returns:
            str: 6-digit code
        """
        import random
        return ''.join([str(random.randint(0, 9)) for _ in range(6)])
    
    @staticmethod
    def send_2fa_code(user, code: str, transfer_amount: float, recipient_account: str):
        """
        Send 2FA code to user via SMS and/or email.
        
        Args:
            user: User to send code to
            code: Generated 2FA code
            transfer_amount: Amount being transferred
            recipient_account: Recipient account number
        """
        try:
            # Format message
            message = (
                f"Your verification code for transfer of {transfer_amount} NGN "
                f"to account {recipient_account[-4:]} is: {code}\n"
                "This code expires in 10 minutes."
            )
            
            # Send SMS if phone number exists
            if hasattr(user, 'profile') and user.profile.phone_number:
                TwoFactorAuthService._send_sms(
                    phone_number=user.profile.phone_number,
                    message=message
                )
            
            # Send email
            TwoFactorAuthService._send_email(
                email=user.email,
                subject="Transfer Verification Code",
                message=message
            )
            
            logger.info(f"2FA code sent to user {user.id} via SMS/email")
            
        except Exception as e:
            logger.error(f"Error sending 2FA code: {str(e)}")
            raise
    
    @staticmethod
    def verify_2fa_code(transfer, code: str) -> bool:
        """
        Verify a 2FA code for a transfer.
        
        Args:
            transfer: Transfer being verified
            code: Code to verify
            
        Returns:
            bool: True if code is valid
        """
        try:
            if not transfer.two_fa_code or not transfer.two_fa_expires_at:
                logger.error(f"No 2FA code found for transfer {transfer.id}")
                return False
            
            # Check if code has expired
            if timezone.now() > transfer.two_fa_expires_at:
                logger.warning(f"2FA code expired for transfer {transfer.id}")
                return False
            
            # Verify code
            is_valid = transfer.two_fa_code == code
            
            if is_valid:
                logger.info(f"2FA code verified for transfer {transfer.id}")
            else:
                logger.warning(f"Invalid 2FA code provided for transfer {transfer.id}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error verifying 2FA code: {str(e)}")
            return False
    
    @staticmethod
    def _send_sms(phone_number: str, message: str):
        """
        Send SMS via SMS gateway/provider.
        
        Args:
            phone_number: Recipient phone number
            message: Message to send
        """
        try:
            # In production, integrate with SMS gateway
            # For now, just log the message
            logger.info(f"[MOCK SMS] To: {phone_number}, Message: {message}")
            
        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            raise
    
    @staticmethod
    def _send_email(email: str, subject: str, message: str):
        """
        Send email via email service.
        
        Args:
            email: Recipient email
            subject: Email subject
            message: Email message
        """
        try:
            # In production, use Django's email backend or email service
            # For now, just log the message
            logger.info(f"[MOCK EMAIL] To: {email}, Subject: {subject}, Message: {message}")
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            raise


class DeviceFingerprintService:
    """
    Service for generating and validating device fingerprints.
    Device fingerprinting helps identify and track devices for security purposes.
    """
    
    @staticmethod
    def generate_device_fingerprint(request) -> str:
        """
        Generate a device fingerprint from request data.
        
        Args:
            request: HTTP request object
            
        Returns:
            str: Device fingerprint hash
        """
        try:
            import hashlib
            import json
            
            # Collect device information from request headers
            headers = request.headers
            user_agent = headers.get('User-Agent', '')
            accept_language = headers.get('Accept-Language', '')
            accept_encoding = headers.get('Accept-Encoding', '')
            
            # Get IP address
            ip = DeviceFingerprintService._get_client_ip(request)
            
            # Combine device data
            device_data = {
                'user_agent': user_agent,
                'accept_language': accept_language,
                'accept_encoding': accept_encoding,
                'ip_address': ip,
                # Add more device characteristics as needed
            }
            
            # Generate hash
            data_string = json.dumps(device_data, sort_keys=True)
            hash_object = hashlib.sha256(data_string.encode())
            fingerprint = hash_object.hexdigest()
            
            return fingerprint
            
        except Exception as e:
            logger.error(f"Error generating device fingerprint: {str(e)}")
            return DeviceFingerprintService._generate_fallback_fingerprint(request)
    
    @staticmethod
    def _get_client_ip(request) -> str:
        """
        Get client IP address from request.
        
        Args:
            request: HTTP request object
            
        Returns:
            str: Client IP address
        """
        try:
            x_forwarded_for = request.headers.get('X-Forwarded-For')
            if x_forwarded_for:
                # Take first IP if multiple are present
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = request.headers.get('X-Real-IP') or request.META.get('REMOTE_ADDR')
            return ip
        except Exception as e:
            logger.error(f"Error getting client IP: {str(e)}")
            return ''
    
    @staticmethod
    def _generate_fallback_fingerprint(request) -> str:
        """
        Generate a basic fallback fingerprint when full fingerprinting fails.
        
        Args:
            request: HTTP request object
            
        Returns:
            str: Basic device fingerprint
        """
        try:
            import hashlib
            import time
            
            # Use basic data that should always be available
            basic_data = {
                'ip': request.META.get('REMOTE_ADDR', ''),
                'user_agent': request.headers.get('User-Agent', ''),
                'timestamp': int(time.time())
            }
            
            # Generate hash
            data_string = str(basic_data)
            hash_object = hashlib.sha256(data_string.encode())
            return hash_object.hexdigest()
            
        except Exception as e:
            logger.error(f"Error generating fallback fingerprint: {str(e)}")
            return hashlib.sha256(str(time.time()).encode()).hexdigest()
    
    @staticmethod
    def compare_fingerprints(fingerprint1: str, fingerprint2: str) -> float:
        """
        Compare two fingerprints and return similarity score.
        
        Args:
            fingerprint1: First fingerprint
            fingerprint2: Second fingerprint
            
        Returns:
            float: Similarity score (0-1)
        """
        try:
            if not fingerprint1 or not fingerprint2:
                return 0.0
                
            # Convert to sets of characters for comparison
            set1 = set(fingerprint1)
            set2 = set(fingerprint2)
            
            # Calculate Jaccard similarity
            intersection = len(set1.intersection(set2))
            union = len(set1.union(set2))
            
            return intersection / union if union > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error comparing fingerprints: {str(e)}")
            return 0.0


class IdempotencyService:
    """
    Service for handling idempotent requests to prevent duplicate transactions.
    """
    
    @staticmethod
    def get_idempotency_key(request) -> str:
        """
        Get idempotency key from request headers.
        
        Args:
            request: HTTP request object
            
        Returns:
            str: Idempotency key
        """
        return request.headers.get('X-Idempotency-Key', '')
    
    @staticmethod
    def is_duplicate_request(idempotency_key: str, user_id: int) -> bool:
        """
        Check if request with given idempotency key is a duplicate.
        
        Args:
            idempotency_key: Idempotency key from request
            user_id: ID of user making request
            
        Returns:
            bool: True if request is duplicate
        """
        try:
            from django.core.cache import cache
            
            if not idempotency_key:
                return False
                
            # Create unique cache key for user+idempotency combination
            cache_key = f"idempotency:{user_id}:{idempotency_key}"
            
            # Try to add key to cache
            # If key already exists, request is duplicate
            if cache.add(cache_key, True, timeout=86400):  # 24 hour timeout
                return False
            return True
            
        except Exception as e:
            logger.error(f"Error checking idempotency: {str(e)}")
            return False
    
    @staticmethod
    def clear_idempotency_key(idempotency_key: str, user_id: int):
        """
        Clear idempotency key from cache.
        
        Args:
            idempotency_key: Idempotency key to clear
            user_id: ID of user who made request
        """
        try:
            from django.core.cache import cache
            
            if idempotency_key:
                cache_key = f"idempotency:{user_id}:{idempotency_key}"
                cache.delete(cache_key)
                
        except Exception as e:
            logger.error(f"Error clearing idempotency key: {str(e)}")


class TransactionPinService:
    """
    Service for handling transaction PIN operations including
    creation, validation, reset, and security measures.
    """
    
    PIN_LENGTH = 4  # Standard 4-digit PIN
    MAX_ATTEMPTS = 3  # Maximum failed attempts before temporary lockout
    LOCKOUT_DURATION = 30  # Lockout duration in minutes
    
    @staticmethod
    def create_transaction_pin(user, pin: str) -> Dict:
        """
        Create or update a user's transaction PIN.
        
        Args:
            user: User to set PIN for
            pin: New PIN to set
            
        Returns:
            Dict: Creation result
        """
        try:
            if not pin.isdigit() or len(pin) != TransactionPinService.PIN_LENGTH:
                return {
                    'success': False,
                    'error': f'PIN must be {TransactionPinService.PIN_LENGTH} digits'
                }
            
            # Hash the PIN before storing
            import hashlib
            import os
            salt = os.urandom(32)  # Generate a new salt
            pin_hash = hashlib.pbkdf2_hmac(
                'sha256',
                pin.encode(),
                salt,
                100000  # Number of iterations
            )
            
            # Store PIN hash and salt in user profile
            user.profile.transaction_pin_hash = pin_hash
            user.profile.transaction_pin_salt = salt
            user.profile.pin_failed_attempts = 0
            user.profile.pin_locked_until = None
            user.profile.save()
            
            return {
                'success': True,
                'message': 'Transaction PIN created successfully'
            }
            
        except Exception as e:
            logger.error(f"Error creating transaction PIN: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to create transaction PIN'
            }
    
    @staticmethod
    def verify_transaction_pin(user, pin: str) -> Dict:
        """
        Verify a transaction PIN.
        
        Args:
            user: User to verify PIN for
            pin: PIN to verify
            
        Returns:
            Dict: Verification result
        """
        try:
            # Check if PIN is locked
            if user.profile.pin_locked_until:
                if timezone.now() < user.profile.pin_locked_until:
                    remaining_time = (user.profile.pin_locked_until - timezone.now()).minutes
                    return {
                        'success': False,
                        'error': f'PIN is locked. Try again in {remaining_time} minutes',
                        'is_locked': True,
                        'remaining_time': remaining_time
                    }
                else:
                    # Reset lockout if duration has passed
                    user.profile.pin_locked_until = None
                    user.profile.pin_failed_attempts = 0
                    user.profile.save()
            
            # Verify the PIN
            import hashlib
            pin_hash = hashlib.pbkdf2_hmac(
                'sha256',
                pin.encode(),
                user.profile.transaction_pin_salt,
                100000
            )
            
            if pin_hash == user.profile.transaction_pin_hash:
                # Reset failed attempts on successful verification
                user.profile.pin_failed_attempts = 0
                user.profile.save()
                
                return {
                    'success': True,
                    'message': 'PIN verified successfully'
                }
            else:
                # Increment failed attempts
                user.profile.pin_failed_attempts += 1
                
                # Check if should lock
                if user.profile.pin_failed_attempts >= TransactionPinService.MAX_ATTEMPTS:
                    user.profile.pin_locked_until = timezone.now() + timezone.timedelta(
                        minutes=TransactionPinService.LOCKOUT_DURATION
                    )
                    user.profile.save()
                    
                    return {
                        'success': False,
                        'error': f'PIN locked for {TransactionPinService.LOCKOUT_DURATION} minutes due to too many failed attempts',
                        'is_locked': True,
                        'remaining_time': TransactionPinService.LOCKOUT_DURATION
                    }
                
                user.profile.save()
                remaining_attempts = TransactionPinService.MAX_ATTEMPTS - user.profile.pin_failed_attempts
                
                return {
                    'success': False,
                    'error': f'Invalid PIN. {remaining_attempts} attempts remaining',
                    'remaining_attempts': remaining_attempts
                }
            
        except Exception as e:
            logger.error(f"Error verifying transaction PIN: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to verify transaction PIN'
            }
    
    @staticmethod
    def reset_transaction_pin(user, old_pin: str, new_pin: str) -> Dict:
        """
        Reset a transaction PIN.
        
        Args:
            user: User to reset PIN for
            old_pin: Current PIN
            new_pin: New PIN to set
            
        Returns:
            Dict: Reset result
        """
        try:
            # First verify the old PIN
            verify_result = TransactionPinService.verify_transaction_pin(user, old_pin)
            if not verify_result['success']:
                return verify_result
            
            # Then create new PIN
            return TransactionPinService.create_transaction_pin(user, new_pin)
            
        except Exception as e:
            logger.error(f"Error resetting transaction PIN: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to reset transaction PIN'
            }
    
    @staticmethod
    def request_pin_reset(user) -> Dict:
        """
        Request a PIN reset (for forgotten PINs).
        This will trigger a verification process (e.g., SMS, email).
        
        Args:
            user: User requesting PIN reset
            
        Returns:
            Dict: Request result
        """
        try:
            # Generate reset token
            import secrets
            reset_token = secrets.token_urlsafe(32)
            reset_expires = timezone.now() + timezone.timedelta(minutes=30)
            
            # Save token and expiry
            user.profile.pin_reset_token = reset_token
            user.profile.pin_reset_expires = reset_expires
            user.profile.save()
            
            # Send reset instructions via SMS and email
            message = (
                f"You have requested to reset your transaction PIN.\n"
                f"Your reset code is: {reset_token[:6]}\n"
                "This code will expire in 30 minutes."
            )
            
            # Send via SMS if phone number exists
            if user.profile.phone_number:
                TwoFactorAuthService._send_sms(
                    phone_number=user.profile.phone_number,
                    message=message
                )
            
            # Send via email
            TwoFactorAuthService._send_email(
                email=user.email,
                subject="Transaction PIN Reset Request",
                message=message
            )
            
            return {
                'success': True,
                'message': 'PIN reset instructions sent',
                'expires_in': '30 minutes'
            }
            
        except Exception as e:
            logger.error(f"Error requesting PIN reset: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to process PIN reset request'
            }
    
    @staticmethod
    def verify_pin_reset(user, reset_token: str, new_pin: str) -> Dict:
        """
        Verify PIN reset token and set new PIN.
        
        Args:
            user: User resetting PIN
            reset_token: Reset verification token
            new_pin: New PIN to set
            
        Returns:
            Dict: Reset verification result
        """
        try:
            # Verify token and expiry
            if not user.profile.pin_reset_token or not user.profile.pin_reset_expires:
                return {
                    'success': False,
                    'error': 'No active PIN reset request'
                }
            
            if timezone.now() > user.profile.pin_reset_expires:
                return {
                    'success': False,
                    'error': 'PIN reset token has expired'
                }
            
            if not secrets.compare_digest(reset_token, user.profile.pin_reset_token):
                return {
                    'success': False,
                    'error': 'Invalid reset token'
                }
            
            # Clear reset token and set new PIN
            user.profile.pin_reset_token = None
            user.profile.pin_reset_expires = None
            user.profile.save()
            
            return TransactionPinService.create_transaction_pin(user, new_pin)
            
        except Exception as e:
            logger.error(f"Error verifying PIN reset: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to verify PIN reset'
            }


class BiometricService:
    """
    Service for handling biometric authentication.
    Supports fingerprint, face, and voice biometrics.
    """
    
    BIOMETRIC_TYPES = {
        'fingerprint': 'fingerprint',
        'face': 'face',
        'voice': 'voice'
    }
    
    @staticmethod
    def register_biometric(user, biometric_type: str, biometric_data: str) -> Dict:
        """
        Register a new biometric identifier for a user.
        
        Args:
            user: User to register biometric for
            biometric_type: Type of biometric (fingerprint, face, voice)
            biometric_data: Encrypted/hashed biometric template
            
        Returns:
            Dict: Registration result
        """
        try:
            # In production, integrate with actual biometric hardware/SDK
            # For now, we'll implement a mock version
            
            if biometric_type not in BiometricService.BIOMETRIC_TYPES:
                raise ValueError(f"Invalid biometric type. Must be one of: {', '.join(BiometricService.BIOMETRIC_TYPES.keys())}")
            
            # Hash the biometric data for secure storage
            import hashlib
            hashed_data = hashlib.sha256(biometric_data.encode()).hexdigest()
            
            # In production, store in secure database/HSM
            # For now, store in user profile
            if not hasattr(user, 'biometric_data'):
                user.biometric_data = {}
            
            user.biometric_data[biometric_type] = {
                'template': hashed_data,
                'registered_at': timezone.now().isoformat(),
                'last_used': None
            }
            user.save()
            
            return {
                'success': True,
                'message': f'{biometric_type.title()} biometric registered successfully',
                'biometric_type': biometric_type,
                'registered_at': user.biometric_data[biometric_type]['registered_at']
            }
            
        except Exception as e:
            logger.error(f"Error registering biometric: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def verify_biometric(user, biometric_type: str, biometric_data: str) -> Dict:
        """
        Verify a biometric against stored template.
        
        Args:
            user: User to verify biometric for
            biometric_type: Type of biometric (fingerprint, face, voice)
            biometric_data: Biometric data to verify
            
        Returns:
            Dict: Verification result
        """
        try:
            if biometric_type not in BiometricService.BIOMETRIC_TYPES:
                raise ValueError(f"Invalid biometric type. Must be one of: {', '.join(BiometricService.BIOMETRIC_TYPES.keys())}")
            
            if not hasattr(user, 'biometric_data') or biometric_type not in user.biometric_data:
                return {
                    'success': False,
                    'error': f'No {biometric_type} biometric registered for user'
                }
            
            # Hash the provided biometric data
            import hashlib
            hashed_data = hashlib.sha256(biometric_data.encode()).hexdigest()
            
            # Compare with stored template
            stored_template = user.biometric_data[biometric_type]['template']
            is_match = hashed_data == stored_template
            
            if is_match:
                # Update last used timestamp
                user.biometric_data[biometric_type]['last_used'] = timezone.now().isoformat()
                user.save()
                
                return {
                    'success': True,
                    'message': f'{biometric_type.title()} verification successful',
                    'biometric_type': biometric_type,
                    'verified_at': timezone.now().isoformat()
                }
            else:
                return {
                    'success': False,
                    'error': f'{biometric_type.title()} verification failed'
                }
            
        except Exception as e:
            logger.error(f"Error verifying biometric: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_registered_biometrics(user) -> Dict:
        """
        Get list of registered biometrics for a user.
        
        Args:
            user: User to get biometrics for
            
        Returns:
            Dict: List of registered biometrics and their status
        """
        try:
            if not hasattr(user, 'biometric_data'):
                return {
                    'registered_biometrics': [],
                    'total_registered': 0
                }
            
            registered = []
            for biometric_type, data in user.biometric_data.items():
                registered.append({
                    'type': biometric_type,
                    'registered_at': data['registered_at'],
                    'last_used': data['last_used']
                })
            
            return {
                'registered_biometrics': registered,
                'total_registered': len(registered)
            }
            
        except Exception as e:
            logger.error(f"Error getting registered biometrics: {str(e)}")
            return {
                'registered_biometrics': [],
                'total_registered': 0,
                'error': str(e)
            }


class TransferValidationService:
    """
    Service for validating bank transfers.
    """
    
    @staticmethod
    def validate_transfer_request(user, amount, recipient_account, recipient_bank_code) -> Dict:
        """
        Validate a bank transfer request.
        
        Args:
            user: User making the transfer
            amount: Transfer amount
            recipient_account: Recipient account number
            recipient_bank_code: Recipient bank code
            
        Returns:
            Dict: Validation result
        """
        try:
            # Check if user has sufficient balance
            wallet = Wallet.objects.get(user=user)
            
            if wallet.balance < amount:
                return {
                    'is_valid': False,
                    'error': 'Insufficient balance',
                    'current_balance': str(wallet.balance),
                    'required_amount': str(amount)
                }
            
            # Check if recipient account is valid
            banks = BankAccountService.search_banks_by_account_number(recipient_account)
            recipient_bank = next((bank for bank in banks if bank['bank_code'] == recipient_bank_code), None)
            
            if not recipient_bank:
                return {
                    'is_valid': False,
                    'error': 'Invalid recipient account or bank',
                    'available_banks': [bank['bank_code'] for bank in banks]
                }
            
            return {
                'is_valid': True,
                'recipient_name': recipient_bank['account_name'],
                'bank_name': recipient_bank['bank_name'],
                'verification_method': recipient_bank['verification_method']
            }
            
        except Wallet.DoesNotExist:
            return {
                'is_valid': False,
                'error': 'Wallet not found. Complete KYC verification first.'
            }
        except Exception as e:
            logger.error(f"Error validating transfer request: {str(e)}")
            return {
                'is_valid': False,
                'error': 'Validation failed. Please try again.'
            } 