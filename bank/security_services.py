"""
Enhanced security services for the bank application.
"""
import logging
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q, Count, Sum
from .models import (
    TwoFactorAuthentication, IPWhitelist, DeviceFingerprint, 
    FraudDetection, SecurityAlert, TransferLimit, BankTransfer,
    User, NightGuardSettings, LargeTransactionShieldSettings, LocationGuardSettings
)
from .constants import (
    SecurityLevel, FraudFlag, TransferLimits, ResponseCodes,
    DeviceFingerprint as DeviceFingerprintEnum
)

logger = logging.getLogger(__name__)

class TwoFactorAuthService:
    """Service for handling Two-Factor Authentication."""
    
    @staticmethod
    def generate_token(user: User, token_type: str = 'sms') -> str:
        """Generate a 2FA token for the user."""
        try:
            # Generate a 6-digit token
            token = ''.join(secrets.choice('0123456789') for _ in range(6))
            
            # Set expiration time (10 minutes)
            expires_at = timezone.now() + timedelta(minutes=10)
            
            # Create 2FA record
            TwoFactorAuthentication.objects.create(
                user=user,
                token=token,
                token_type=token_type,
                expires_at=expires_at
            )
            
            logger.info(f"Generated 2FA token for user {user.username}")
            return token
            
        except Exception as e:
            logger.error(f"Error generating 2FA token: {str(e)}")
            raise
    
    @staticmethod
    def verify_token(user: User, token: str, token_type: str = 'sms') -> bool:
        """Verify a 2FA token."""
        try:
            # Get the most recent valid token
            two_fa = TwoFactorAuthentication.objects.filter(
                user=user,
                token=token,
                token_type=token_type,
                is_used=False,
                expires_at__gt=timezone.now()
            ).order_by('-created_at').first()
            
            if two_fa:
                # Mark as used
                two_fa.is_used = True
                two_fa.used_at = timezone.now()
                two_fa.save()
                
                logger.info(f"2FA token verified for user {user.username}")
                return True
            
            logger.warning(f"Invalid 2FA token for user {user.username}")
            return False
            
        except Exception as e:
            logger.error(f"Error verifying 2FA token: {str(e)}")
            return False
    
    @staticmethod
    def is_2fa_required(transfer: BankTransfer) -> bool:
        """Check if 2FA is required for a transfer."""
        amount = transfer.amount.amount
        return amount >= TransferLimits.HIGH_VALUE_THRESHOLD

class IPWhitelistService:
    """Service for IP address whitelisting."""
    
    @staticmethod
    def is_ip_allowed(user: User, ip_address: str) -> bool:
        """Check if an IP address is allowed for the user."""
        try:
            # Check if IP is whitelisted
            whitelist_entry = IPWhitelist.objects.filter(
                user=user,
                ip_address=ip_address,
                status='allowed',
                is_active=True
            ).first()
            
            return whitelist_entry is not None
            
        except Exception as e:
            logger.error(f"Error checking IP whitelist: {str(e)}")
            return False
    
    @staticmethod
    def add_ip_to_whitelist(user: User, ip_address: str, description: str = "") -> bool:
        """Add an IP address to the whitelist."""
        try:
            IPWhitelist.objects.create(
                user=user,
                ip_address=ip_address,
                description=description,
                status='allowed'
            )
            
            logger.info(f"Added IP {ip_address} to whitelist for user {user.username}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding IP to whitelist: {str(e)}")
            return False

class DeviceFingerprintService:
    """Service for device fingerprinting."""
    
    @staticmethod
    def create_device_fingerprint(user: User, device_data: Dict) -> str:
        """Create a device fingerprint from device data."""
        try:
            # Create a unique device ID from device data
            device_string = f"{device_data.get('user_agent', '')}{device_data.get('ip_address', '')}{device_data.get('screen_resolution', '')}{device_data.get('timezone', '')}"
            device_id = hashlib.sha256(device_string.encode()).hexdigest()
            
            # Create or update device fingerprint
            device_fp, created = DeviceFingerprint.objects.get_or_create(
                device_id=device_id,
                defaults={
                    'user': user,
                    'device_type': device_data.get('device_type', 'browser'),
                    'user_agent': device_data.get('user_agent', ''),
                    'ip_address': device_data.get('ip_address', ''),
                    'location': device_data.get('location', ''),
                }
            )
            
            if not created:
                # Update last used timestamp
                device_fp.last_used = timezone.now()
                device_fp.save()
            
            logger.info(f"Device fingerprint created/updated for user {user.username}")
            return device_id
            
        except Exception as e:
            logger.error(f"Error creating device fingerprint: {str(e)}")
            raise
    
    @staticmethod
    def is_trusted_device(user: User, device_id: str) -> bool:
        """Check if a device is trusted for the user."""
        try:
            device = DeviceFingerprint.objects.filter(
                user=user,
                device_id=device_id,
                is_trusted=True,
                is_active=True
            ).first()
            
            return device is not None
            
        except Exception as e:
            logger.error(f"Error checking trusted device: {str(e)}")
            return False

