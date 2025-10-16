"""
Tests for the loan-related models.
"""
import pytest
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.loans.models import Loan, LoanTransfer, Reservation


@pytest.mark.unit
class TestReservationModel:
    """Test suite for Reservation model."""

    def test_create_reservation(self, reservation):
        """Test creating a reservation."""
        assert reservation.book.title == 'Test Book'
        assert reservation.status == Reservation.Status.ACTIVE
        assert reservation.expires_at > timezone.now()

    def test_reservation_str_representation(self, reservation):
        """Test string representation of reservation."""
        assert 'Reservation' in str(reservation)
        assert reservation.book.title in str(reservation)

    def test_is_expired_property(self, reservation, expired_reservation):
        """Test is_expired property."""
        assert not reservation.is_expired
        assert expired_reservation.is_expired

    def test_remaining_time_property(self, reservation):
        """Test remaining_time property."""
        remaining = reservation.remaining_time
        assert remaining > timedelta(0)
        assert remaining <= timedelta(hours=1)

    def test_remaining_time_for_expired(self, expired_reservation):
        """Test remaining_time for expired reservation."""
        assert expired_reservation.remaining_time == timedelta(0)

    def test_expire_fsm_transition(self, reservation):
        """Test expire FSM transition."""
        initial_quantity = reservation.book.available_quantity

        # Set reservation to expired time to allow FSM transition
        reservation.expires_at = timezone.now() - timedelta(minutes=1)
        reservation.save()

        reservation.expire()
        reservation.save()

        assert reservation.status == Reservation.Status.EXPIRED
        reservation.book.refresh_from_db()
        assert reservation.book.available_quantity == initial_quantity + 1

    def test_auto_set_expires_at(self, book, library_user):
        """Test that expires_at is auto-set if not provided."""
        reservation = Reservation.objects.create(
            book=book,
            user=library_user
        )

        assert reservation.expires_at is not None
        expected_time = timezone.now() + timedelta(hours=1)
        time_diff = abs((reservation.expires_at - expected_time).total_seconds())
        assert time_diff < 5  # Within 5 seconds


@pytest.mark.unit
class TestLoanModel:
    """Test suite for Loan model."""

    def test_create_loan(self, loan):
        """Test creating a loan."""
        assert loan.book.title == 'Test Book'
        assert loan.status == Loan.Status.ACTIVE
        assert loan.due_date > timezone.now()

    def test_loan_str_representation(self, loan):
        """Test string representation of loan."""
        assert 'Loan' in str(loan)
        assert loan.book.title in str(loan)

    def test_is_overdue_property(self, loan, overdue_loan):
        """Test is_overdue property."""
        assert not loan.is_overdue
        assert overdue_loan.is_overdue

    def test_remaining_time_property(self, loan):
        """Test remaining_time property."""
        remaining = loan.remaining_time
        assert remaining > timedelta(0)
        assert remaining <= timedelta(days=2)

    def test_return_loan_fsm_transition(self, loan):
        """Test return_loan FSM transition."""
        initial_quantity = loan.book.available_quantity

        loan.return_loan()
        loan.save()

        assert loan.status == Loan.Status.RETURNED
        assert loan.returned_at is not None
        loan.book.refresh_from_db()
        assert loan.book.available_quantity == initial_quantity + 1

    def test_mark_overdue_fsm_transition(self, loan):
        """Test mark_overdue FSM transition."""
        # Manually set due date to past to allow FSM transition
        loan.due_date = timezone.now() - timedelta(days=1)
        loan.save()

        loan.mark_overdue()
        loan.save()

        assert loan.status == Loan.Status.OVERDUE

    def test_auto_set_due_date(self, book, library_user):
        """Test that due_date is auto-set if not provided."""
        loan = Loan.objects.create(
            book=book,
            user=library_user
        )

        assert loan.due_date is not None
        expected_time = timezone.now() + timedelta(days=2)
        time_diff = abs((loan.due_date - expected_time).total_seconds())
        assert time_diff < 5  # Within 5 seconds


@pytest.mark.unit
class TestLoanTransferModel:
    """Test suite for LoanTransfer model."""

    def test_create_loan_transfer(self, loan, another_library_user):
        """Test creating a loan transfer."""
        transfer = LoanTransfer.objects.create(
            loan=loan,
            from_user=loan.user,
            to_user=another_library_user
        )

        assert transfer.loan == loan
        assert transfer.from_user == loan.user
        assert transfer.to_user == another_library_user
        assert transfer.accepted

    def test_loan_transfer_str_representation(self, loan, another_library_user):
        """Test string representation of loan transfer."""
        transfer = LoanTransfer.objects.create(
            loan=loan,
            from_user=loan.user,
            to_user=another_library_user
        )

        assert 'Transfer' in str(transfer)

    def test_transfer_validation_same_user(self, loan):
        """Test that transfer to same user is not allowed."""
        transfer = LoanTransfer(
            loan=loan,
            from_user=loan.user,
            to_user=loan.user
        )

        with pytest.raises(ValidationError):
            transfer.save()
