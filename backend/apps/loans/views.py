"""
Views for the loans app.
"""
from django.db import transaction
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsLibrarian, IsOwnerOrLibrarian

from .models import Loan, LoanTransfer, Reservation
from .serializers import (
    ConvertReservationToLoanSerializer,
    LoanSerializer,
    LoanTransferSerializer,
    ReservationSerializer,
)


@extend_schema_view(
    list=extend_schema(
        summary='List reservations',
        description='Get reservations. Library users see their own, librarians see all.',
        tags=['Reservations']
    ),
    retrieve=extend_schema(
        summary='Get reservation details',
        description='Retrieve detailed information about a specific reservation.',
        tags=['Reservations']
    ),
    create=extend_schema(
        summary='Create a reservation',
        description='Reserve a book for 1 hour.',
        tags=['Reservations']
    ),
    destroy=extend_schema(
        summary='Cancel reservation',
        description='Cancel an active reservation.',
        tags=['Reservations']
    )
)
class ReservationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing reservations.
    Users can only see and manage their own reservations.
    Librarians can see all reservations.
    """

    serializer_class = ReservationSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrLibrarian]
    filterset_fields = ['status', 'book']
    ordering_fields = ['created_at', 'expires_at']
    ordering = ['-created_at']
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        """Return reservations based on user role."""
        user = self.request.user
        if user.is_librarian:
            return Reservation.objects.select_related('book', 'user').all()
        return Reservation.objects.select_related('book', 'user').filter(user=user)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """Cancel reservation and restore book availability."""
        instance = self.get_object()

        if instance.status == Reservation.Status.ACTIVE:
            # Restore book availability
            instance.book.available_quantity += 1
            instance.book.save()

            # Mark reservation as cancelled
            instance.status = Reservation.Status.CANCELLED
            instance.save()

            return Response(
                {'detail': 'Reservation cancelled successfully.'},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'detail': 'Only active reservations can be cancelled.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @extend_schema(
        summary='Convert reservation to loan',
        description='Convert an active reservation into a 2-day loan.',
        request=ConvertReservationToLoanSerializer,
        responses={201: LoanSerializer},
        tags=['Reservations']
    )
    @action(detail=True, methods=['post'], url_path='convert-to-loan')
    def convert_to_loan(self, request, pk=None):
        """Endpoint to convert a reservation to a loan."""
        reservation = self.get_object()

        serializer = ConvertReservationToLoanSerializer(
            data={'reservation_id': reservation.id},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        loan = serializer.save()

        return Response(
            LoanSerializer(loan).data,
            status=status.HTTP_201_CREATED
        )


@extend_schema_view(
    list=extend_schema(
        summary='List loans',
        description='Get loans. Library users see their own, librarians see all.',
        tags=['Loans']
    ),
    retrieve=extend_schema(
        summary='Get loan details',
        description='Retrieve detailed information about a specific loan.',
        tags=['Loans']
    ),
    create=extend_schema(
        summary='Create a loan',
        description='Borrow a book for 2 days.',
        tags=['Loans']
    )
)
class LoanViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing loans.
    Users can only see and manage their own loans.
    Librarians can see all loans.
    """

    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrLibrarian]
    filterset_fields = ['status', 'book']
    ordering_fields = ['created_at', 'due_date']
    ordering = ['-created_at']
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        """Return loans based on user role."""
        user = self.request.user
        if user.is_librarian:
            return Loan.objects.select_related('book', 'user', 'reservation').all()
        return Loan.objects.select_related('book', 'user', 'reservation').filter(user=user)

    @extend_schema(
        summary='Return a book',
        description='Mark a loan as returned and restore book availability.',
        responses={200: LoanSerializer},
        tags=['Loans']
    )
    @action(detail=True, methods=['post'])
    def return_book(self, request, pk=None):
        """Endpoint to return a borrowed book."""
        loan = self.get_object()

        if loan.status in [Loan.Status.ACTIVE, Loan.Status.OVERDUE]:
            loan.return_book()
            return Response(
                LoanSerializer(loan).data,
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'detail': 'This loan has already been returned.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @extend_schema(
        summary='Share a loan',
        description='Transfer a loan to another user.',
        request=LoanTransferSerializer,
        responses={201: LoanTransferSerializer},
        tags=['Loans']
    )
    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        """Endpoint to share/transfer a loan to another user."""
        loan = self.get_object()

        serializer = LoanTransferSerializer(
            data={'loan': loan.id, 'to_user': request.data.get('to_user')},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        transfer = serializer.save()

        return Response(
            LoanTransferSerializer(transfer).data,
            status=status.HTTP_201_CREATED
        )

    @extend_schema(
        summary='Get active loans',
        description='Get all active loans for the current user or all users (librarian).',
        responses={200: LoanSerializer(many=True)},
        tags=['Loans']
    )
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Endpoint to get all active loans."""
        queryset = self.get_queryset().filter(
            status__in=[Loan.Status.ACTIVE, Loan.Status.OVERDUE]
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(
        summary='List loan transfers',
        description='Get loan transfer history.',
        tags=['Loan Transfers']
    ),
    retrieve=extend_schema(
        summary='Get loan transfer details',
        description='Retrieve detailed information about a specific loan transfer.',
        tags=['Loan Transfers']
    )
)
class LoanTransferViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing loan transfers.
    Read-only as transfers are created through the loan share endpoint.
    """

    serializer_class = LoanTransferSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['loan', 'from_user', 'to_user', 'accepted']
    ordering_fields = ['transferred_at']
    ordering = ['-transferred_at']

    def get_queryset(self):
        """Return transfers based on user role."""
        user = self.request.user
        if user.is_librarian:
            return LoanTransfer.objects.select_related(
                'loan', 'loan__book', 'from_user', 'to_user'
            ).all()
        return LoanTransfer.objects.select_related(
            'loan', 'loan__book', 'from_user', 'to_user'
        ).filter(from_user=user) | LoanTransfer.objects.select_related(
            'loan', 'loan__book', 'from_user', 'to_user'
        ).filter(to_user=user)
