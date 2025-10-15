"""
Custom permissions for the biblioteca application.
"""
from rest_framework import permissions


class IsLibrarian(permissions.BasePermission):
    """
    Permission to only allow librarians to access the view.
    """

    message = 'Only librarians can perform this action.'

    def has_permission(self, request, view):
        """Check if user is authenticated and is a librarian."""
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_librarian
        )


class IsLibraryUser(permissions.BasePermission):
    """
    Permission to only allow library users to access the view.
    """

    message = 'Only library users can perform this action.'

    def has_permission(self, request, view):
        """Check if user is authenticated and is a library user."""
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_library_user
        )


class IsLibrarianOrReadOnly(permissions.BasePermission):
    """
    Permission to allow read access to everyone, but write access only to librarians.
    """

    def has_permission(self, request, view):
        """Check if request is safe method or user is librarian."""
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_librarian
        )


class IsOwnerOrLibrarian(permissions.BasePermission):
    """
    Permission to only allow owners of an object or librarians to access it.
    """

    def has_object_permission(self, request, view, obj):
        """Check if user is owner or librarian."""
        # Librarians can access everything
        if request.user.is_librarian:
            return True

        # Check if object has a user field
        if hasattr(obj, 'user'):
            return obj.user == request.user

        return False
