"""
Tests for the loans API endpoints.
"""
import pytest
from django.urls import reverse
from rest_framework import status

from apps.loans.models import Loan, Reservation


@pytest.mark.integration
class TestReservationAPI:
    """Test suite for reservation endpoints."""

    def test_list_my_reservations(self, authenticated_client, reservation):
        """Test listing own reservations."""
        url = reverse('reservation-list')

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_create_reservation(self, authenticated_client, book):
        """Test creating a reservation."""
        url = reverse('reservation-list')
        data = {'book': book.id}

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert Reservation.objects.filter(
            user=authenticated_client.handler._force_user,
            book=book
        ).exists()

    def test_create_reservation_unavailable_book(self, authenticated_client, unavailable_book):
        """Test creating reservation for unavailable book."""
        url = reverse('reservation-list')
        data = {'book': unavailable_book.id}

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cancel_reservation(self, authenticated_client, reservation):
        """Test cancelling a reservation."""
        url = reverse('reservation-detail', args=[reservation.id])

        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_200_OK
        reservation.refresh_from_db()
        assert reservation.status == Reservation.Status.CANCELLED

    def test_convert_reservation_to_loan(self, authenticated_client, reservation):
        """Test converting reservation to loan."""
        url = reverse('reservation-convert-to-loan', args=[reservation.id])

        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_201_CREATED
        assert 'id' in response.data
        reservation.refresh_from_db()
        assert reservation.status == Reservation.Status.CONVERTED_TO_LOAN


@pytest.mark.integration
class TestLoanAPI:
    """Test suite for loan endpoints."""

    def test_list_my_loans(self, authenticated_client, loan):
        """Test listing own loans."""
        url = reverse('loan-list')

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_create_loan(self, authenticated_client, book):
        """Test creating a loan."""
        url = reverse('loan-list')
        data = {'book': book.id}

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert Loan.objects.filter(
            user=authenticated_client.handler._force_user,
            book=book
        ).exists()

    def test_create_loan_unavailable_book(self, authenticated_client, unavailable_book):
        """Test creating loan for unavailable book."""
        url = reverse('loan-list')
        data = {'book': unavailable_book.id}

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_return_book(self, authenticated_client, loan):
        """Test returning a book."""
        url = reverse('loan-return-book', args=[loan.id])

        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        loan.refresh_from_db()
        assert loan.status == Loan.Status.RETURNED

    def test_share_loan(self, authenticated_client, loan, another_library_user):
        """Test sharing a loan with another user."""
        url = reverse('loan-share', args=[loan.id])
        data = {'to_user': another_library_user.id}

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        loan.refresh_from_db()
        assert loan.user == another_library_user

    def test_get_active_loans(self, authenticated_client, loan):
        """Test getting active loans."""
        url = reverse('loan-active')

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1


@pytest.mark.integration
class TestLibrarianViews:
    """Test suite for librarian-specific views."""

    def test_librarian_sees_all_reservations(self, librarian_client, reservation):
        """Test that librarian can see all reservations."""
        url = reverse('reservation-list')

        response = librarian_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_librarian_sees_all_loans(self, librarian_client, loan):
        """Test that librarian can see all loans."""
        url = reverse('loan-list')

        response = librarian_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
