"""
Views for the books app.
"""
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsLibrarianOrReadOnly

from .filters import BookFilter
from .models import Book
from .serializers import (
    BookAvailabilitySerializer,
    BookListSerializer,
    BookSerializer,
)


@extend_schema_view(
    list=extend_schema(
        summary='List all books',
        description='Get a paginated list of all books with search and filter options.',
        tags=['Books']
    ),
    retrieve=extend_schema(
        summary='Get book details',
        description='Retrieve detailed information about a specific book.',
        tags=['Books']
    ),
    create=extend_schema(
        summary='Create a new book',
        description='Add a new book to the library (librarian only).',
        tags=['Books']
    ),
    update=extend_schema(
        summary='Update book',
        description='Update all fields of a book (librarian only).',
        tags=['Books']
    ),
    partial_update=extend_schema(
        summary='Partial update book',
        description='Update specific fields of a book (librarian only).',
        tags=['Books']
    ),
    destroy=extend_schema(
        summary='Delete book',
        description='Delete a book from the library (librarian only).',
        tags=['Books']
    )
)
class BookViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing books.
    - List/Retrieve: Available to all authenticated users
    - Create/Update/Delete: Only available to librarians
    """

    queryset = Book.objects.select_related('created_by').all()
    permission_classes = [IsAuthenticated, IsLibrarianOrReadOnly]
    filterset_class = BookFilter
    search_fields = ['title', 'author', 'isbn', 'description']
    ordering_fields = ['title', 'author', 'created_at', 'available_quantity']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return BookListSerializer
        elif self.action == 'availability':
            return BookAvailabilitySerializer
        return BookSerializer

    @extend_schema(
        summary='Check book availability',
        description='Check the availability status of a specific book.',
        responses={200: BookAvailabilitySerializer},
        tags=['Books']
    )
    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        """Endpoint to check book availability."""
        book = self.get_object()
        serializer = BookAvailabilitySerializer(book)
        return Response(serializer.data, status=status.HTTP_200_OK)
