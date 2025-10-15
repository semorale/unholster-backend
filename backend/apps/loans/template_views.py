"""
Template-based views for the loans app (Django Templates V1).
"""
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import ListView

from apps.books.models import Book

from .models import Loan, LoanTransfer, Reservation


def is_librarian(user):
    """Check if user is a librarian."""
    return user.is_authenticated and user.is_librarian


class MyReservationsView(LoginRequiredMixin, ListView):
    """View for user's active reservations."""

    model = Reservation
    template_name = 'loans/my_reservations.html'
    context_object_name = 'reservations'

    def get_queryset(self):
        """Get active reservations for current user."""
        return Reservation.objects.filter(
            user=self.request.user,
            status=Reservation.Status.ACTIVE
        ).select_related('book').order_by('-created_at')


class MyLoansView(LoginRequiredMixin, ListView):
    """View for user's active loans."""

    model = Loan
    template_name = 'loans/my_loans.html'
    context_object_name = 'loans'

    def get_queryset(self):
        """Get active loans for current user."""
        return Loan.objects.filter(
            user=self.request.user,
            status__in=[Loan.Status.ACTIVE, Loan.Status.OVERDUE]
        ).select_related('book').order_by('-borrowed_at')


@login_required
@user_passes_test(is_librarian)
def librarian_dashboard(request):
    """Dashboard view for librarians with statistics."""

    # Calculate statistics
    stats = {
        'total_books': Book.objects.count(),
        'available_copies': Book.objects.aggregate(total=Sum('available_quantity'))['total'] or 0,
        'active_reservations': Reservation.objects.filter(status=Reservation.Status.ACTIVE).count(),
        'active_loans': Loan.objects.filter(status__in=[Loan.Status.ACTIVE, Loan.Status.OVERDUE]).count(),
    }

    # Get recent loans
    recent_loans = Loan.objects.select_related(
        'book', 'user'
    ).order_by('-created_at')[:10]

    # Get recent reservations
    recent_reservations = Reservation.objects.select_related(
        'book', 'user'
    ).order_by('-created_at')[:10]

    context = {
        'stats': stats,
        'recent_loans': recent_loans,
        'recent_reservations': recent_reservations,
    }

    return render(request, 'loans/librarian_dashboard.html', context)


@login_required
@transaction.atomic
def reservation_create(request):
    """Create a new reservation."""
    if request.method == 'POST':
        book_id = request.POST.get('book')
        book = get_object_or_404(Book, id=book_id)

        # Check if book is available
        if not book.is_available:
            messages.error(request, 'This book is not available for reservation.')
            return redirect('book_detail', pk=book.id)

        # Check max reservations
        active_reservations = Reservation.objects.filter(
            user=request.user,
            status=Reservation.Status.ACTIVE
        ).count()

        if active_reservations >= 3:
            messages.error(request, 'You have reached the maximum number of active reservations (3).')
            return redirect('book_detail', pk=book.id)

        # Check if user already has an active reservation for this book
        if Reservation.objects.filter(
            user=request.user,
            book=book,
            status=Reservation.Status.ACTIVE
        ).exists():
            messages.error(request, 'You already have an active reservation for this book.')
            return redirect('book_detail', pk=book.id)

        # Create reservation
        reservation = Reservation.objects.create(
            book=book,
            user=request.user,
            expires_at=timezone.now() + timedelta(hours=1)
        )

        # Decrease book availability
        book.available_quantity -= 1
        book.save()

        messages.success(request, f'Successfully reserved "{book.title}" for 1 hour.')
        return redirect('my_reservations')

    return redirect('book_list')


@login_required
@transaction.atomic
def reservation_cancel(request, pk):
    """Cancel an active reservation."""
    reservation = get_object_or_404(
        Reservation,
        id=pk,
        user=request.user,
        status=Reservation.Status.ACTIVE
    )

    if request.method == 'POST':
        # Restore book availability
        reservation.book.available_quantity += 1
        reservation.book.save()

        # Mark reservation as cancelled
        reservation.status = Reservation.Status.CANCELLED
        reservation.save()

        messages.success(request, 'Reservation cancelled successfully.')
        return redirect('my_reservations')

    return redirect('my_reservations')


