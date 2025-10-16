"""
Loan-related models for the biblioteca application.
"""
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField, transition

from apps.books.models import Book


class Reservation(models.Model):
    """
    Reservation model representing a book reservation.
    Reservations last for 1 hour and can be converted to loans.
    Uses FSM to control state transitions.
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
    status = FSMField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        protected=True,
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

    def can_expire(self):
        """Check if reservation can be expired (time has passed)."""
        return self.is_expired

    def can_cancel(self):
        """Check if reservation can be cancelled."""
        return True

    @transition(field=status, source=Status.ACTIVE, target=Status.EXPIRED,
                conditions=[can_expire],
                custom={'description': 'Mark reservation as expired and restore book availability'})
    def expire(self):
        """Mark reservation as expired and restore book availability."""
        # Restore book availability with validation to prevent exceeding total quantity
        # Use Case/When to ensure we don't exceed quantity
        from django.db.models import Case, When, Value
        Book.objects.filter(id=self.book.id).update(
            available_quantity=Case(
                When(available_quantity__lt=models.F('quantity'),
                     then=models.F('available_quantity') + 1),
                default=models.F('quantity'),
                output_field=models.PositiveIntegerField()
            )
        )

    @transition(field=status, source=Status.ACTIVE, target=Status.CANCELLED,
                conditions=[can_cancel],
                custom={'description': 'Cancel an active reservation'})
    def cancel(self):
        """Cancel reservation and restore book availability."""
        # Restore book availability with validation to prevent exceeding total quantity
        from django.db.models import Case, When
        Book.objects.filter(id=self.book.id).update(
            available_quantity=Case(
                When(available_quantity__lt=models.F('quantity'),
                     then=models.F('available_quantity') + 1),
                default=models.F('quantity'),
                output_field=models.PositiveIntegerField()
            )
        )

    @transition(field=status, source=Status.ACTIVE, target=Status.CONVERTED_TO_LOAN,
                custom={'description': 'Convert reservation to a loan'})
    def convert_to_loan(self):
        """Mark reservation as converted to loan."""
        # Book availability is not restored as it's converted to a loan
        pass


class Loan(models.Model):
    """
    Loan model representing a book loan.
    Loans last for 2 days and can be transferred between users.
    Uses FSM to control state transitions.
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
    status = FSMField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        protected=True,
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
        """Set due date if not provided (2 days from borrowing) and schedule in Redis."""
        is_new = self.pk is None
        due_date_changed = False

        if not self.due_date:
            self.due_date = timezone.now() + timedelta(days=2)
            due_date_changed = True
        elif 'update_fields' in kwargs and 'due_date' in kwargs.get('update_fields', []):
            due_date_changed = True

        super().save(*args, **kwargs)

        # Schedule in Redis after saving (so we have pk)
        # Only schedule if status is ACTIVE
        if self.status == self.Status.ACTIVE and (is_new or due_date_changed):
            try:
                from .redis_scheduler import LoanScheduler
                scheduler = LoanScheduler()
                if is_new:
                    scheduler.schedule_loan(self.pk, self.due_date)
                else:
                    scheduler.reschedule_loan(self.pk, self.due_date)
            except Exception as e:
                # Don't fail the save if Redis is unavailable
                # The sync task will fix inconsistencies
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to schedule loan {self.pk} in Redis: {e}")

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

    @property
    def has_pending_transfer(self):
        """Check if loan has a pending transfer."""
        return self.transfers.filter(status='pending').exists()

    @property
    def pending_transfer(self):
        """Get the pending transfer if exists."""
        return self.transfers.filter(status='pending').first()

    def can_mark_overdue(self):
        """Check if loan can be marked as overdue (due date has passed)."""
        return self.is_overdue

    def can_return(self):
        """Check if loan can be returned."""
        return True

    @transition(field=status, source=Status.ACTIVE, target=Status.OVERDUE,
                conditions=[can_mark_overdue],
                custom={'description': 'Mark loan as overdue when due date has passed'})
    def mark_overdue(self):
        """Mark loan as overdue."""
        # No additional actions needed, just state change
        pass

    @transition(field=status, source=[Status.ACTIVE, Status.OVERDUE], target=Status.RETURNED,
                conditions=[can_return],
                custom={'description': 'Return the book and restore availability'})
    def return_loan(self):
        """Mark loan as returned, restore book availability, and remove from Redis scheduler."""
        self.returned_at = timezone.now()
        # Restore book availability with validation to prevent exceeding total quantity
        from django.db.models import Case, When
        Book.objects.filter(id=self.book.id).update(
            available_quantity=Case(
                When(available_quantity__lt=models.F('quantity'),
                     then=models.F('available_quantity') + 1),
                default=models.F('quantity'),
                output_field=models.PositiveIntegerField()
            )
        )

        # Remove from Redis scheduler
        try:
            from .redis_scheduler import LoanScheduler
            scheduler = LoanScheduler()
            scheduler.remove_loan(self.pk)
        except Exception as e:
            # Don't fail the transition if Redis is unavailable
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to remove loan {self.pk} from Redis scheduler: {e}")


