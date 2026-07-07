from rest_framework.permissions import BasePermission

class IsAdminOrReadOnly(BasePermission):
    """
    This allows full access to the admins (is_staff=True)
    Allows read-only access (GET) to anyone else who's authenticated
    """
    def has_permission(self, request, view):
        #safe methods = GET, HEAD, OPTIONS (these are allowed for everyone)
        if request.method in ['GET', 'HEAD', 'OPTION']:
            return True
        return request.user and request.user.is_staff
    

class IsAdminOnly(BasePermission):
    """
    Only allows access to admins. No read-only exception
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_staff