class FraudDetectionService:
    """Service for fraud detection and risk assessment."""
    
    @staticmethod
    def assess_transfer_risk(transfer: BankTransfer) -> Dict:
        """Assess the risk level of a transfer."""
        try:
            risk_score = 0
            fraud_flags = []
            
            # Check velocity (frequency of transfers)
            velocity_score = FraudDetectionService._check_velocity(transfer.user, transfer.amount)
            risk_score += velocity_score['score']
            fraud_flags.extend(velocity_score['flags'])
            
            # Check amount anomalies
            amount_score = FraudDetectionService._check_amount_anomalies(transfer)
            risk_score += amount_score['score']
            fraud_flags.extend(amount_score['flags'])
            
            # Check recipient anomalies
            recipient_score = FraudDetectionService._check_recipient_anomalies(transfer)
            risk_score += recipient_score['score']
            fraud_flags.extend(recipient_score['flags'])
            
            # Check device/location anomalies
            device_score = FraudDetectionService._check_device_anomalies(transfer)
            risk_score += device_score['score']
            fraud_flags.extend(device_score['flags'])
            
            # Determine risk level
            risk_level = FraudDetectionService._determine_risk_level(risk_score)
            
            # Create fraud detection record
            FraudDetection.objects.create(
                user=transfer.user,
                transfer=transfer,
                fraud_type='comprehensive_check',
                risk_score=risk_score,
                flag=risk_level,
                description=f"Risk assessment: {', '.join(fraud_flags)}"
            )
            
            return {
                'risk_score': risk_score,
                'risk_level': risk_level,
                'fraud_flags': fraud_flags,
                'requires_review': risk_score >= 70,
                'requires_2fa': risk_score >= 50,
                'requires_approval': risk_score >= 80
            }
            
        except Exception as e:
            logger.error(f"Error assessing transfer risk: {str(e)}")
            return {
                'risk_score': 0,
                'risk_level': 'normal',
                'fraud_flags': [],
                'requires_review': False,
                'requires_2fa': False,
                'requires_approval': False
            }
    
    @staticmethod
    def _check_velocity(user: User, amount) -> Dict:
        """Check transfer velocity (frequency and amount)."""
        try:
            now = timezone.now()
            hour_ago = now - timedelta(hours=1)
            day_ago = now - timedelta(days=1)
            
            # Check hourly velocity
            hourly_transfers = BankTransfer.objects.filter(
                user=user,
                created_at__gte=hour_ago
            )
            hourly_count = hourly_transfers.count()
            hourly_amount = hourly_transfers.aggregate(total=Sum('amount'))['total'] or 0
            
            # Check daily velocity
            daily_transfers = BankTransfer.objects.filter(
                user=user,
                created_at__gte=day_ago
            )
            daily_count = daily_transfers.count()
            daily_amount = daily_transfers.aggregate(total=Sum('amount'))['total'] or 0
            
            flags = []
            score = 0
            
            # Hourly limits
            if hourly_count > TransferLimits.MAX_TRANSFERS_PER_HOUR:
                flags.append('high_hourly_frequency')
                score += 20
            
            if hourly_amount.amount > TransferLimits.MAX_AMOUNT_PER_HOUR:
                flags.append('high_hourly_amount')
                score += 25
            
            # Daily limits
            if daily_count > TransferLimits.MAX_TRANSFERS_PER_DAY:
                flags.append('high_daily_frequency')
                score += 15
            
            if daily_amount.amount > TransferLimits.MAX_AMOUNT_PER_DAY:
                flags.append('high_daily_amount')
                score += 20
            
            return {'score': score, 'flags': flags}
            
        except Exception as e:
            logger.error(f"Error checking velocity: {str(e)}")
            return {'score': 0, 'flags': []}
    
    @staticmethod
    def _check_amount_anomalies(transfer: BankTransfer) -> Dict:
        """Check for amount anomalies."""
        try:
            flags = []
            score = 0
            
            # Check if amount is unusually high for this user
            user_avg = BankTransfer.objects.filter(
                user=transfer.user,
                status='completed'
            ).aggregate(avg=Sum('amount') / Count('id'))['avg'] or 0
            
            if user_avg > 0 and transfer.amount.amount > user_avg * 5:
                flags.append('unusually_high_amount')
                score += 15
            
            # Check for round amounts (potential fraud indicator)
            if transfer.amount.amount % 10000 == 0 and transfer.amount.amount > 100000:
                flags.append('suspicious_round_amount')
                score += 10
            
            return {'score': score, 'flags': flags}
            
        except Exception as e:
            logger.error(f"Error checking amount anomalies: {str(e)}")
            return {'score': 0, 'flags': []}
    
    @staticmethod
    def _check_recipient_anomalies(transfer: BankTransfer) -> Dict:
        """Check for recipient anomalies."""
        try:
            flags = []
            score = 0
            
            # Check if this is a new recipient
            previous_transfers = BankTransfer.objects.filter(
                user=transfer.user,
                account_number=transfer.account_number,
                status='completed'
            ).count()
            
            if previous_transfers == 0:
                flags.append('new_recipient')
                score += 10
            
            # Check for multiple transfers to same recipient in short time
            recent_transfers = BankTransfer.objects.filter(
                user=transfer.user,
                account_number=transfer.account_number,
                created_at__gte=timezone.now() - timedelta(hours=1)
            ).count()
            
            if recent_transfers > 3:
                flags.append('multiple_transfers_to_same_recipient')
                score += 15
            
            return {'score': score, 'flags': flags}
            
        except Exception as e:
            logger.error(f"Error checking recipient anomalies: {str(e)}")
            return {'score': 0, 'flags': []}
    
    @staticmethod
    def _check_device_anomalies(transfer: BankTransfer) -> Dict:
        """Check for device/location anomalies."""
        try:
            flags = []
            score = 0
            
            # Check if device fingerprint is trusted
            if transfer.device_fingerprint:
                device = DeviceFingerprint.objects.filter(
                    device_id=transfer.device_fingerprint,
                    user=transfer.user
                ).first()
                
                if device and not device.is_trusted:
                    flags.append('untrusted_device')
                    score += 10
            
            # Check IP whitelist
            if transfer.ip_address:
                if not IPWhitelistService.is_ip_allowed(transfer.user, transfer.ip_address):
                    flags.append('ip_not_whitelisted')
                    score += 15
            
            return {'score': score, 'flags': flags}
            
        except Exception as e:
            logger.error(f"Error checking device anomalies: {str(e)}")
            return {'score': 0, 'flags': []}
    
    @staticmethod
    def _determine_risk_level(risk_score: int) -> str:
        """Determine risk level based on score."""
        if risk_score >= 80:
            return FraudFlag.HIGH_RISK
        elif risk_score >= 50:
            return FraudFlag.SUSPICIOUS
        else:
            return FraudFlag.NORMAL

