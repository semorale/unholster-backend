"""
Tests for the books API endpoints.
"""
import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.integration
class TestBookAPI:
    """Test suite for book endpoints."""

    def test_list_books(self, authenticated_client, book):
        """Test listing books."""
        url = reverse('book-list')

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_list_books_unauthenticated(self, api_client):
        """Test that unauthenticated users cannot list books."""
        url = reverse('book-list')

        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_book(self, authenticated_client, book):
        """Test retrieving book details."""
        url = reverse('book-detail', args=[book.id])

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == book.title
        assert response.data['author'] == book.author

    def test_search_books(self, authenticated_client, book):
        """Test searching books."""
        url = reverse('book-list')

        response = authenticated_client.get(url, {'search': 'Test'})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_filter_books_by_availability(self, authenticated_client, book):
        """Test filtering books by availability."""
        url = reverse('book-list')

        response = authenticated_client.get(url, {'available': 'true'})

        assert response.status_code == status.HTTP_200_OK
        for book_data in response.data['results']:
            assert book_data['available_quantity'] > 0

    def test_create_book_as_librarian(self, librarian_client):
        """Test creating a book as librarian."""
        url = reverse('book-list')
        data = {
            'title': 'New Book',
            'author': 'New Author',
            'quantity': 3,
        }

        response = librarian_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'New Book'

    def test_create_book_as_regular_user(self, authenticated_client):
        """Test that regular users cannot create books."""
        url = reverse('book-list')
        data = {
            'title': 'New Book',
            'author': 'New Author',
            'quantity': 3,
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_book_as_librarian(self, librarian_client, book):
        """Test updating a book as librarian."""
        url = reverse('book-detail', args=[book.id])
        data = {
            'title': 'Updated Title',
            'author': book.author,
            'quantity': book.quantity,
        }

        response = librarian_client.put(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'Updated Title'

    def test_delete_book_as_librarian(self, librarian_client, book):
        """Test deleting a book as librarian."""
        url = reverse('book-detail', args=[book.id])

        response = librarian_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_check_book_availability(self, authenticated_client, book):
        """Test checking book availability."""
        url = reverse('book-availability', args=[book.id])

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'available_quantity' in response.data
        assert 'is_available' in response.data