class LoanTransfer(models.Model):
    """
    LoanTransfer model representing the transfer of a loan from one user to another.
    Uses FSM to control transfer acceptance workflow.

    Workflow:
    1. PENDING: Transfer created, waiting for recipient acceptance (24h expiry)
    2. ACCEPTED: Recipient accepted, loan ownership transferred
    3. REJECTED: Recipient rejected, loan stays with original owner
    4. CANCELLED: Sender cancelled before acceptance
    5. EXPIRED: 24 hours passed without action
    """

    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        ACCEPTED = 'accepted', _('Accepted')
        REJECTED = 'rejected', _('Rejected')
        CANCELLED = 'cancelled', _('Cancelled')
        EXPIRED = 'expired', _('Expired')

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
    status = FSMField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        protected=True,
        help_text=_('Current status of the transfer')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_('When the transfer was created')
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the transfer request expires (24 hours)')
    )
    responded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the transfer was accepted/rejected/cancelled')
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loan_transfers'
        verbose_name = _('loan transfer')
        verbose_name_plural = _('loan transfers')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['loan']),
            models.Index(fields=['from_user']),
            models.Index(fields=['to_user']),
            models.Index(fields=['status']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"Transfer #{self.id}: Loan {self.loan.id} from {self.from_user.email} to {self.to_user.email} ({self.status})"

    def save(self, *args, **kwargs):
        """Set expiration time if not provided (24 hours from creation)."""
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    def clean(self):
        """Validate transfer constraints."""
        if self.from_user == self.to_user:
            raise ValidationError(_('Cannot transfer loan to the same user.'))

        # Check if loan belongs to from_user
        if self.loan.user != self.from_user:
            raise ValidationError(_('Can only transfer your own loans.'))

    @property
    def is_expired(self):
        """Check if the transfer request has expired."""
        if self.status != self.Status.PENDING:
            return False
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

    @property
    def remaining_time(self):
        """Calculate remaining time before expiration."""
        if self.status != self.Status.PENDING:
            return timedelta(0)
        if not self.expires_at:
            return timedelta(0)
        remaining = self.expires_at - timezone.now()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)

    def can_accept(self):
        """Check if transfer can be accepted."""
        return not self.is_expired

    def can_reject(self):
        """Check if transfer can be rejected."""
        return not self.is_expired

    def can_cancel(self):
        """Check if transfer can be cancelled."""
        return not self.is_expired

    def can_expire(self):
        """Check if transfer can be expired."""
        return self.is_expired

    @transition(field=status, source=Status.PENDING, target=Status.ACCEPTED,
                conditions=[can_accept],
                custom={'description': 'Accept transfer and change loan ownership'})
    def accept(self):
        """Accept the transfer and change loan ownership."""
        # Validate loan is still active
        if self.loan.status not in [Loan.Status.ACTIVE, Loan.Status.OVERDUE]:
            raise ValidationError(_('Cannot accept transfer: loan has been returned.'))

        self.responded_at = timezone.now()
        # Transfer loan ownership
        self.loan.user = self.to_user
        self.loan.save(update_fields=['user', 'updated_at'])

    @transition(field=status, source=Status.PENDING, target=Status.REJECTED,
                conditions=[can_reject],
                custom={'description': 'Reject transfer, loan stays with original owner'})
    def reject(self):
        """Reject the transfer, loan stays with original owner."""
        self.responded_at = timezone.now()
        # No loan changes needed

    @transition(field=status, source=Status.PENDING, target=Status.CANCELLED,
                conditions=[can_cancel],
                custom={'description': 'Cancel transfer before acceptance'})
    def cancel(self):
        """Cancel the transfer before it's accepted."""
        self.responded_at = timezone.now()
        # No loan changes needed

    @transition(field=status, source=Status.PENDING, target=Status.EXPIRED,
                conditions=[can_expire],
                custom={'description': 'Mark transfer as expired after 24 hours'})
    def expire(self):
        """Mark transfer as expired after 24 hours."""
        self.responded_at = timezone.now()
        # No loan changes needed
