"""
Pytest configuration and fixtures for the biblioteca project.
"""
import pytest
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import User
from apps.books.models import Book
from apps.loans.models import Loan, Reservation


@pytest.fixture
def librarian_user(db):
    """Create a librarian user for testing."""
    return User.objects.create_user(
        email='librarian@test.com',
        password='testpass123',
        first_name='John',
        last_name='Doe',
        role=User.Role.LIBRARIAN
    )


@pytest.fixture
def library_user(db):
    """Create a library user for testing."""
    return User.objects.create_user(
        email='user@test.com',
        password='testpass123',
        first_name='Jane',
        last_name='Smith',
        role=User.Role.LIBRARY_USER
    )


@pytest.fixture
def another_library_user(db):
    """Create another library user for testing."""
    return User.objects.create_user(
        email='user2@test.com',
        password='testpass123',
        first_name='Bob',
        last_name='Johnson',
        role=User.Role.LIBRARY_USER
    )


@pytest.fixture
def book(db, librarian_user):
    """Create a book for testing."""
    return Book.objects.create(
        title='Test Book',
        author='Test Author',
        isbn='1234567890123',
        description='Test description',
        quantity=5,
        available_quantity=5,
        created_by=librarian_user
    )


@pytest.fixture
def unavailable_book(db, librarian_user):
    """Create a book with no available copies."""
    return Book.objects.create(
        title='Unavailable Book',
        author='Test Author',
        quantity=1,
        available_quantity=0,
        created_by=librarian_user
    )


@pytest.fixture
def reservation(db, book, library_user):
    """Create a reservation for testing."""
    book.available_quantity -= 1
    book.save()

    return Reservation.objects.create(
        book=book,
        user=library_user,
        expires_at=timezone.now() + timedelta(hours=1)
    )


@pytest.fixture
def expired_reservation(db, book, library_user):
    """Create an expired reservation for testing."""
    return Reservation.objects.create(
        book=book,
        user=library_user,
        expires_at=timezone.now() - timedelta(hours=1)
    )


@pytest.fixture
def loan(db, book, library_user):
    """Create a loan for testing."""
    book.available_quantity -= 1
    book.save()

    return Loan.objects.create(
        book=book,
        user=library_user,
        due_date=timezone.now() + timedelta(days=2)
    )


@pytest.fixture
def overdue_loan(db, book, library_user):
    """Create an overdue loan for testing."""
    return Loan.objects.create(
        book=book,
        user=library_user,
        due_date=timezone.now() - timedelta(days=1),
        status=Loan.Status.OVERDUE
    )


@pytest.fixture
def api_client():
    """Create an API client for testing."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, library_user):
    """Create an authenticated API client."""
    api_client.force_authenticate(user=library_user)
    return api_client


@pytest.fixture
def librarian_client(api_client, librarian_user):
    """Create an authenticated API client for librarian."""
    api_client.force_authenticate(user=librarian_user)
    return api_client