class SecurityAlertService:
    """Service for creating and managing security alerts."""
    
    @staticmethod
    def create_alert(user: User, alert_type: str, severity: str, title: str, message: str, **kwargs) -> SecurityAlert:
        """Create a security alert."""
        try:
            alert = SecurityAlert.objects.create(
                user=user,
                alert_type=alert_type,
                severity=severity,
                title=title,
                message=message,
                ip_address=kwargs.get('ip_address'),
                user_agent=kwargs.get('user_agent'),
                location=kwargs.get('location')
            )
            
            logger.info(f"Security alert created for user {user.username}: {title}")
            return alert
            
        except Exception as e:
            logger.error(f"Error creating security alert: {str(e)}")
            raise
    
    @staticmethod
    def alert_suspicious_activity(transfer: BankTransfer, risk_assessment: Dict) -> None:
        """Create alerts for suspicious activity."""
        try:
            if risk_assessment['risk_score'] >= 70:
                SecurityAlertService.create_alert(
                    user=transfer.user,
                    alert_type='suspicious_activity',
                    severity=SecurityLevel.HIGH,
                    title='Suspicious Transfer Activity Detected',
                    message=f'Your transfer of {transfer.amount} has been flagged for review due to suspicious activity.',
                    ip_address=transfer.ip_address,
                    user_agent=transfer.user_agent
                )
            
            if risk_assessment['risk_score'] >= 50:
                SecurityAlertService.create_alert(
                    user=transfer.user,
                    alert_type='two_fa_required',
                    severity=SecurityLevel.MEDIUM,
                    title='Two-Factor Authentication Required',
                    message='Your transfer requires additional verification. Please complete 2FA.',
                    ip_address=transfer.ip_address,
                    user_agent=transfer.user_agent
                )
                
        except Exception as e:
            logger.error(f"Error creating suspicious activity alert: {str(e)}")

