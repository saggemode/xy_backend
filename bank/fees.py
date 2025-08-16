from decimal import Decimal
import math
# VATCharge/TransferChargeControl models are not available; implement safe defaults
from typing import Optional

class _ChargeControl:
    def __init__(self, levy_active=True, vat_active=True, fee_active=True):
        self.levy_active = levy_active
        self.vat_active = vat_active
        self.fee_active = fee_active

def _get_db_charge_control() -> Optional[_ChargeControl]:
    try:
        from .models import TransferChargeControl  # type: ignore
        obj = TransferChargeControl.objects.order_by('-updated_at').first()
        return obj
    except Exception:
        return None

LEVY_THRESHOLD = Decimal('10000')
LEVY_AMOUNT = Decimal('50')

def get_charge_control():
    return _get_db_charge_control() or _ChargeControl()

def get_active_vat_rate():
    try:
        from .models import VATCharge  # type: ignore
        vat = VATCharge.objects.filter(active=True).order_by('-updated_at').first()
        return vat.rate if vat else Decimal('0.075')
    except Exception:
        return Decimal('0.075')

def calculate_transfer_fees(amount, transfer_type='intra'):
    amount = Decimal(amount)
    vat_rate = get_active_vat_rate()
    charge_control = get_charge_control()
    levy_active = charge_control.levy_active if charge_control else True
    vat_active = charge_control.vat_active if charge_control else True
    fee_active = charge_control.fee_active if charge_control else True

    if transfer_type == 'intra':
        fee = Decimal('0.00')
        vat = amount * vat_rate if vat_active else Decimal('0.00')
    else:
        if not fee_active:
            fee = Decimal('0.00')
        elif amount <= 5000:
            fee = Decimal('10.00')
        elif amount <= 50000:
            fee = Decimal('25.00')
        else:
            fee = Decimal('50.00')
        vat = fee * vat_rate if vat_active else Decimal('0.00')

    if levy_active and amount >= LEVY_THRESHOLD:
        blocks = math.ceil(float(amount) / float(LEVY_THRESHOLD))
        levy = LEVY_AMOUNT * blocks
    else:
        levy = Decimal('0.00')
    return (fee, vat, levy) 