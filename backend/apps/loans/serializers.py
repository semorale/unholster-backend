"""
Serializers for the loans app.
"""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django_fsm import TransitionNotAllowed
from rest_framework import serializers

from apps.books.serializers import BookListSerializer

from .models import Loan, LoanTransfer, Reservation


class ReservationSerializer(serializers.ModelSerializer):
    """Serializer for Reservation model."""

    book_details = BookListSerializer(source='book', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    is_expired = serializers.ReadOnlyField()
    remaining_time = serializers.ReadOnlyField()

    class Meta:
        model = Reservation
        fields = [
            'id', 'book', 'book_details', 'user', 'user_email',
            'reserved_at', 'expires_at', 'status', 'is_expired',
            'remaining_time', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'reserved_at', 'expires_at',
            'created_at', 'updated_at'
        ]

    def validate_book(self, value):
        """Validate that book is available for reservation."""
        if not value.is_available:
            raise serializers.ValidationError(
                'This book is not available for reservation.'
            )
        return value

    def validate(self, attrs):
        """Validate reservation limits."""
        user = self.context['request'].user

        # Check max active reservations (3)
        active_reservations = Reservation.objects.filter(
            user=user,
            status=Reservation.Status.ACTIVE
        ).count()

        if active_reservations >= 3:
            raise serializers.ValidationError(
                'You have reached the maximum number of active reservations (3).'
            )

        # Check if user already has an active reservation for this book
        book = attrs.get('book')
        if book and Reservation.objects.filter(
            user=user,
            book=book,
            status=Reservation.Status.ACTIVE
        ).exists():
            raise serializers.ValidationError(
                'You already have an active reservation for this book.'
            )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        """Create reservation and decrease book availability."""
        validated_data['user'] = self.context['request'].user
        validated_data['expires_at'] = timezone.now() + timedelta(hours=1)

        # Decrease book availability
        book = validated_data['book']
        if book.available_quantity < 1:
            raise serializers.ValidationError('Book is no longer available.')

        book.available_quantity -= 1
        book.save()

        return super().create(validated_data)


class LoanSerializer(serializers.ModelSerializer):
    """Serializer for Loan model."""

    book_details = BookListSerializer(source='book', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    is_overdue = serializers.ReadOnlyField()
    remaining_time = serializers.ReadOnlyField()
    has_pending_transfer = serializers.ReadOnlyField()
    pending_transfer = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = [
            'id', 'book', 'book_details', 'user', 'user_email',
            'reservation', 'borrowed_at', 'due_date', 'returned_at',
            'status', 'is_overdue', 'remaining_time',
            'has_pending_transfer', 'pending_transfer',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'borrowed_at', 'due_date', 'returned_at',
            'created_at', 'updated_at'
        ]

    def get_pending_transfer(self, obj):
        """Get pending transfer details if exists."""
        if obj.has_pending_transfer:
            transfer = obj.pending_transfer
            return {
                'id': transfer.id,
                'to_user_email': transfer.to_user.email,
                'to_user_name': transfer.to_user.full_name,
                'created_at': transfer.created_at,
                'expires_at': transfer.expires_at,
                'remaining_time': str(transfer.remaining_time)
            }
        return None

    def validate_book(self, value):
        """Validate that book is available for loan."""
        # If converting from reservation, skip this check
        if self.context.get('from_reservation'):
            return value

        if not value.is_available:
            raise serializers.ValidationError(
                'This book is not available for loan.'
            )
        return value

    def validate(self, attrs):
        """Validate loan limits."""
        user = self.context['request'].user

        # Skip validation if converting from reservation
        if self.context.get('from_reservation'):
            return attrs

        # Check max active loans (5)
        active_loans = Loan.objects.filter(
            user=user,
            status__in=[Loan.Status.ACTIVE, Loan.Status.OVERDUE]
        ).count()

        if active_loans >= 5:
            raise serializers.ValidationError(
                'You have reached the maximum number of active loans (5).'
            )

        # Check if user already has an active loan for this book
        book = attrs.get('book')
        if book and Loan.objects.filter(
            user=user,
            book=book,
            status__in=[Loan.Status.ACTIVE, Loan.Status.OVERDUE]
        ).exists():
            raise serializers.ValidationError(
                'You already have an active loan for this book.'
            )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        """Create loan and decrease book availability if not from reservation."""
        validated_data['user'] = self.context['request'].user
        validated_data['due_date'] = timezone.now() + timedelta(days=2)

        # Decrease book availability only if not from reservation
        if not self.context.get('from_reservation'):
            book = validated_data['book']
            if book.available_quantity < 1:
                raise serializers.ValidationError('Book is no longer available.')

            book.available_quantity -= 1
            book.save()

        return super().create(validated_data)


class LoanTransferSerializer(serializers.ModelSerializer):
    """Serializer for LoanTransfer model with pending acceptance workflow."""

    from_user_email = serializers.EmailField(source='from_user.email', read_only=True)
    to_user_email = serializers.EmailField(source='to_user.email', read_only=True)
    from_user_name = serializers.CharField(source='from_user.full_name', read_only=True)
    to_user_name = serializers.CharField(source='to_user.full_name', read_only=True)
    loan_details = LoanSerializer(source='loan', read_only=True)
    is_expired = serializers.ReadOnlyField()
    remaining_time = serializers.ReadOnlyField()

    class Meta:
        model = LoanTransfer
        fields = [
            'id', 'loan', 'loan_details', 'from_user', 'from_user_email', 'from_user_name',
            'to_user', 'to_user_email', 'to_user_name', 'status',
            'created_at', 'expires_at', 'responded_at', 'updated_at',
            'is_expired', 'remaining_time'
        ]
        read_only_fields = [
            'id', 'from_user', 'status', 'created_at', 'expires_at',
            'responded_at', 'updated_at'
        ]

    def validate(self, attrs):
        """Validate loan transfer request."""
        loan = attrs.get('loan')
        to_user = attrs.get('to_user')
        from_user = self.context['request'].user

        # Validate that the loan belongs to the requesting user
        if loan.user != from_user:
            raise serializers.ValidationError(
                'You can only transfer your own loans.'
            )

        # Validate that loan is active
        if loan.status != Loan.Status.ACTIVE:
            raise serializers.ValidationError(
                'Only active loans can be transferred.'
            )

        # Check if loan already has a pending transfer
        if loan.has_pending_transfer:
            raise serializers.ValidationError(
                'This loan already has a pending transfer.'
            )

        # Validate that to_user is different from from_user
        if to_user == from_user:
            raise serializers.ValidationError(
                'Cannot transfer loan to yourself.'
            )

        # Check if to_user has reached max loans (5) including pending transfers
        active_loans = Loan.objects.filter(
            user=to_user,
            status__in=[Loan.Status.ACTIVE, Loan.Status.OVERDUE]
        ).count()

        pending_transfers = LoanTransfer.objects.filter(
            to_user=to_user,
            status=LoanTransfer.Status.PENDING
        ).count()

        if active_loans + pending_transfers >= 5:
            raise serializers.ValidationError(
                'Target user has reached the maximum number of active loans (5) including pending transfers.'
            )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        """Create loan transfer request (PENDING status, not automatic)."""
        validated_data['from_user'] = self.context['request'].user
        validated_data['expires_at'] = timezone.now() + timedelta(hours=24)

        # Create the transfer record with PENDING status (default)
        transfer = super().create(validated_data)

        # DO NOT update the loan's user yet - wait for acceptance
        # Loan stays with from_user until transfer is accepted

        return transfer


class ConvertReservationToLoanSerializer(serializers.Serializer):
    """Serializer for converting a reservation to a loan."""

    reservation_id = serializers.IntegerField()

    def validate_reservation_id(self, value):
        """Validate that reservation exists and belongs to user."""
        user = self.context['request'].user

        try:
            reservation = Reservation.objects.get(id=value, user=user)
        except Reservation.DoesNotExist:
            raise serializers.ValidationError('Reservation not found.')

        if reservation.status != Reservation.Status.ACTIVE:
            raise serializers.ValidationError('Reservation is not active.')

        if reservation.is_expired:
            raise serializers.ValidationError('Reservation has expired.')

        return value

    @transaction.atomic
    def save(self):
        """Convert reservation to loan."""
        reservation = Reservation.objects.get(
            id=self.validated_data['reservation_id']
        )

        # Check max active loans (5)
        user = self.context['request'].user
        active_loans = Loan.objects.filter(
            user=user,
            status__in=[Loan.Status.ACTIVE, Loan.Status.OVERDUE]
        ).count()

        if active_loans >= 5:
            raise serializers.ValidationError(
                'You have reached the maximum number of active loans (5).'
            )

        # Check if user already has an active loan for this book
        if Loan.objects.filter(
            user=user,
            book=reservation.book,
            status__in=[Loan.Status.ACTIVE, Loan.Status.OVERDUE]
        ).exists():
            raise serializers.ValidationError(
                'You already have an active loan for this book.'
            )

        # Create loan from reservation
        loan = Loan.objects.create(
            book=reservation.book,
            user=reservation.user,
            reservation=reservation,
            due_date=timezone.now() + timedelta(days=2)
        )

        # Mark reservation as converted using FSM transition
        try:
            reservation.convert_to_loan()
            reservation.save()
        except TransitionNotAllowed:
            raise serializers.ValidationError(
                'Cannot convert this reservation to a loan.'
            )

        # Note: No need to adjust book availability as it was already
        # decreased when the reservation was created

        return loan