class TransferLimitService:
    """Service for managing transfer limits."""
    
    @staticmethod
    def check_transfer_limits(user: User, amount) -> Dict:
        """Check if a transfer is within limits."""
        try:
            limits = TransferLimit.objects.filter(user=user, is_active=True)
            
            for limit in limits:
                if limit.limit_type == 'daily':
                    daily_total = BankTransfer.objects.filter(
                        user=user,
                        created_at__date=timezone.now().date(),
                        status__in=['completed', 'pending']
                    ).aggregate(total=Sum('amount'))['total'] or 0
                    
                    if daily_total + amount > limit.amount_limit:
                        return {
                            'within_limits': False,
                            'limit_type': 'daily',
                            'current_total': daily_total,
                            'limit': limit.amount_limit,
                            'excess': (daily_total + amount) - limit.amount_limit
                        }
                
                elif limit.limit_type == 'per_transaction':
                    if amount > limit.amount_limit:
                        return {
                            'within_limits': False,
                            'limit_type': 'per_transaction',
                            'amount': amount,
                            'limit': limit.amount_limit,
                            'excess': amount - limit.amount_limit
                        }
            
            return {'within_limits': True}
            
        except Exception as e:
            logger.error(f"Error checking transfer limits: {str(e)}")
            return {'within_limits': True}  # Default to allowing if error
    
    @staticmethod
    def get_user_limits(user: User) -> Dict:
        """Get all limits for a user."""
        try:
            limits = TransferLimit.objects.filter(user=user, is_active=True)
            
            limit_data = {}
            for limit in limits:
                limit_data[limit.limit_type] = {
                    'amount_limit': limit.amount_limit,
                    'count_limit': limit.count_limit
                }
            
            return limit_data
            
        except Exception as e:
            logger.error(f"Error getting user limits: {str(e)}")
            return {} 


