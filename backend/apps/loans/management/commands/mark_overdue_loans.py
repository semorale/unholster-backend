"""
Management command to mark overdue loans using Redis scheduler.
This command should be run periodically (e.g., every minute via cron or Celery Beat).
"""
import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from django_fsm import TransitionNotAllowed

from apps.loans.models import Loan
from apps.loans.redis_scheduler import LoanScheduler

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Mark overdue loans using Redis scheduler'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=1000,
            help='Maximum number of overdue loans to process in one run',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate the operation without making changes',
        )

    def handle(self, *args, **options):
        limit = options['limit']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        try:
            scheduler = LoanScheduler()

            # Get overdue loan IDs from Redis
            overdue_ids = scheduler.get_overdue_loans(limit=limit)

            if not overdue_ids:
                self.stdout.write(self.style.SUCCESS('No overdue loans found'))
                return

            self.stdout.write(f'Found {len(overdue_ids)} overdue loan(s)')

            # Process each overdue loan
            marked_count = 0
            error_count = 0
            already_overdue_count = 0

            for loan_id in overdue_ids:
                try:
                    loan = Loan.objects.get(id=loan_id)

                    # Check if already marked as overdue
                    if loan.status == Loan.Status.OVERDUE:
                        already_overdue_count += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f'  Loan #{loan_id} already marked as OVERDUE'
                            )
                        )
                        # Remove from Redis since it's already processed
                        if not dry_run:
                            scheduler.remove_loan(loan_id)
                        continue

                    # Check if loan was returned
                    if loan.status == Loan.Status.RETURNED:
                        self.stdout.write(
                            self.style.WARNING(
                                f'  Loan #{loan_id} already RETURNED, removing from Redis'
                            )
                        )
                        if not dry_run:
                            scheduler.remove_loan(loan_id)
                        continue

                    # Mark as overdue using FSM transition
                    if loan.status == Loan.Status.ACTIVE:
                        if not dry_run:
                            with transaction.atomic():
                                try:
                                    loan.mark_overdue()
                                    loan.save()
                                    marked_count += 1
                                    self.stdout.write(
                                        self.style.SUCCESS(
                                            f'  ✓ Marked loan #{loan_id} as OVERDUE '
                                            f'(Book: {loan.book.title}, User: {loan.user.email})'
                                        )
                                    )
                                except TransitionNotAllowed as e:
                                    error_count += 1
                                    self.stdout.write(
                                        self.style.ERROR(
                                            f'  ✗ FSM transition failed for loan #{loan_id}: {e}'
                                        )
                                    )
                        else:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'  [DRY RUN] Would mark loan #{loan_id} as OVERDUE '
                                    f'(Book: {loan.book.title}, User: {loan.user.email})'
                                )
                            )
                            marked_count += 1

                except Loan.DoesNotExist:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f'  ✗ Loan #{loan_id} not found in database, removing from Redis'
                        )
                    )
                    if not dry_run:
                        scheduler.remove_loan(loan_id)
                except Exception as e:
                    error_count += 1
                    logger.exception(f'Error processing loan #{loan_id}')
                    self.stdout.write(
                        self.style.ERROR(
                            f'  ✗ Error processing loan #{loan_id}: {str(e)}'
                        )
                    )

            # Summary
            self.stdout.write('\n' + '='*60)
            self.stdout.write(self.style.SUCCESS(f'Summary:'))
            self.stdout.write(f'  Total overdue loans found: {len(overdue_ids)}')
            self.stdout.write(
                self.style.SUCCESS(f'  Successfully marked as overdue: {marked_count}')
            )
            if already_overdue_count > 0:
                self.stdout.write(
                    self.style.WARNING(f'  Already marked as overdue: {already_overdue_count}')
                )
            if error_count > 0:
                self.stdout.write(
                    self.style.ERROR(f'  Errors: {error_count}')
                )

            # Get updated stats
            stats = scheduler.get_stats()
            self.stdout.write(f'\nRedis Scheduler Stats:')
            self.stdout.write(f'  Total scheduled loans: {stats["total_scheduled"]}')
            self.stdout.write(f'  Remaining overdue: {stats["overdue_count"]}')

        except Exception as e:
            logger.exception('Error in mark_overdue_loans command')
            self.stdout.write(
                self.style.ERROR(f'Command failed: {str(e)}')
            )
            raise
