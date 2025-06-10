from rest_framework import permissions

class IsStoreStaff(permissions.BasePermission):
    """
    Custom permission to only allow store staff to access inventory.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'store_staff') 