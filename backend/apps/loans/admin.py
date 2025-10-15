"""
Admin configuration for loans app.
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Loan, LoanTransfer, Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    """Admin configuration for Reservation model."""

    list_display = ['id', 'book', 'user', 'reserved_at', 'expires_at', 'status']
    list_filter = ['status', 'reserved_at']
    search_fields = ['book__title', 'user__email']
    readonly_fields = ['reserved_at', 'created_at', 'updated_at', 'remaining_time']
    ordering = ['-created_at']

    fieldsets = (
        (_('Reservation Details'), {
            'fields': ('book', 'user', 'status')
        }),
        (_('Timing'), {
            'fields': ('reserved_at', 'expires_at', 'remaining_time')
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def remaining_time(self, obj):
        """Display remaining time in admin."""
        return obj.remaining_time
    remaining_time.short_description = _('Remaining Time')


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    """Admin configuration for Loan model."""

    list_display = ['id', 'book', 'user', 'borrowed_at', 'due_date', 'returned_at', 'status']
    list_filter = ['status', 'borrowed_at', 'due_date']
    search_fields = ['book__title', 'user__email']
    readonly_fields = ['borrowed_at', 'created_at', 'updated_at', 'remaining_time']
    ordering = ['-created_at']

    fieldsets = (
        (_('Loan Details'), {
            'fields': ('book', 'user', 'reservation', 'status')
        }),
        (_('Timing'), {
            'fields': ('borrowed_at', 'due_date', 'returned_at', 'remaining_time')
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def remaining_time(self, obj):
        """Display remaining time in admin."""
        return obj.remaining_time
    remaining_time.short_description = _('Remaining Time')


@admin.register(LoanTransfer)
class LoanTransferAdmin(admin.ModelAdmin):
    """Admin configuration for LoanTransfer model."""

    list_display = ['id', 'loan', 'from_user', 'to_user', 'transferred_at', 'accepted']
    list_filter = ['accepted', 'transferred_at']
    search_fields = ['loan__book__title', 'from_user__email', 'to_user__email']
    readonly_fields = ['transferred_at', 'created_at']
    ordering = ['-transferred_at']

    fieldsets = (
        (_('Transfer Details'), {
            'fields': ('loan', 'from_user', 'to_user', 'accepted')
        }),
        (_('Metadata'), {
            'fields': ('transferred_at', 'created_at')
        }),
    )
