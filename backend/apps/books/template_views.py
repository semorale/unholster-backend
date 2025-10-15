"""
Template-based views for the books app (Django Templates V1).
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .models import Book


class BookListView(LoginRequiredMixin, ListView):
    """List view for books with search and filter capabilities."""

    model = Book
    template_name = 'books/book_list.html'
    context_object_name = 'books'
    paginate_by = 12

    def get_queryset(self):
        """Filter books based on search and availability."""
        queryset = Book.objects.all()

        # Search functionality
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(author__icontains=search_query) |
                Q(isbn__icontains=search_query)
            )

        # Availability filter
        available = self.request.GET.get('available', '')
        if available == 'true':
            queryset = queryset.filter(available_quantity__gt=0)
        elif available == 'false':
            queryset = queryset.filter(available_quantity=0)

        return queryset.order_by('-created_at')


class BookDetailView(LoginRequiredMixin, DetailView):
    """Detail view for a single book."""

    model = Book
    template_name = 'books/book_detail.html'
    context_object_name = 'book'


class BookCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Create view for adding a new book (librarian only)."""

    model = Book
    template_name = 'books/book_form.html'
    fields = ['title', 'author', 'isbn', 'description', 'quantity']
    success_url = reverse_lazy('book_list')

    def test_func(self):
        """Only librarians can create books."""
        return self.request.user.is_librarian

    def form_valid(self, form):
        """Set created_by and available_quantity."""
        form.instance.created_by = self.request.user
        form.instance.available_quantity = form.instance.quantity
        messages.success(self.request, f'Book "{form.instance.title}" added successfully.')
        return super().form_valid(form)


class BookUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update view for editing a book (librarian only)."""

    model = Book
    template_name = 'books/book_form.html'
    fields = ['title', 'author', 'isbn', 'description', 'quantity', 'available_quantity']

    def test_func(self):
        """Only librarians can update books."""
        return self.request.user.is_librarian

    def form_valid(self, form):
        """Add success message."""
        messages.success(self.request, f'Book "{form.instance.title}" updated successfully.')
        return super().form_valid(form)

    def get_success_url(self):
        """Redirect to book detail page."""
        return reverse_lazy('book_detail', kwargs={'pk': self.object.pk})


class BookDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete view for removing a book (librarian only)."""

    model = Book
    success_url = reverse_lazy('book_list')

    def test_func(self):
        """Only librarians can delete books."""
        return self.request.user.is_librarian

    def post(self, request, *args, **kwargs):
        """Add success message before deletion."""
        book = self.get_object()
        messages.success(request, f'Book "{book.title}" deleted successfully.')
        return super().post(request, *args, **kwargs)
