"""
Tests for the User model.
"""
import pytest
from django.db import IntegrityError

from apps.accounts.models import User


@pytest.mark.unit
class TestUserModel:
    """Test suite for User model."""

    def test_create_user(self, db):
        """Test creating a user."""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

        assert user.email == 'test@example.com'
        assert user.first_name == 'Test'
        assert user.last_name == 'User'
        assert user.role == User.Role.LIBRARY_USER
        assert user.check_password('testpass123')
        assert user.is_active
        assert not user.is_staff

    def test_create_librarian(self, db):
        """Test creating a librarian user."""
        user = User.objects.create_user(
            email='librarian@example.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            role=User.Role.LIBRARIAN
        )

        assert user.email == 'librarian@example.com'
        assert user.role == User.Role.LIBRARIAN
        assert user.is_librarian
        assert not user.is_library_user

    def test_user_str_representation(self, library_user):
        """Test string representation of user."""
        assert str(library_user) == 'user@test.com (Library User)'

    def test_user_full_name(self, library_user):
        """Test full_name property."""
        assert library_user.full_name == 'Jane Smith'

    def test_user_full_name_with_no_name(self, db):
        """Test full_name property when no name is provided."""
        user = User.objects.create_user(
            email='noname@example.com',
            password='testpass123'
        )
        assert user.full_name == 'noname@example.com'

    def test_is_librarian_property(self, librarian_user, library_user):
        """Test is_librarian property."""
        assert librarian_user.is_librarian
        assert not library_user.is_librarian

    def test_is_library_user_property(self, librarian_user, library_user):
        """Test is_library_user property."""
        assert not librarian_user.is_library_user
        assert library_user.is_library_user

    def test_unique_email_constraint(self, db):
        """Test that email must be unique."""
        User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

        with pytest.raises(IntegrityError):
            User.objects.create_user(
                email='test@example.com',
                password='testpass456'
            )

    def test_email_is_username_field(self, db):
        """Test that email is the username field."""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

        assert User.USERNAME_FIELD == 'email'
        assert user.username is None
