"""
User model for the biblioteca application.
"""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user with the given email and password."""
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.LIBRARIAN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    Supports two roles: librarian and library_user.
    """

    class Role(models.TextChoices):
        LIBRARIAN = 'librarian', _('Librarian')
        LIBRARY_USER = 'library_user', _('Library User')

    # Remove username field - we'll use email for authentication
    username = None
    email = models.EmailField(_('email address'), unique=True)

    # Custom fields
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.LIBRARY_USER,
        help_text=_('User role in the system')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    class Meta:
        db_table = 'users'
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    @property
    def is_librarian(self):
        """Check if user is a librarian."""
        return self.role == self.Role.LIBRARIAN

    @property
    def is_library_user(self):
        """Check if user is a library user."""
        return self.role == self.Role.LIBRARY_USER

    @property
    def full_name(self):
        """Return user's full name."""
        return f"{self.first_name} {self.last_name}".strip() or self.email
