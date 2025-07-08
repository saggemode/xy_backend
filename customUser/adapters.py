# accounts/adapters.py
from allauth.account.adapter import DefaultAccountAdapter

class CustomAccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        user.full_name = request.data.get('full_name')
        user.phone = request.data.get('phone')
        if commit:
            user.save()
        return user
