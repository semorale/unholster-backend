"""
Template-based views for the accounts app (Django Templates V1).
"""
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .models import User


class CustomLoginView(DjangoLoginView):
    """Custom login view."""

    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        """Redirect to home after successful login."""
        return reverse_lazy('home')

    def form_valid(self, form):
        """Add success message after login."""
        messages.success(self.request, f'Welcome back, {form.get_user().full_name}!')
        return super().form_valid(form)


class RegisterView(CreateView):
    """User registration view."""

    model = User
    template_name = 'accounts/register.html'
    fields = ['email', 'first_name', 'last_name', 'password']
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        """Create user with encrypted password."""
        user = form.save(commit=False)
        user.set_password(form.cleaned_data['password'])
        user.role = User.Role.LIBRARY_USER  # Default role
        user.save()

        messages.success(
            self.request,
            'Registration successful! Please login with your credentials.'
        )
        return redirect(self.success_url)


def logout_view(request):
    """Logout view."""
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('home')
