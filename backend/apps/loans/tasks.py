"""
Celery tasks for the loans app - Redis event-driven version.
"""
from celery import shared_task
from django.utils import timezone
from django_fsm import TransitionNotAllowed

from apps.loans.models import Loan, LoanTransfer, Reservation
from apps.loans.redis_scheduler import LoanScheduler


@shared_task
def mark_overdue_loans():
    """
    Event-driven approach: Check Redis sorted set for overdue loans.
    Much more efficient than scanning all active loans.
    Runs every 1 minute (can be more frequent).

    This is the new default task that uses Redis for efficient scheduling.
    """
    scheduler = LoanScheduler()

    # Get overdue loan IDs from Redis (very fast, O(log N))
    overdue_loan_ids = scheduler.get_overdue_loans(limit=5000)

    if not overdue_loan_ids:
        return "No overdue loans to process"

    # Fetch only the overdue loans (single query with IN clause)
    overdue_loans = Loan.objects.filter(
        pk__in=overdue_loan_ids,
        status=Loan.Status.ACTIVE  # Double-check status
    )

    count = 0
    failed = 0
    processed_ids = []

    for loan in overdue_loans.iterator(chunk_size=500):
        try:
            loan.mark_overdue()
            loan.save(update_fields=['status'])
            count += 1
            processed_ids.append(loan.pk)
        except TransitionNotAllowed:
            failed += 1

    # Remove processed loans from Redis
    if processed_ids:
        scheduler.remove_processed_loans(processed_ids)

    # Get stats for monitoring
    stats = scheduler.get_stats()

    return f"Marked {count} loans as overdue ({failed} failed). " \
           f"Scheduler stats: {stats}"


@shared_task
def sync_redis_scheduler():
    """
    Maintenance task: Sync DB with Redis in case of inconsistencies.
    Runs once per day to ensure Redis and DB are in sync.

    This handles edge cases like:
    - Redis server restart
    - Manual DB updates that bypassed Redis
    - Failed Redis operations during loan creation
    """
    scheduler = LoanScheduler()

    # Get all active loans from DB
    active_loans = Loan.objects.filter(
        status=Loan.Status.ACTIVE
    ).values_list('pk', 'due_date')

    # Reschedule all in Redis (overwrites existing)
    synced = 0
    for loan_id, due_date in active_loans:
        scheduler.reschedule_loan(loan_id, due_date)
        synced += 1

    # Get stats after sync
    stats = scheduler.get_stats()

    return f"Synced {synced} active loans to Redis scheduler. Stats: {stats}"


@shared_task
def mark_expired_reservations():
    """
    Mark all active reservations that have expired and restore book availability using FSM transitions.
    This task should run periodically (e.g., every 15 minutes).
    """
    expired_reservations = Reservation.objects.filter(
        status=Reservation.Status.ACTIVE,
        expires_at__lt=timezone.now()
    )

    count = 0
    failed = 0
    for reservation in expired_reservations:
        try:
            reservation.expire()
            reservation.save()
            count += 1
        except TransitionNotAllowed:
            failed += 1
            # Log the error or handle it appropriately
            continue

    return f"Marked {count} reservations as expired ({failed} failed)"


@shared_task
def expire_pending_transfers():
    """
    Expire all pending loan transfers that have exceeded 24 hours using FSM transitions.
    This task should run periodically (e.g., every hour or every 15 minutes).
    """
    expired_transfers = LoanTransfer.objects.filter(
        status=LoanTransfer.Status.PENDING,
        expires_at__lt=timezone.now()
    )

    count = 0
    failed = 0
    for transfer in expired_transfers:
        try:
            transfer.expire()
            transfer.save()
            count += 1
        except TransitionNotAllowed:
            failed += 1
            # Log the error or handle it appropriately
            continue

    return f"Expired {count} pending transfers ({failed} failed)"
