"""
Book model for the biblioteca application.
"""
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class Book(models.Model):
    """
    Book model representing a book in the library.
    Tracks both total quantity and available quantity.
    """

    isbn = models.CharField(
        max_length=13,
        unique=True,
        blank=True,
        null=True,
        help_text=_('ISBN-13 code for the book')
    )
    title = models.CharField(
        max_length=255,
        help_text=_('Title of the book')
    )
    author = models.CharField(
        max_length=255,
        help_text=_('Author of the book')
    )
    description = models.TextField(
        blank=True,
        help_text=_('Description of the book')
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text=_('Total quantity of books available in the library')
    )
    available_quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(0)],
        help_text=_('Current quantity of books available for loan')
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_books',
        help_text=_('User who added this book to the library')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'books'
        verbose_name = _('book')
        verbose_name_plural = _('books')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['author']),
            models.Index(fields=['isbn']),
        ]

    def __str__(self):
        return f"{self.title} by {self.author}"

    def clean(self):
        """Validate that available_quantity doesn't exceed total quantity."""
        from django.core.exceptions import ValidationError
        if self.available_quantity > self.quantity:
            raise ValidationError(
                _('Available quantity cannot exceed total quantity.')
            )

    def save(self, *args, **kwargs):
        """Override save to run clean validation."""
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_available(self):
        """Check if the book has available copies."""
        return self.available_quantity > 0

    @property
    def borrowed_count(self):
        """Calculate how many copies are currently borrowed."""
        return self.quantity - self.available_quantity
