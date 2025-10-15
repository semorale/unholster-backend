"""
Serializers for the books app.
"""
from rest_framework import serializers

from .models import Book


class BookSerializer(serializers.ModelSerializer):
    """Serializer for Book model."""

    created_by_email = serializers.EmailField(
        source='created_by.email',
        read_only=True
    )
    is_available = serializers.ReadOnlyField()
    borrowed_count = serializers.ReadOnlyField()

    class Meta:
        model = Book
        fields = [
            'id', 'isbn', 'title', 'author', 'description',
            'quantity', 'available_quantity', 'is_available',
            'borrowed_count', 'created_by', 'created_by_email',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        """Set created_by to current user and set initial available_quantity."""
        validated_data['created_by'] = self.context['request'].user
        # Set available_quantity equal to quantity on creation
        if 'available_quantity' not in validated_data:
            validated_data['available_quantity'] = validated_data.get('quantity', 1)
        return super().create(validated_data)


class BookListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for book list view."""

    is_available = serializers.ReadOnlyField()

    class Meta:
        model = Book
        fields = [
            'id', 'isbn', 'title', 'author',
            'quantity', 'available_quantity', 'is_available'
        ]


class BookAvailabilitySerializer(serializers.ModelSerializer):
    """Serializer for checking book availability."""

    is_available = serializers.ReadOnlyField()
    borrowed_count = serializers.ReadOnlyField()

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'quantity', 'available_quantity',
            'is_available', 'borrowed_count'
        ]
