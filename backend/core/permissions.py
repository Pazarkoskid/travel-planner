from rest_framework.permissions import BasePermission


def is_admin(user):
    return bool(user and user.is_authenticated and (user.is_superuser or getattr(user, "role", None) == "ADMIN"))


class IsAdminRole(BasePermission):
    message = "Потребна е администраторска улога."

    def has_permission(self, request, view):
        return is_admin(request.user)


class IsBusinessRole(BasePermission):
    message = "Потребна е улога сопственик/оператор."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.role == "BUSINESS" or is_admin(u)))
