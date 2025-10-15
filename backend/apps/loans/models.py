"""
Loan-related models for the biblioteca application.
"""
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.books.models import Book


class Reservation(models.Model):
    """
    Reservation model representing a book reservation.
    Reservations last for 1 hour and can be converted to loans.
    """

    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        EXPIRED = 'expired', _('Expired')
        CONVERTED_TO_LOAN = 'converted_to_loan', _('Converted to Loan')
        CANCELLED = 'cancelled', _('Cancelled')

    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='reservations',
        help_text=_('Book being reserved')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reservations',
        help_text=_('User who made the reservation')
    )
    reserved_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_('When the reservation was made')
    )
    expires_at = models.DateTimeField(
        help_text=_('When the reservation expires')
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        help_text=_('Current status of the reservation')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reservations'
        verbose_name = _('reservation')
        verbose_name_plural = _('reservations')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['book', 'status']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"Reservation #{self.id}: {self.book.title} by {self.user.email}"

    def save(self, *args, **kwargs):
        """Set expiration time if not provided (1 hour from reservation)."""
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=1)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        """Check if the reservation has expired."""
        if self.status != self.Status.ACTIVE:
            return False
        return timezone.now() > self.expires_at

    @property
    def remaining_time(self):
        """Calculate remaining time before expiration."""
        if self.is_expired or self.status != self.Status.ACTIVE:
            return timedelta(0)
        return self.expires_at - timezone.now()

    def mark_as_expired(self):
        """Mark reservation as expired and restore book availability."""
        if self.status == self.Status.ACTIVE:
            self.status = self.Status.EXPIRED
            self.save()
            # Restore book availability
            self.book.available_quantity += 1
            self.book.save()


class Loan(models.Model):
    """
    Loan model representing a book loan.
    Loans last for 2 days and can be transferred between users.
    """

    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        RETURNED = 'returned', _('Returned')
        OVERDUE = 'overdue', _('Overdue')

    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='loans',
        help_text=_('Book being loaned')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='loans',
        help_text=_('Current user who has the book')
    )
    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='loans',
        help_text=_('Reservation that was converted to this loan (if any)')
    )
    borrowed_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_('When the book was borrowed')
    )
    due_date = models.DateTimeField(
        help_text=_('When the book should be returned')
    )
    returned_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the book was returned')
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        help_text=_('Current status of the loan')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loans'
        verbose_name = _('loan')
        verbose_name_plural = _('loans')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['book', 'status']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return f"Loan #{self.id}: {self.book.title} by {self.user.email}"

    def save(self, *args, **kwargs):
        """Set due date if not provided (2 days from borrowing)."""
        if not self.due_date:
            self.due_date = timezone.now() + timedelta(days=2)
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        """Check if the loan is overdue."""
        if self.status == self.Status.RETURNED:
            return False
        return timezone.now() > self.due_date

    @property
    def remaining_time(self):
        """Calculate remaining time before due date."""
        if self.status == self.Status.RETURNED:
            return timedelta(0)
        remaining = self.due_date - timezone.now()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)

    def return_book(self):
        """Mark loan as returned and restore book availability."""
        if self.status == self.Status.ACTIVE or self.status == self.Status.OVERDUE:
            self.status = self.Status.RETURNED
            self.returned_at = timezone.now()
            self.save()
            # Restore book availability
            self.book.available_quantity += 1
            self.book.save()

    def mark_as_overdue(self):
        """Mark loan as overdue."""
        if self.status == self.Status.ACTIVE and self.is_overdue:
            self.status = self.Status.OVERDUE
            self.save()


class LoanTransfer(models.Model):
    """
    LoanTransfer model representing the transfer of a loan from one user to another.
    Keeps track of loan ownership history.
    """

    loan = models.ForeignKey(
        Loan,
        on_delete=models.CASCADE,
        related_name='transfers',
        help_text=_('Loan being transferred')
    )
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='loan_transfers_sent',
        help_text=_('User who is transferring the loan')
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='loan_transfers_received',
        help_text=_('User who is receiving the loan')
    )
    transferred_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_('When the transfer occurred')
    )
    accepted = models.BooleanField(
        default=True,
        help_text=_('Whether the transfer was accepted')
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'loan_transfers'
        verbose_name = _('loan transfer')
        verbose_name_plural = _('loan transfers')
        ordering = ['-transferred_at']
        indexes = [
            models.Index(fields=['loan']),
            models.Index(fields=['from_user']),
            models.Index(fields=['to_user']),
        ]

    def __str__(self):
        return f"Transfer #{self.id}: Loan {self.loan.id} from {self.from_user.email} to {self.to_user.email}"

    def clean(self):
        """Validate that from_user and to_user are different."""
        if self.from_user == self.to_user:
            raise ValidationError(_('Cannot transfer loan to the same user.'))

    def save(self, *args, **kwargs):
        """Override save to run clean validation."""
        self.full_clean()
        super().save(*args, **kwargs)
