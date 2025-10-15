"""
Admin configuration for books app.
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Book


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    """Admin configuration for Book model."""

    list_display = ['title', 'author', 'isbn', 'quantity', 'available_quantity', 'created_at']
    list_filter = ['created_at', 'author']
    search_fields = ['title', 'author', 'isbn', 'description']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'borrowed_count']
    ordering = ['-created_at']

    fieldsets = (
        (_('Book Information'), {
            'fields': ('title', 'author', 'isbn', 'description')
        }),
        (_('Inventory'), {
            'fields': ('quantity', 'available_quantity', 'borrowed_count')
        }),
        (_('Metadata'), {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )

    def borrowed_count(self, obj):
        """Display borrowed count in admin."""
        return obj.borrowed_count
    borrowed_count.short_description = _('Borrowed Count')
