"""
Tests for the Book model.
"""
import pytest
from django.core.exceptions import ValidationError

from apps.books.models import Book


@pytest.mark.unit
class TestBookModel:
    """Test suite for Book model."""

    def test_create_book(self, book):
        """Test creating a book."""
        assert book.title == 'Test Book'
        assert book.author == 'Test Author'
        assert book.isbn == '1234567890123'
        assert book.quantity == 5
        assert book.available_quantity == 5

    def test_book_str_representation(self, book):
        """Test string representation of book."""
        assert str(book) == 'Test Book by Test Author'

    def test_is_available_property(self, book, unavailable_book):
        """Test is_available property."""
        assert book.is_available
        assert not unavailable_book.is_available

    def test_borrowed_count_property(self, book):
        """Test borrowed_count property."""
        book.available_quantity = 3
        book.save()
        assert book.borrowed_count == 2

    def test_book_validation_available_quantity(self, librarian_user):
        """Test that available_quantity cannot exceed quantity."""
        book = Book(
            title='Test',
            author='Author',
            quantity=5,
            available_quantity=10,
            created_by=librarian_user
        )

        with pytest.raises(ValidationError):
            book.save()

    def test_book_without_isbn(self, librarian_user):
        """Test creating book without ISBN."""
        book = Book.objects.create(
            title='No ISBN Book',
            author='Test Author',
            quantity=1,
            available_quantity=1,
            created_by=librarian_user
        )

        assert book.isbn is None or book.isbn == ''

    def test_book_quantity_validators(self, librarian_user):
        """Test that quantity must be at least 1."""
        book = Book(
            title='Test',
            author='Author',
            quantity=0,
            available_quantity=0,
            created_by=librarian_user
        )

        with pytest.raises(ValidationError):
            book.full_clean()
