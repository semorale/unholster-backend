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
from django_fsm import TransitionNotAllowed

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
    """Cancel an active reservation using FSM."""
    reservation = get_object_or_404(
        Reservation,
        id=pk,
        user=request.user,
        status=Reservation.Status.ACTIVE
    )

    if request.method == 'POST':
        try:
            # Use FSM transition to cancel
            reservation.cancel()
            reservation.save()
            messages.success(request, 'Reservation cancelled successfully.')
        except TransitionNotAllowed:
            messages.error(request, 'Cannot cancel this reservation.')

        return redirect('my_reservations')

    return redirect('my_reservations')


@login_required
@transaction.atomic
def reservation_convert(request, pk):
    """Convert a reservation to a loan using FSM."""
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

        # Check if user already has an active loan for this book
        if Loan.objects.filter(
            user=request.user,
            book=reservation.book,
            status__in=[Loan.Status.ACTIVE, Loan.Status.OVERDUE]
        ).exists():
            messages.error(request, 'You already have an active loan for this book.')
            return redirect('my_reservations')

        try:
            # Create loan
            loan = Loan.objects.create(
                book=reservation.book,
                user=request.user,
                reservation=reservation,
                due_date=timezone.now() + timedelta(days=2)
            )

            # Use FSM transition to convert reservation
            reservation.convert_to_loan()
            reservation.save()

            messages.success(request, f'Successfully converted reservation to loan. Due date: {loan.due_date.strftime("%B %d, %Y %H:%M")}')
            return redirect('my_loans')
        except TransitionNotAllowed:
            messages.error(request, 'Cannot convert this reservation.')
            return redirect('my_reservations')

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

        # Check if user already has an active loan for this book
        if Loan.objects.filter(
            user=request.user,
            book=book,
            status__in=[Loan.Status.ACTIVE, Loan.Status.OVERDUE]
        ).exists():
            messages.error(request, 'You already have an active loan for this book.')
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
    """Return a borrowed book using FSM."""
    loan = get_object_or_404(
        Loan,
        id=pk,
        user=request.user,
        status__in=[Loan.Status.ACTIVE, Loan.Status.OVERDUE]
    )

    if request.method == 'POST':
        # Check if loan has pending transfer
        if loan.has_pending_transfer:
            messages.error(request, 'Cannot return this loan while it has a pending transfer. Please cancel the transfer first.')
            return redirect('my_loans')

        try:
            # Use FSM transition to return loan
            loan.return_loan()
            loan.save()
            messages.success(request, f'Successfully returned "{loan.book.title}".')
        except TransitionNotAllowed:
            messages.error(request, 'Cannot return this loan.')

        return redirect('my_loans')

    return redirect('my_loans')


@login_required
def loan_share(request, pk):
    """Share/transfer a loan to another user (creates PENDING transfer)."""
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

        # Check if loan already has a pending transfer
        if loan.has_pending_transfer:
            messages.error(request, 'This loan already has a pending transfer.')
            return redirect('my_loans')

        # Check if to_user has reached max loans (including pending transfers)
        active_loans = Loan.objects.filter(
            user=to_user,
            status__in=[Loan.Status.ACTIVE, Loan.Status.OVERDUE]
        ).count()

        pending_transfers = LoanTransfer.objects.filter(
            to_user=to_user,
            status=LoanTransfer.Status.PENDING
        ).count()

        if active_loans + pending_transfers >= 5:
            messages.error(request, 'Target user has reached the maximum number of active loans (5) including pending transfers.')
            return redirect('my_loans')

        # Create PENDING transfer (DO NOT update loan ownership yet)
        with transaction.atomic():
            LoanTransfer.objects.create(
                loan=loan,
                from_user=request.user,
                to_user=to_user,
                expires_at=timezone.now() + timedelta(hours=24)
            )

        messages.success(request, f'Transfer request sent to {to_user.full_name}. They have 24 hours to accept.')
        return redirect('my_loans')

    # GET request - show user selection form
    from apps.accounts.models import User
    users = User.objects.filter(role=User.Role.LIBRARY_USER).exclude(id=request.user.id)

    context = {
        'loan': loan,
        'users': users,
    }

    return render(request, 'loans/loan_share_form.html', context)


class PendingTransfersView(LoginRequiredMixin, ListView):
    """View for user's pending transfer requests (received)."""

    model = LoanTransfer
    template_name = 'loans/pending_transfers.html'
    context_object_name = 'transfers'

    def get_queryset(self):
        """Get pending transfers for current user."""
        return LoanTransfer.objects.filter(
            to_user=self.request.user,
            status=LoanTransfer.Status.PENDING
        ).select_related('loan', 'loan__book', 'from_user').order_by('-created_at')


class MyTransfersSentView(LoginRequiredMixin, ListView):
    """View for user's sent transfer requests."""

    model = LoanTransfer
    template_name = 'loans/my_transfers_sent.html'
    context_object_name = 'transfers'

    def get_queryset(self):
        """Get transfers sent by current user."""
        return LoanTransfer.objects.filter(
            from_user=self.request.user
        ).select_related('loan', 'loan__book', 'to_user').order_by('-created_at')


@login_required
@transaction.atomic
def transfer_accept(request, pk):
    """Accept a pending loan transfer using FSM."""
    transfer = get_object_or_404(
        LoanTransfer,
        id=pk,
        to_user=request.user,
        status=LoanTransfer.Status.PENDING
    )

    if request.method == 'POST':
        # Validate transfer hasn't expired
        if transfer.is_expired:
            messages.error(request, 'This transfer request has expired.')
            return redirect('pending_transfers')

        try:
            # Use FSM transition to accept
            transfer.accept()
            transfer.save()
            messages.success(request, f'Successfully accepted loan transfer for "{transfer.loan.book.title}".')
            return redirect('my_loans')
        except TransitionNotAllowed:
            messages.error(request, 'Cannot accept this transfer. It may have expired.')
            return redirect('pending_transfers')
        except Exception as e:
            messages.error(request, f'Cannot accept this transfer: {str(e)}')
            return redirect('pending_transfers')

    return redirect('pending_transfers')


@login_required
@transaction.atomic
def transfer_reject(request, pk):
    """Reject a pending loan transfer using FSM."""
    transfer = get_object_or_404(
        LoanTransfer,
        id=pk,
        to_user=request.user,
        status=LoanTransfer.Status.PENDING
    )

    if request.method == 'POST':
        try:
            # Use FSM transition to reject
            transfer.reject()
            transfer.save()
            messages.success(request, 'Transfer request rejected.')
            return redirect('pending_transfers')
        except TransitionNotAllowed:
            messages.error(request, 'Cannot reject this transfer.')
            return redirect('pending_transfers')

    return redirect('pending_transfers')


@login_required
@transaction.atomic
def transfer_cancel(request, pk):
    """Cancel a pending loan transfer (sender) using FSM."""
    transfer = get_object_or_404(
        LoanTransfer,
        id=pk,
        from_user=request.user,
        status=LoanTransfer.Status.PENDING
    )

    if request.method == 'POST':
        try:
            # Use FSM transition to cancel
            transfer.cancel()
            transfer.save()
            messages.success(request, 'Transfer request cancelled.')
            return redirect('my_transfers_sent')
        except TransitionNotAllowed:
            messages.error(request, 'Cannot cancel this transfer.')
            return redirect('my_transfers_sent')

    return redirect('my_transfers_sent')
