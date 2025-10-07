from rest_framework import permissions

class IsManagerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'role', None) in ('manager', 'admin')

class IsOwnerCompanyFlightOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        role = getattr(request.user, 'role', None)
        if role == 'admin':
            return True
        if role == 'manager':
            return getattr(obj.company, "manager_id", None) == request.user.id
        return False
