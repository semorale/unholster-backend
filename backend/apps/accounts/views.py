"""
Views for the accounts app.
"""
from django.contrib.auth import login, logout
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .permissions import IsLibrarian
from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)


@extend_schema_view(
    post=extend_schema(
        summary='Register a new user',
        description='Create a new user account with email and password.',
        tags=['Authentication']
    )
)
class RegisterView(generics.CreateAPIView):
    """View for user registration."""

    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer


@extend_schema_view(
    post=extend_schema(
        summary='Login user',
        description='Authenticate a user and create a session.',
        tags=['Authentication']
    )
)
class LoginView(APIView):
    """View for user login."""

    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        """Handle user login."""
        serializer = LoginSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        return Response(
            UserSerializer(user).data,
            status=status.HTTP_200_OK
        )


@extend_schema(
    summary='Logout user',
    description='Logout the current user and destroy the session.',
    tags=['Authentication']
)
class LogoutView(APIView):
    """View for user logout."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Handle user logout."""
        logout(request)
        return Response(
            {'detail': 'Successfully logged out.'},
            status=status.HTTP_200_OK
        )


@extend_schema(
    summary='Get current user',
    description='Retrieve the currently authenticated user information.',
    tags=['Authentication']
)
class CurrentUserView(APIView):
    """View to get current user information."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return current user data."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        summary='List all users',
        description='Get a list of all users (librarian only).',
        tags=['Users']
    ),
    retrieve=extend_schema(
        summary='Get user details',
        description='Retrieve details of a specific user (librarian only).',
        tags=['Users']
    ),
    update=extend_schema(
        summary='Update user',
        description='Update user information (librarian only).',
        tags=['Users']
    ),
    partial_update=extend_schema(
        summary='Partial update user',
        description='Partially update user information (librarian only).',
        tags=['Users']
    ),
    destroy=extend_schema(
        summary='Delete user',
        description='Delete a user (librarian only).',
        tags=['Users']
    )
)
class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for managing users (librarian only)."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsLibrarian]
    filterset_fields = ['role', 'is_active']
    search_fields = ['email', 'first_name', 'last_name']
    ordering_fields = ['created_at', 'email']

    @extend_schema(
        summary='Change password',
        description='Change the password for the current user.',
        request=ChangePasswordSerializer,
        tags=['Users']
    )
    @action(
        detail=False,
        methods=['post'],
        permission_classes=[IsAuthenticated],
        url_path='change-password'
    )
    def change_password(self, request):
        """Endpoint to change user password."""
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'detail': 'Password updated successfully.'},
            status=status.HTTP_200_OK
        )
