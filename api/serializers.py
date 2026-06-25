from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Book, Member, Bororwing, Reservation


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['id', 'title', 'published_year', 'is_available']

class MemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Member
        fields = ['id', 'user', 'membership_date', 'location', 'age']

class BorrowingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bororwing
        fields = ['id', 'book', 'member', 'borrowing_date', 'due_date', 'returning_date']

class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = ['id', 'book', 'member', 'reserved_at', 'is_active']
