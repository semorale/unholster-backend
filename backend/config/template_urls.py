"""
URL configuration for template-based views (Django Templates V1).
"""
from django.urls import path

from apps.accounts.template_views import CustomLoginView, RegisterView, logout_view
from apps.books.template_views import (
    BookCreateView,
    BookDeleteView,
    BookDetailView,
    BookListView,
    BookUpdateView,
)
from apps.loans.template_views import (
    MyLoansView,
    MyReservationsView,
    librarian_dashboard,
    loan_create,
    loan_return,
    loan_share,
    reservation_cancel,
    reservation_convert,
    reservation_create,
)

from .views import home

urlpatterns = [
    # Home
    path('', home, name='home'),

    # Authentication
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', RegisterView.as_view(), name='register'),

    # Books
    path('books/', BookListView.as_view(), name='book_list'),
    path('books/<int:pk>/', BookDetailView.as_view(), name='book_detail'),
    path('books/create/', BookCreateView.as_view(), name='book_create'),
    path('books/<int:pk>/edit/', BookUpdateView.as_view(), name='book_edit'),
    path('books/<int:pk>/delete/', BookDeleteView.as_view(), name='book_delete'),

    # Reservations
    path('reservations/', MyReservationsView.as_view(), name='my_reservations'),
    path('reservations/create/', reservation_create, name='reservation_create'),
    path('reservations/<int:pk>/cancel/', reservation_cancel, name='reservation_cancel'),
    path('reservations/<int:pk>/convert/', reservation_convert, name='reservation_convert'),

    # Loans
    path('loans/', MyLoansView.as_view(), name='my_loans'),
    path('loans/create/', loan_create, name='loan_create'),
    path('loans/<int:pk>/return/', loan_return, name='loan_return'),
    path('loans/<int:pk>/share/', loan_share, name='loan_share'),

    # Librarian
    path('librarian/dashboard/', librarian_dashboard, name='librarian_dashboard'),
]
