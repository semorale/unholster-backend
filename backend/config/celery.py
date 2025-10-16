"""
Celery configuration for biblioteca project.
"""
import os

from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('biblioteca')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Configure periodic tasks
app.conf.beat_schedule = {
    # Event-driven overdue detection: Can run every minute (very efficient with Redis)
    'check-overdue-loans-event-driven': {
        'task': 'apps.loans.tasks.mark_overdue_loans',
        'schedule': crontab(minute='*/1'),  # Every minute
    },
    # Daily sync to ensure Redis and DB consistency
    'sync-redis-scheduler-daily': {
        'task': 'apps.loans.tasks.sync_redis_scheduler',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily
    },
    # Reservations (unchanged)
    'mark-expired-reservations-every-15-minutes': {
        'task': 'apps.loans.tasks.mark_expired_reservations',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    # Loan transfers expiry
    'expire-pending-transfers-every-hour': {
        'task': 'apps.loans.tasks.expire_pending_transfers',
        'schedule': crontab(minute=0),  # Every hour
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery is working."""
    print(f'Request: {self.request!r}')
