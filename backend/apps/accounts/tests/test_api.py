"""
Tests for the accounts API endpoints.
"""
import pytest
from django.urls import reverse
from rest_framework import status

from apps.accounts.models import User


@pytest.mark.integration
class TestAuthenticationAPI:
    """Test suite for authentication endpoints."""

    def test_register_user(self, api_client):
        """Test user registration."""
        url = reverse('register')
        data = {
            'email': 'newuser@test.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'testpass123',
            'password2': 'testpass123',
            'role': User.Role.LIBRARY_USER
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(email='newuser@test.com').exists()

    def test_register_user_password_mismatch(self, api_client):
        """Test registration with mismatched passwords."""
        url = reverse('register')
        data = {
            'email': 'newuser@test.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'testpass123',
            'password2': 'different456',
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_user(self, api_client, library_user):
        """Test user login."""
        url = reverse('login')
        data = {
            'email': 'user@test.com',
            'password': 'testpass123'
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert 'email' in response.data

    def test_login_invalid_credentials(self, api_client):
        """Test login with invalid credentials."""
        url = reverse('login')
        data = {
            'email': 'invalid@test.com',
            'password': 'wrongpass'
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_logout_user(self, authenticated_client):
        """Test user logout."""
        url = reverse('logout')

        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_200_OK

    def test_get_current_user(self, authenticated_client, library_user):
        """Test getting current user info."""
        url = reverse('current-user')

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == library_user.email

    def test_get_current_user_unauthenticated(self, api_client):
        """Test getting current user when not authenticated."""
        url = reverse('current-user')

        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.integration
class TestUserManagementAPI:
    """Test suite for user management endpoints (librarian only)."""

    def test_list_users_as_librarian(self, librarian_client):
        """Test listing users as librarian."""
        url = reverse('user-list')

        response = librarian_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data

    def test_list_users_as_regular_user(self, authenticated_client):
        """Test that regular users cannot list all users."""
        url = reverse('user-list')

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_user_as_librarian(self, librarian_client, library_user):
        """Test retrieving user details as librarian."""
        url = reverse('user-detail', args=[library_user.id])

        response = librarian_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == library_user.email
