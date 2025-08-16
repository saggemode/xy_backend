import phonenumbers
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

def normalize_phone(phone, default_region='NG'):
    try:
        if phone.startswith('+'):
            parsed = phonenumbers.parse(phone, None)
        else:
            parsed = phonenumbers.parse(phone, default_region)
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        return phone

class UsernameEmailPhoneBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        user = None
        # Try to get country from request.POST or fallback to NG
        default_region = 'NG'
        if request:
            country = request.POST.get('country') or request.GET.get('country')
            if country and len(country) == 2:
                default_region = country.upper()
        phone = normalize_phone(username, default_region=default_region)
        try:
            user = User.objects.get(
                Q(username__iexact=username) |
                Q(email__iexact=username) |
                Q(profile__phone__iexact=phone)
            )
        except User.DoesNotExist:
            return None
        if user.check_password(password):
            return user
        return None 