class LargeTransactionShieldService:
    """Large Transaction Shield enforcement with thresholds and face fallback."""

    @staticmethod
    def _is_app_initiated(transfer: BankTransfer) -> bool:
        return NightGuardService._is_app_initiated(transfer)

    @staticmethod
    def _exceeds_thresholds(user: User, amount) -> bool:
        try:
            settings_obj = LargeTransactionShieldSettings.objects.get(user=user)
        except LargeTransactionShieldSettings.DoesNotExist:
            return False
        if not settings_obj.enabled:
            return False

        amount_value = float(amount.amount) if hasattr(amount, 'amount') else float(amount)

        # Per-transaction limit
        if settings_obj.per_transaction_limit is not None:
            if amount_value > float(settings_obj.per_transaction_limit):
                return True

        # Daily aggregate
        if settings_obj.daily_limit is not None:
            day_total = BankTransfer.objects.filter(
                user=user,
                status='completed',
                created_at__date=timezone.now().date()
            ).aggregate(total=Sum('amount'))['total'] or 0
            try:
                day_total_val = float(day_total.amount) if hasattr(day_total, 'amount') else float(day_total)
            except Exception:
                day_total_val = 0
            if day_total_val + amount_value > float(settings_obj.daily_limit):
                return True

        # Monthly aggregate
        if settings_obj.monthly_limit is not None:
            start_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_total = BankTransfer.objects.filter(
                user=user,
                status='completed',
                created_at__gte=start_month
            ).aggregate(total=Sum('amount'))['total'] or 0
            try:
                month_total_val = float(month_total.amount) if hasattr(month_total, 'amount') else float(month_total)
            except Exception:
                month_total_val = 0
            if month_total_val + amount_value > float(settings_obj.monthly_limit):
                return True

        return False

    @staticmethod
    def apply_shield(transfer: BankTransfer) -> dict:
        try:
            if not LargeTransactionShieldService._is_app_initiated(transfer):
                return {'required': False}
            if not LargeTransactionShieldService._exceeds_thresholds(transfer.user, transfer.amount):
                return {'required': False}

            # Require face verification first, then fallback (2FA/PIN)
            transfer.requires_2fa = True
            metadata = transfer.metadata or {}
            try:
                settings_obj = LargeTransactionShieldSettings.objects.get(user=transfer.user)
                face_enrolled = bool(settings_obj.face_template_hash)
            except LargeTransactionShieldSettings.DoesNotExist:
                face_enrolled = False
            metadata.update({
                'large_tx_shield_required': True,
                'large_tx_shield_status': metadata.get('large_tx_shield_status', 'pending'),
                'large_tx_face_enrolled': face_enrolled,
            })
            transfer.metadata = metadata
            transfer.save(update_fields=['requires_2fa', 'metadata', 'updated_at'])
            return {'required': True}
        except Exception as e:
            logger.error(f"Error applying Large Transaction Shield: {str(e)}")
            return {'required': False, 'error': str(e)}

    @staticmethod
    def enroll_face(user: User, face_bytes: bytes, algorithm: str = 'sha256') -> bool:
        try:
            import hashlib
            settings_obj, _ = LargeTransactionShieldSettings.objects.get_or_create(user=user)
            if algorithm.lower() != 'sha256':
                algorithm = 'sha256'
            settings_obj.face_template_alg = algorithm
            settings_obj.face_template_hash = hashlib.sha256(face_bytes).hexdigest()
            settings_obj.face_registered_at = timezone.now()
            settings_obj.enabled = True if settings_obj.enabled else False
            settings_obj.save(update_fields=['face_template_alg', 'face_template_hash', 'face_registered_at', 'enabled', 'updated_at'])
            return True
        except Exception as e:
            logger.error(f"Error enrolling LTS face: {str(e)}")
            return False

    @staticmethod
    def verify_face(user: User, face_bytes: bytes) -> bool:
        try:
            import hashlib
            settings_obj = LargeTransactionShieldSettings.objects.get(user=user)
            if not settings_obj.face_template_hash:
                return False
            sample_hash = hashlib.sha256(face_bytes).hexdigest()
            return sample_hash == settings_obj.face_template_hash
        except LargeTransactionShieldSettings.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Error verifying LTS face: {str(e)}")
            return False


class LocationGuardService:
    """Location Guard enforcement based on usual states list and face fallback."""

    @staticmethod
    def _is_app_initiated(transfer: BankTransfer) -> bool:
        return NightGuardService._is_app_initiated(transfer)

    @staticmethod
    def _out_of_allowed_state(user: User, location_data: dict) -> bool:
        try:
            settings_obj = LocationGuardSettings.objects.get(user=user)
        except LocationGuardSettings.DoesNotExist:
            return False
        if not settings_obj.enabled:
            return False
        if not location_data:
            return False
        current_state = (location_data.get('state') or '').strip().lower()
        if not current_state:
            return False
        allowed = [str(s).strip().lower() for s in (settings_obj.allowed_states or [])]
        return current_state not in allowed

    @staticmethod
    def apply_guard(transfer: BankTransfer) -> dict:
        try:
            if not LocationGuardService._is_app_initiated(transfer):
                return {'required': False}
            location_data = transfer.location_data or {}

            # IP geolocation cross-check
            ip_state = None
            try:
                ip_state = LocationGuardService._get_state_from_ip(transfer.ip_address)
            except Exception:
                ip_state = None

            client_state = (location_data.get('state') or '').strip().lower()
            mismatch = bool(ip_state and client_state and (ip_state != client_state))

            if not LocationGuardService._out_of_allowed_state(transfer.user, location_data) and not mismatch:
                return {'required': False}

            transfer.requires_2fa = True
            metadata = transfer.metadata or {}
            try:
                settings_obj = LocationGuardSettings.objects.get(user=transfer.user)
                face_enrolled = bool(settings_obj.face_template_hash)
            except LocationGuardSettings.DoesNotExist:
                face_enrolled = False
            metadata.update({
                'location_guard_required': True,
                'location_guard_status': metadata.get('location_guard_status', 'pending'),
                'location_guard_face_enrolled': face_enrolled,
                'location_ip_state': ip_state,
                'location_client_state': client_state,
                'location_state_mismatch': mismatch,
            })
            transfer.metadata = metadata
            transfer.save(update_fields=['requires_2fa', 'metadata', 'updated_at'])
            return {'required': True}
        except Exception as e:
            logger.error(f"Error applying Location Guard: {str(e)}")
            return {'required': False, 'error': str(e)}

    @staticmethod
    def _get_state_from_ip(ip_address: str) -> str:
        """Best-effort IP geolocation to state. Returns lowercase state or ''."""
        if not ip_address:
            return ''
        try:
            import geoip2.database
            db_path = getattr(settings, 'GEOIP2_CITY_DB', 'GeoLite2-City.mmdb')
            reader = geoip2.database.Reader(db_path)
            resp = reader.city(ip_address)
            admin_name = resp.subdivisions.most_specific.name or ''
            return admin_name.strip().lower()
        except Exception:
            return ''


