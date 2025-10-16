"""
Views for the loans app.
"""
from django.db import transaction
from django_fsm import TransitionNotAllowed
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
        """Cancel reservation and restore book availability using FSM."""
        instance = self.get_object()

        if instance.status == Reservation.Status.ACTIVE:
            try:
                # Use FSM transition to cancel
                instance.cancel()
                instance.save()

                return Response(
                    {'detail': 'Reservation cancelled successfully.'},
                    status=status.HTTP_200_OK
                )
            except TransitionNotAllowed:
                return Response(
                    {'detail': 'Cannot cancel this reservation.'},
                    status=status.HTTP_400_BAD_REQUEST
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
        """Endpoint to return a borrowed book using FSM."""
        loan = self.get_object()

        if loan.status in [Loan.Status.ACTIVE, Loan.Status.OVERDUE]:
            try:
                # Use FSM transition to return loan
                loan.return_loan()
                loan.save()
                return Response(
                    LoanSerializer(loan).data,
                    status=status.HTTP_200_OK
                )
            except TransitionNotAllowed:
                return Response(
                    {'detail': 'Cannot return this loan.'},
                    status=status.HTTP_400_BAD_REQUEST
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
    ViewSet for managing loan transfers with acceptance workflow.
    Transfers are created through the loan share endpoint.
    Acceptance, rejection, and cancellation are handled through custom actions.
    """

    serializer_class = LoanTransferSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['loan', 'from_user', 'to_user', 'status']
    ordering_fields = ['created_at', 'responded_at']
    ordering = ['-created_at']

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

    @extend_schema(
        summary='Get pending transfers',
        description='Get all pending transfer requests received by the current user.',
        responses={200: LoanTransferSerializer(many=True)},
        tags=['Loan Transfers']
    )
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Endpoint to get all pending transfers for the current user."""
        queryset = LoanTransfer.objects.filter(
            to_user=request.user,
            status=LoanTransfer.Status.PENDING
        ).select_related('loan', 'loan__book', 'from_user')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary='Accept transfer',
        description='Accept a pending loan transfer. Loan ownership will be transferred.',
        responses={200: LoanTransferSerializer},
        tags=['Loan Transfers']
    )
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def accept(self, request, pk=None):
        """Endpoint for recipient to accept a loan transfer."""
        transfer = self.get_object()

        # Validate transfer belongs to current user (recipient)
        if transfer.to_user != request.user:
            return Response(
                {'detail': 'You can only accept transfers sent to you.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if transfer is pending
        if transfer.status != LoanTransfer.Status.PENDING:
            return Response(
                {'detail': f'Cannot accept transfer with status: {transfer.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Use FSM transition to accept
            transfer.accept()
            transfer.save()

            return Response(
                LoanTransferSerializer(transfer, context={'request': request}).data,
                status=status.HTTP_200_OK
            )
        except TransitionNotAllowed:
            return Response(
                {'detail': 'Cannot accept this transfer. It may have expired.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @extend_schema(
        summary='Reject transfer',
        description='Reject a pending loan transfer. Loan stays with original owner.',
        responses={200: LoanTransferSerializer},
        tags=['Loan Transfers']
    )
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def reject(self, request, pk=None):
        """Endpoint for recipient to reject a loan transfer."""
        transfer = self.get_object()

        # Validate transfer belongs to current user (recipient)
        if transfer.to_user != request.user:
            return Response(
                {'detail': 'You can only reject transfers sent to you.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if transfer is pending
        if transfer.status != LoanTransfer.Status.PENDING:
            return Response(
                {'detail': f'Cannot reject transfer with status: {transfer.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Use FSM transition to reject
            transfer.reject()
            transfer.save()

            return Response(
                LoanTransferSerializer(transfer, context={'request': request}).data,
                status=status.HTTP_200_OK
            )
        except TransitionNotAllowed:
            return Response(
                {'detail': 'Cannot reject this transfer. It may have expired.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @extend_schema(
        summary='Cancel transfer',
        description='Cancel a pending loan transfer (by sender). Loan stays with original owner.',
        responses={200: LoanTransferSerializer},
        tags=['Loan Transfers']
    )
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def cancel(self, request, pk=None):
        """Endpoint for sender to cancel a loan transfer."""
        transfer = self.get_object()

        # Validate transfer belongs to current user (sender)
        if transfer.from_user != request.user:
            return Response(
                {'detail': 'You can only cancel transfers you initiated.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if transfer is pending
        if transfer.status != LoanTransfer.Status.PENDING:
            return Response(
                {'detail': f'Cannot cancel transfer with status: {transfer.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Use FSM transition to cancel
            transfer.cancel()
            transfer.save()

            return Response(
                LoanTransferSerializer(transfer, context={'request': request}).data,
                status=status.HTTP_200_OK
            )
        except TransitionNotAllowed:
            return Response(
                {'detail': 'Cannot cancel this transfer. It may have expired.'},
                status=status.HTTP_400_BAD_REQUEST
            )
