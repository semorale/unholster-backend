"""
Redis-based loan due date scheduler using sorted sets.
Provides event-driven scheduling for marking overdue loans.
"""
import redis
from django.conf import settings
from django.utils import timezone
from typing import List, Dict


class LoanScheduler:
    """
    Manages loan due dates in Redis sorted set for efficient overdue detection.

    Uses Redis sorted set where:
    - Member: 'loan:{id}'
    - Score: Unix timestamp of due_date

    This allows O(log N) queries to find overdue loans instead of O(N) table scans.
    """

    SORTED_SET_KEY = 'loans:due_dates'

    def __init__(self):
        """Initialize Redis connection."""
        redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
        self.redis = redis.from_url(
            redis_url,
            decode_responses=True
        )

    def schedule_loan(self, loan_id: int, due_date) -> bool:
        """
        Add a loan to the Redis sorted set with due_date as score.

        Args:
            loan_id: The loan ID to schedule
            due_date: datetime object of when loan is due

        Returns:
            True if added, False if already exists
        """
        timestamp = due_date.timestamp()
        result = self.redis.zadd(
            self.SORTED_SET_KEY,
            {f'loan:{loan_id}': timestamp},
            nx=True  # Only add if not exists
        )
        return bool(result)

    def reschedule_loan(self, loan_id: int, new_due_date) -> int:
        """
        Update the due date for an existing loan.

        Args:
            loan_id: The loan ID to reschedule
            new_due_date: datetime object of new due date

        Returns:
            Number of elements added (0 if updated, 1 if new)
        """
        timestamp = new_due_date.timestamp()
        result = self.redis.zadd(
            self.SORTED_SET_KEY,
            {f'loan:{loan_id}': timestamp}
        )
        return result

    def remove_loan(self, loan_id: int) -> bool:
        """
        Remove a loan from the scheduler (when returned/cancelled).

        Args:
            loan_id: The loan ID to remove

        Returns:
            True if removed, False if didn't exist
        """
        result = self.redis.zrem(self.SORTED_SET_KEY, f'loan:{loan_id}')
        return bool(result)

    def get_overdue_loans(self, limit: int = 1000) -> List[int]:
        """
        Get all loans that are past their due date.

        Uses ZRANGEBYSCORE to efficiently query only overdue loans.
        This is O(log N + M) where M is the number of overdue loans.

        Args:
            limit: Maximum number of overdue loans to return

        Returns:
            List of loan IDs that are overdue
        """
        now = timezone.now().timestamp()

        # Get all items with score (timestamp) <= now
        overdue_items = self.redis.zrangebyscore(
            self.SORTED_SET_KEY,
            '-inf',  # From earliest time
            now,     # To current time
            start=0,
            num=limit,
            withscores=False
        )

        # Extract loan IDs from 'loan:123' format
        loan_ids = []
        for item in overdue_items:
            try:
                loan_id = int(item.split(':')[1])
                loan_ids.append(loan_id)
            except (IndexError, ValueError):
                # Skip malformed entries
                continue

        return loan_ids

    def remove_processed_loans(self, loan_ids: List[int]) -> int:
        """
        Remove loans from Redis after they've been marked overdue.

        Args:
            loan_ids: List of loan IDs to remove

        Returns:
            Number of loans removed
        """
        if not loan_ids:
            return 0

        keys = [f'loan:{loan_id}' for loan_id in loan_ids]
        result = self.redis.zrem(self.SORTED_SET_KEY, *keys)
        return result

    def get_stats(self) -> Dict[str, int]:
        """
        Get scheduler statistics.

        Returns:
            Dictionary with:
                - total_scheduled: Total loans in scheduler
                - overdue_count: Number of overdue loans
        """
        total_scheduled = self.redis.zcard(self.SORTED_SET_KEY)
        overdue_count = len(self.get_overdue_loans())

        return {
            'total_scheduled': total_scheduled,
            'overdue_count': overdue_count
        }

    def get_next_due(self, limit: int = 5) -> List[Dict]:
        """
        Get the next loans that will become due (for monitoring/debugging).

        Args:
            limit: Number of upcoming due loans to return

        Returns:
            List of dicts with 'loan_id' and 'due_timestamp'
        """
        now = timezone.now().timestamp()

        # Get loans coming due soon
        upcoming = self.redis.zrangebyscore(
            self.SORTED_SET_KEY,
            now,      # From now
            '+inf',   # To future
            start=0,
            num=limit,
            withscores=True
        )

        result = []
        for item, score in upcoming:
            try:
                loan_id = int(item.split(':')[1])
                result.append({
                    'loan_id': loan_id,
                    'due_timestamp': score
                })
            except (IndexError, ValueError):
                continue

        return result

    def clear_all(self) -> int:
        """
        Clear all scheduled loans (use with caution, mainly for testing).

        Returns:
            Number of loans removed
        """
        return self.redis.delete(self.SORTED_SET_KEY)