class FaceChallengeService:
    """Server-issued nonce for face verification to mitigate replay."""

    @staticmethod
    def _now():
        return timezone.now()

    @staticmethod
    def generate(transfer: BankTransfer, feature_key: str, ttl_seconds: int = 300) -> dict:
        try:
            nonce = secrets.token_urlsafe(24)
            expires = FaceChallengeService._now() + timezone.timedelta(seconds=ttl_seconds)
            metadata = transfer.metadata or {}
            metadata[f'{feature_key}_challenge'] = nonce
            metadata[f'{feature_key}_challenge_expires_at'] = expires.isoformat()
            transfer.metadata = metadata
            transfer.save(update_fields=['metadata', 'updated_at'])
            return {'challenge': nonce, 'expires_at': expires.isoformat()}
        except Exception as e:
            logger.error(f"Error generating face challenge: {str(e)}")
            return {'error': 'challenge_generation_failed'}

    @staticmethod
    def validate(transfer: BankTransfer, feature_key: str, provided: str) -> bool:
        try:
            metadata = transfer.metadata or {}
            expected = metadata.get(f'{feature_key}_challenge')
            expires_at = metadata.get(f'{feature_key}_challenge_expires_at')
            if not expected or not expires_at:
                return False
            if provided != expected:
                return False
            try:
                exp_dt = timezone.datetime.fromisoformat(expires_at)
            except Exception:
                return False
            return FaceChallengeService._now() <= exp_dt
        except Exception:
            return False

    @staticmethod
    def enroll_face(user: User, face_bytes: bytes, algorithm: str = 'sha256') -> bool:
        try:
            import hashlib
            settings_obj, _ = LocationGuardSettings.objects.get_or_create(user=user)
            if algorithm.lower() != 'sha256':
                algorithm = 'sha256'
            settings_obj.face_template_alg = algorithm
            settings_obj.face_template_hash = hashlib.sha256(face_bytes).hexdigest()
            settings_obj.face_registered_at = timezone.now()
            settings_obj.enabled = True if settings_obj.enabled else False
            settings_obj.save(update_fields=['face_template_alg', 'face_template_hash', 'face_registered_at', 'enabled', 'updated_at'])
            return True
        except Exception as e:
            logger.error(f"Error enrolling Location Guard face: {str(e)}")
            return False

    @staticmethod
    def verify_face(user: User, face_bytes: bytes) -> bool:
        try:
            import hashlib
            settings_obj = LocationGuardSettings.objects.get(user=user)
            if not settings_obj.face_template_hash:
                return False
            sample_hash = hashlib.sha256(face_bytes).hexdigest()
            return sample_hash == settings_obj.face_template_hash
        except LocationGuardSettings.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Error verifying Location Guard face: {str(e)}")
            return False