@login_required
@transaction.atomic
def reservation_convert(request, pk):
    """Convert a reservation to a loan."""
    reservation = get_object_or_404(
        Reservation,
        id=pk,
        user=request.user,
        status=Reservation.Status.ACTIVE
    )

    if request.method == 'POST':
        # Check if reservation is expired
        if reservation.is_expired:
            messages.error(request, 'This reservation has expired.')
            return redirect('my_reservations')

        # Check max loans
        active_loans = Loan.objects.filter(
            user=request.user,
            status__in=[Loan.Status.ACTIVE, Loan.Status.OVERDUE]
        ).count()

        if active_loans >= 5:
            messages.error(request, 'You have reached the maximum number of active loans (5).')
            return redirect('my_reservations')

        # Create loan
        loan = Loan.objects.create(
            book=reservation.book,
            user=request.user,
            reservation=reservation,
            due_date=timezone.now() + timedelta(days=2)
        )

        # Mark reservation as converted
        reservation.status = Reservation.Status.CONVERTED_TO_LOAN
        reservation.save()

        messages.success(request, f'Successfully converted reservation to loan. Due date: {loan.due_date.strftime("%B %d, %Y %H:%M")}')
        return redirect('my_loans')

    return redirect('my_reservations')


@login_required
@transaction.atomic
def loan_create(request):
    """Create a new loan directly (without reservation)."""
    if request.method == 'POST':
        book_id = request.POST.get('book')
        book = get_object_or_404(Book, id=book_id)

        # Check if book is available
        if not book.is_available:
            messages.error(request, 'This book is not available for borrowing.')
            return redirect('book_detail', pk=book.id)

        # Check max loans
        active_loans = Loan.objects.filter(
            user=request.user,
            status__in=[Loan.Status.ACTIVE, Loan.Status.OVERDUE]
        ).count()

        if active_loans >= 5:
            messages.error(request, 'You have reached the maximum number of active loans (5).')
            return redirect('book_detail', pk=book.id)

        # Create loan
        loan = Loan.objects.create(
            book=book,
            user=request.user,
            due_date=timezone.now() + timedelta(days=2)
        )

        # Decrease book availability
        book.available_quantity -= 1
        book.save()

        messages.success(request, f'Successfully borrowed "{book.title}". Due date: {loan.due_date.strftime("%B %d, %Y %H:%M")}')
        return redirect('my_loans')

    return redirect('book_list')


@login_required
@transaction.atomic
def loan_return(request, pk):
    """Return a borrowed book."""
    loan = get_object_or_404(
        Loan,
        id=pk,
        user=request.user,
        status__in=[Loan.Status.ACTIVE, Loan.Status.OVERDUE]
    )

    if request.method == 'POST':
        loan.return_book()
        messages.success(request, f'Successfully returned "{loan.book.title}".')
        return redirect('my_loans')

    return redirect('my_loans')


@login_required
def loan_share(request, pk):
    """Share/transfer a loan to another user."""
    loan = get_object_or_404(
        Loan,
        id=pk,
        user=request.user,
        status=Loan.Status.ACTIVE
    )

    if request.method == 'POST':
        to_user_id = request.POST.get('to_user')

        if not to_user_id:
            messages.error(request, 'Please select a user to share with.')
            return redirect('my_loans')

        from apps.accounts.models import User
        to_user = get_object_or_404(User, id=to_user_id)

        # Validate
        if to_user == request.user:
            messages.error(request, 'Cannot transfer loan to yourself.')
            return redirect('my_loans')

        # Check if to_user has reached max loans
        active_loans = Loan.objects.filter(
            user=to_user,
            status__in=[Loan.Status.ACTIVE, Loan.Status.OVERDUE]
        ).count()

        if active_loans >= 5:
            messages.error(request, 'Target user has reached the maximum number of active loans (5).')
            return redirect('my_loans')

        # Create transfer and update loan
        with transaction.atomic():
            LoanTransfer.objects.create(
                loan=loan,
                from_user=request.user,
                to_user=to_user
            )
            loan.user = to_user
            loan.save()

        messages.success(request, f'Successfully shared loan with {to_user.full_name}.')
        return redirect('my_loans')

    # GET request - show user selection form
    from apps.accounts.models import User
    users = User.objects.filter(role=User.Role.LIBRARY_USER).exclude(id=request.user.id)

    context = {
        'loan': loan,
        'users': users,
    }

    return render(request, 'loans/loan_share_form.html', context)
