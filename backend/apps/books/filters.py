"""
Filters for the books app.
"""
import django_filters

from .models import Book


class BookFilter(django_filters.FilterSet):
    """Filter for Book model with search capabilities."""

    title = django_filters.CharFilter(lookup_expr='icontains')
    author = django_filters.CharFilter(lookup_expr='icontains')
    isbn = django_filters.CharFilter(lookup_expr='icontains')
    available = django_filters.BooleanFilter(method='filter_available')

    class Meta:
        model = Book
        fields = ['title', 'author', 'isbn', 'available']

    def filter_available(self, queryset, name, value):
        """Filter books by availability status."""
        if value:
            return queryset.filter(available_quantity__gt=0)
        return queryset.filter(available_quantity=0)