class NightGuardService:
    """Night Guard enforcement for app-initiated transfers during configured hours."""

    @staticmethod
    def _is_app_initiated(transfer: BankTransfer) -> bool:
        try:
            # Explicit channel/source in metadata takes priority
            source = (transfer.metadata or {}).get('source') or (transfer.metadata or {}).get('channel')
            if source and str(source).lower() in {'app', 'mobile_app', 'mobile'}:
                return True
            # Heuristic: presence of user_agent/device_fingerprint and not scheduled/bulk
            if transfer.user_agent or transfer.device_fingerprint:
                if not transfer.is_scheduled and not transfer.is_bulk:
                    return True
            return False
        except Exception:
            return False

    @staticmethod
    def _within_window(start_time, end_time, now_time) -> bool:
        """Check if now_time lies within [start_time, end_time], supporting cross-midnight windows."""
        if not start_time or not end_time:
            return False
        if start_time <= end_time:
            # Same-day window, e.g., 21:00-23:00
            return start_time <= now_time <= end_time
        # Cross-midnight window, e.g., 22:00-05:00
        return now_time >= start_time or now_time <= end_time

    @staticmethod
    def is_active_for_user(user) -> bool:
        try:
            settings_obj = NightGuardSettings.objects.get(user=user)
            return bool(settings_obj.enabled)
        except NightGuardSettings.DoesNotExist:
            return False

    @staticmethod
    def apply_night_guard(transfer: BankTransfer) -> dict:
        """Mark transfer as requiring stricter verification if within Guard hours.

        Returns a dict with required flag and details. Does not perform face verification
        itself; that should be handled by the client/app. If required, we set transfer
        flags so upstream flows can request verification before proceeding.
        """
        try:
            if not NightGuardService._is_app_initiated(transfer):
                return {'required': False}

            try:
                settings_obj = NightGuardSettings.objects.get(user=transfer.user)
            except NightGuardSettings.DoesNotExist:
                return {'required': False}

            if not settings_obj.enabled:
                return {'required': False}

            now_time = timezone.now().time()
            if not NightGuardService._within_window(settings_obj.start_time, settings_obj.end_time, now_time):
                return {'required': False}

            # Within Night Guard window -> require face verification first, then fallback
            transfer.requires_2fa = True  # we will rely on 2FA as fallback if face fails
            metadata = transfer.metadata or {}
            metadata.update({
                'night_guard_required': True,
                'night_guard_status': metadata.get('night_guard_status', 'pending'),
                'night_guard_primary': settings_obj.primary_method,
                'night_guard_fallback': settings_obj.fallback_method,
                'night_guard_window': {
                    'start_time': settings_obj.start_time.isoformat() if settings_obj.start_time else None,
                    'end_time': settings_obj.end_time.isoformat() if settings_obj.end_time else None,
                },
                'night_guard_face_enrolled': bool(settings_obj.face_template_hash),
            })
            transfer.metadata = metadata
            transfer.save(update_fields=['requires_2fa', 'metadata', 'updated_at'])

            return {
                'required': True,
                'primary': settings_obj.primary_method,
                'fallback': settings_obj.fallback_method,
            }

        except Exception as e:
            logger.error(f"Error applying Night Guard: {str(e)}")
            return {'required': False, 'error': str(e)}

    @staticmethod
    def mark_face_failed(transfer: BankTransfer) -> None:
        try:
            metadata = transfer.metadata or {}
            metadata['night_guard_status'] = 'face_failed'
            transfer.metadata = metadata
            transfer.save(update_fields=['metadata', 'updated_at'])
        except Exception as e:
            logger.error(f"Error marking face verification failed: {str(e)}")

    @staticmethod
    def enroll_face(user: User, face_bytes: bytes, algorithm: str = 'sha256') -> bool:
        """Enroll a face template by hashing the provided sample (placeholder for real biometrics)."""
        try:
            import hashlib
            settings_obj, _ = NightGuardSettings.objects.get_or_create(user=user)
            if algorithm.lower() != 'sha256':
                algorithm = 'sha256'
            settings_obj.face_template_alg = algorithm
            settings_obj.face_template_hash = hashlib.sha256(face_bytes).hexdigest()
            settings_obj.face_registered_at = timezone.now()
            settings_obj.enabled = True if settings_obj.enabled else False
            settings_obj.save(update_fields=['face_template_alg', 'face_template_hash', 'face_registered_at', 'enabled', 'updated_at'])
            return True
        except Exception as e:
            logger.error(f"Error enrolling Night Guard face: {str(e)}")
            return False

    @staticmethod
    def verify_face(user: User, face_bytes: bytes) -> bool:
        """Verify provided face sample against enrolled template (placeholder hash match)."""
        try:
            import hashlib
            settings_obj = NightGuardSettings.objects.get(user=user)
            if not settings_obj.face_template_hash:
                return False
            sample_hash = hashlib.sha256(face_bytes).hexdigest()
            return sample_hash == settings_obj.face_template_hash
        except NightGuardSettings.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Error verifying Night Guard face: {str(e)}")
            return False
