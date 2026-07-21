import os
import random
import uuid
import requests as http_requests

from django.core.cache import cache
from django.contrib.auth.models import User
from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from .models import Member, Reservation, Borrowing, Book, Payment
from .serializers import BookSerializer, MemberSerializer, BorrowingSerializer, ReservationSerializer, PaymentSerializer
from .email_service import send_otp_email
from .permissions import IsAdminOrReadOnly, IsAdminOnly
from datetime import date, timedelta
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

# define request bodies once as variables
SIGNUP_REQUEST = {
    'application/json': {
        'type': 'object',
        'properties': {
            'username': {'type': 'string'},
            'email': {'type': 'string'},
            'password': {'type': 'string'},
            'location': {'type': 'string'},
            'age': {'type': 'integer'},
        },
        'required': ['username', 'email', 'password', 'location', 'age']
    }
}

LOGIN_REQUEST = {
    'application/json': {
        'type': 'object',
        'properties': {
            'email': {'type': 'string'},
            'password': {'type': 'string'},
        },
        'required': ['email', 'password']
    }
}

VERIFY_OTP_REQUEST = {
    'application/json': {
        'type': 'object',
        'properties': {
            'email': {'type': 'string'},
            'otp': {'type': 'string'},
        },
        'required': ['email', 'otp']
    }
}

FORGOT_PASSWORD_REQUEST = {
    'application/json': {
        'type': 'object',
        'properties': {
            'email': {'type': 'string'},
        },
        'required': ['email']
    }
}

RESET_PASSWORD_REQUEST = {
    'application/json': {
        'type': 'object',
        'properties': {
            'email': {'type': 'string'},
            'new_password': {'type': 'string'},
        },
        'required': ['email', 'new_password']
    }
}

LOGOUT_REQUEST = {
    'application/json': {
        'type': 'object',
        'properties': {
            'refresh': {'type': 'string'},
        },
        'required': ['refresh']
    }
}

BOOK_REQUEST = {
    'application/json': {
        'type': 'object',
        'properties': {
            'title': {'type': 'string'},
            'author': {'type': 'string'},
            'published_year': {'type': 'string', 'format': 'date'},
            'is_available': {'type': 'boolean'},
        },
        'required': ['title', 'author', 'published_year']
    }
}

BORROW_REQUEST = {
    'application/json': {
        'type': 'object',
        'properties': {
            'book_id': {'type': 'integer'},
        },
        'required': ['book_id']
    }
}

PAYMENT_REQUEST = {
    'application/json': {
        'type': 'object',
        'properties': {
            'borrowing_id': {'type': 'integer'},
        },
        'required': ['borrowing_id']
    }
}




# Create your views here.

#authentication views
#POST/api/auth/signup
@extend_schema(request=SIGNUP_REQUEST, description='Register a new user account')
@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    location = request.data.get('location')
    age = request.data.get('age')

    #validation check for all fields
    if not all([username, email, password, location, age]):
        return Response(
            {'error': 'all fields are required: username, email, password, location, age'}, status=status.HTTP_400_BAD_REQUEST
        )
    
    #username validation 
    if User.objects.filter(username=username).exists():
        return Response(
            {'error': 'sorry, username already taken'}, status=status.HTTP_400_BAD_REQUEST )
    #email validation
    if User.objects.filter(email=email).exists():
        return Response(
            {'error': 'email already registered'}, status=status.HTTP_400_BAD_REQUEST )

    #creating user where here django hashes the password automatically
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password
    )

    #creating a linked member profile 
    Member.objects.create(
        user=user,
        location=location,
        age=age
    )

    #issuing tokens to users after a successful signup
    refresh = RefreshToken.for_user(user)

    return Response({
        'message': 'Account created successfully',
        'access': str(refresh.access_token),
        'refresh': str(refresh), }, status=status.HTTP_201_CREATED)

#POST/api/auth/login
@extend_schema(request=LOGIN_REQUEST, description='Login and receive OTP via email')
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    email = request.data.get('email')
    password = request.data.get('password')

    if not all([email, password]):
        return Response(
            {'error': 'email and password are required'}, status=status.HTTP_400_BAD_REQUEST )
    
    try: 
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response(
            {'error': 'invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED )
    
    if not user.check_password(password):
        return Response(
            {'error': 'invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED )
    
     # generate 6 digit OTP
    otp = str(random.randint(100000, 999999))

    # store in cache — expires in 5 minutes
    cache.set(f'otp_{email}', otp, timeout=300)

    # sending otp via EmailJS
    email_sent = send_otp_email(email, otp)
    if not email_sent:
        cache.delete(f'otp_{email}')
        return Response(
            {'error': 'failed to send OTP, please try again'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR )
    return Response({
        'message': 'OTP has been sent to your mail, please verify to complete login'}, status=status.HTTP_200_OK)


# POST /api/auth/login/verify-otp/
#second step; here we verify the otp and return jwt tokens
@extend_schema(request=VERIFY_OTP_REQUEST, description='Verify OTP and receive JWT tokens')
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    email = request.data.get('email')
    otp = request.data.get('otp')

    if not all([email, otp]):
        return Response(
            {'error': 'email and otp are required'}, status=status.HTTP_400_BAD_REQUEST )
    
    cached_otp = cache.get(f'otp_{email}')

    if cached_otp is None:
        return Response(
            {'error': 'OTP has expired, please login again'}, status=status.HTTP_400_BAD_REQUEST )

    if cached_otp != otp:
        return Response(
            {'error': 'invalid OTP'}, status=status.HTTP_400_BAD_REQUEST )
    
    # delete OTP immediately so it can't be reused
    cache.delete(f'otp_{email}')

    #here after logging in django tries to fetch the user profile
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response(
            {'error': 'user not found'}, status=status.HTTP_404_NOT_FOUND )
    
    refresh = RefreshToken.for_user(user)

    return Response({
        'message': f'Welcome back {user.username}',
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }, status=status.HTTP_200_OK)

#POST/api/auth/logout/
@extend_schema(request=LOGOUT_REQUEST, description='Logout and blacklist refresh token')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    refresh_token = request.data.get('refresh')
    if not refresh_token:
        return Response({'error': 'Sorry, refresh token is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
    except TokenError:
        return Response({'error': 'Oops invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)
    return Response({'message': 'logged out successfully'}, status=status.HTTP_200_OK)


#POST/api/auth/forgot-password
@extend_schema(request=FORGOT_PASSWORD_REQUEST, description='Request password reset OTP')
@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):
    email = request.data.get('email')
    if not email:
        return Response({'error': 'email is required'}, status=status.HTTP_400_BAD_REQUEST)
    #checking if user exists
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({'message': 'if an account with this email exists, an OTP has been sent'}, status=status.HTTP_200_OK)
    except User.MultipleObjectsReturned:
        return Response({'error': 'multiple accounts found with this email, please contact support'}, status=status.HTTP_400_BAD_REQUEST)
    
    otp = str(random.randint(100000, 999999))

    #store otp in cache for 5 mins 
    cache.set(f'forgot_password_otp_{email}', otp, timeout=300)
    email_sent = send_otp_email(email, otp)
    if not email_sent:
        cache.delete(f'forgot_password_otp_{email}')
        return Response({'error': 'failed to send OTP, please try again'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response({'message': 'if an account with that email exists, an OTP has been sent'}, status=status.HTTP_200_OK)


#POST/api/auth/forgot-password/verify-otp/
@extend_schema(request=VERIFY_OTP_REQUEST, description='Verify password reset OTP')
@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password_verify_otp(request):
    email = request.data.get('email')
    otp = request.data.get('otp')

    if not all([email, otp]):
        return Response({'error': 'email and otp are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    cached_otp = cache.get(f'forgot_password_otp{email}')

    if cached_otp is None:
        return Response({'error': 'OTP has expired, please request a new one...'}, status=status.HTTP_400_BAD_REQUEST)
    
    if cached_otp != otp:
        return Response({'error': 'invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)
    
    cache.delete(f'forgot_password_otp_{email}')
    cache.set(f'forgot_password_verified_{email}', True, timeout=300)
    return Response(
        {'message': 'OTP verified successfully, you can now reset your password'},
        status=status.HTTP_200_OK
    )

# POST /api/auth/forgot-password/reset/
@extend_schema(request=RESET_PASSWORD_REQUEST, description='Reset password with new password')
@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    email = request.data.get('email')
    new_password = request.data.get('new_password')

    if not all([email, new_password]):
        return Response(
            {'error': 'email and new_password are required'}, status=status.HTTP_400_BAD_REQUEST )
    
    # check if OTP was verified for this email
    verified = cache.get(f'forgot_password_verified_{email}')
    if not verified:
        return Response(
            {'error': 'please verify your OTP first before resetting password'}, status=status.HTTP_400_BAD_REQUEST )
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response(
            {'error': 'user not found'}, status=status.HTTP_404_NOT_FOUND )
    except User.MultipleObjectsReturned:
        return Response(
            {'error': 'multiple accounts found with this email, please contact support'}, status=status.HTTP_400_BAD_REQUEST )
    
    user.set_password(new_password)
    user.save()

    cache.delete(f'forgot_password_verified_{email}')

    return Response(
        {'message': 'password reset successfully, please login with your new password'}, status=status.HTTP_200_OK )

# GET /api/auth/profile/
# PUT /api/auth/profile/
@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def profile(request):
    try:
        member = Member.objects.get(user=request.user)
    except Member.DoesNotExist:
        return Response(
            {'error': 'member profile not found'}, status=status.HTTP_404_NOT_FOUND )
    
    if request.method == 'GET':
        serializer = MemberSerializer(member)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = MemberSerializer(member, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

#book views 
# GET /api/books/
# POST /api/books/
@extend_schema(methods=['GET'], description='List all books')
@extend_schema(methods=['POST'], request=BOOK_REQUEST, description='Add a new book - admin only')
@api_view(['GET', 'POST'])
@permission_classes([IsAdminOrReadOnly])
def book_list_create(request):
    if request.method == 'GET':
        books = Book.objects.all().order_by('id')
        serializer = BookSerializer(books, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = BookSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            #custom message along with the saved book data
            response_data = {
                "message": f"Book '{serializer.data.get('title')}' was successfully added to the library!",
                "data": serializer.data
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        #if validations fail, custom failure alert
        error_data = {
            "message": "Oops, failed to add book! sorry",
            "errors": serializer.errors
        }
        return Response(error_data, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(methods=['GET'], description='Get a single book')
@extend_schema(methods=['PUT'], request=BOOK_REQUEST, description='Update a book - admin only')
@extend_schema(methods=['DELETE'], description='Delete a book - admin only')
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAdminOrReadOnly])
def book_detail(request, pk):
    try:
        book = Book.objects.get(pk=pk)
    except Book.DoesNotExist:
        return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = BookSerializer(book)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = BookSerializer(book, data=request.data, partial=True) #partial=True means u can update just onme field
        if serializer.is_valid():
            serializer.save()
            #success response 
            response_data = {
                "message": f"Book ID {book.id} was successfully updated!",
                "data": serializer.data
            }
            return Response(response_data)
        
        #error response 
        error_data = {
            "message": "Update failed. Please check your data fields",
            "errors": serializer.errors
        }
        return Response(error_data, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        book.delete()
        return Response({'message': 'Book deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def book_search(request):
    keyword = request.query_params.get('q', '')
    if not keyword:
        return Response({'error': 'Please provide a search keyword'}, status=status.HTTP_400_BAD_REQUEST)
    books = Book.objects.filter(title__icontains=keyword) | Book.objects.filter(author__icontains=keyword)
    serializer = BookSerializer(books, many=True)
    return Response(serializer.data)


#POST/api/borrow
@extend_schema(request=BORROW_REQUEST, description='Borrow a book')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def borrow_book(request):
    book_id = request.data.get('book_id')
    
    if not book_id:
        return Response(
            {'error': 'book_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    #get the member profile of the logged user 
    try:
        member = Member.objects.get(user=request.user)
    except Member.DoesNotExist:
        return Response(
            {'error': "member profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    #get book 
    try:
        book = Book.objects.get(pk=book_id)
    except Book.DoesNotExist:
        return Response(
            {'error': 'Sorry, book not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    #checking if book is available
    if not book.is_available:
        return Response(
            {'error': 'Oops, book is not available, you can reserve it instead'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    #check if the member has an active borrowing for this book
    already_borrowed = Borrowing.objects.filter(
        book=book,
        member=member,
        returning_date__isnull=True
    ).exists()

    if already_borrowed:
        return Response(
            {'error': 'Sorry, you have already borrowed this book!'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    #creating a borrowing record 
    due_date = date.today() + timedelta(days=14)
    borrowing = Borrowing.objects.create(
        book=book,
        member=member,
        due_date=due_date
    )
    #marking the book as unavailable now after it has been borrowed
    book.is_available = False
    book.save()

    serializer = BorrowingSerializer(borrowing)
    return Response({
        'message': 'book has been borrowed successfully',
        'borrowing': serializer.data
    }, status=status.HTTP_201_CREATED)


#POST/api/return
@extend_schema(request=BORROW_REQUEST, description='Return a borrowed book')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def return_book(request):
    book_id = request.data.get('book_id')
    
    if not book_id:
        return Response(
            {'error': 'book_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    #get the member profile of the logged in user
    try:
        member = Member.objects.get(user=request.user)
    except Member.DoesNotExist:
        return Response(
            {'error': 'Sorry, member profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    #getting the book
    try:
        book = Book.objects.get(pk=book_id)
    except Book.DoesNotExist:
        return Response(
            {'error': 'Oops, book not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    #finding the active borrowing record for this member and book
    try:
        borrowing = Borrowing.objects.get(
            book=book,
            member=member,
            returning_date__isnull=True
            )
    except Borrowing.DoesNotExist:
        return Response(
            {'error': 'Sorry, no active borrowing found for this book'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    #setting return date to today 
    borrowing.returning_date = date.today()
    borrowing.save()

    book.is_available = True
    book.save()

    serializer = BorrowingSerializer(borrowing)
    return Response(
        {'message': 'book returned successfully',
         'borrowing': serializer.data},
         status=status.HTTP_200_OK
    )


#POST/api/renew/
@extend_schema(request=BORROW_REQUEST, description='Renew a borrowed book')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def renew_book(request):
    book_id = request.data.get('book_id')

    if not book_id:
        return Response(
            {'error': 'book_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        member = Member.objects.get(user=request.user)
    except Member.DoesNotExist:
        return Response(
            {'error': 'member profile not found'}, status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        book = Book.objects.get(pk=book_id)
    except Book.DoesNotExist:
        return Response(
            {'error': 'Sorry, book not found'}, status=status.HTTP_404_NOT_FOUND
        )
    
    #checking if theres an active borrowing for that book
    try:
        borrowing = Borrowing.objects.get(
            book=book, member=member, returning_date__isnull=True
        )
    except Borrowing.DoesNotExist:
        return Response(
            {'error': 'no active borrowing found for this book'}, status=status.HTTP_404_NOT_FOUND
        )
    
    has_reservation = Reservation.objects.filter(book=book, is_active=True).exists()
    if has_reservation:
        return Response(
            {'error': 'Oops, cannot renew, another member has reserved this book'}, status=status.HTTP_400_BAD_REQUEST
        )
    #extending due date by 14 days from today
    borrowing.due_date = date.today() + timedelta(days=14)
    borrowing.save()

    serializer = BorrowingSerializer(borrowing)
    return Response({
        'message': 'book renewed renewed successfully, new dute date is'  + str(borrowing.due_date),
        'borrowing': serializer.data
    }, status=status.HTTP_200_OK)

#POST/api/reserve
@extend_schema(request=BORROW_REQUEST, description='Reserve a book')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reserve_book(request):
    book_id = request.data.get('book_id')

    if not book_id:
        return Response(
            {'error': 'book_id is required'}, status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        member = Member.objects.get(user=request.user)
    except Member.DoesNotExist:
        return Response(
            {'error': 'member profile not found'}, status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        book = Book.objects.get(pk=book_id)
    except Book.DoesNotExist:
        return Response(
            {'error': 'Sorry, book not found'}, status=status.HTTP_404_NOT_FOUND
        )
    
    #users can only reserve a book that is currently borrowed
    if book.is_available:
        return Response(
            {'error': 'uhm book is currently available, you can borrow it directly!'}, status=status.HTTP_400_BAD_REQUEST
        )
    #checking if the member is the one who currently has the book borrowed
    already_borrowed_by_member = Borrowing.objects.filter(book=book, member=member, returning_date__isnull=True).exists()

    if already_borrowed_by_member:
        return Response({'error': 'you cannot reserve a book you have already borrwed'}, status=status.HTTP_400_BAD_REQUEST)
    #checking if member has an already active reservation
    already_reserved = Reservation.objects.filter(
        book=book, member=member, is_active=True
    ).exists()
    if already_reserved:
        return Response(
            {'error': 'you already got an active reservation for this book'}, status=status.HTTP_400_BAD_REQUEST
        )
    
    reservation = Reservation.objects.create(book=book, member=member,)
    serializer = ReservationSerializer(reservation)
    return Response({'message': 'book reserved successfully', 'reservation': serializer.data}, status=status.HTTP_201_CREATED)

#DELETE/api/reserve
@extend_schema(request=BORROW_REQUEST, description='Cancel a reservation')
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def cancel_reservation(request):
    book_id = request.data.get('book_id')
    if not book_id:
        return Response({'error': 'book_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        member = Member.objects.get(pk=book_id)
    except Book.DoesNotExist:
        return Response({'error': 'member profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    try:
        book = Book.objects.get(pk=book_id)
    except Book.DoesNotExist:
        return Response(
            {'error': 'book not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        reservation = Reservation.objects.get(book=book, member=member, is_active=True)
    except Reservation.DoesNotExist:
        return Response(
            {'error': 'n0 active reservation found for this book'}, status=status.HTTP_404_NOT_FOUND)
    
    #deactivate the reservation instead of del it 
    ##se we can keep record of it
    reservation.is_active = False
    reservation.save()

    return Response({'message': 'reservation cancelled successfully'}, status=status.HTTP_200_OK)


#GET/api/history/
@extend_schema(description='View borrowing history')
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def borrowing_history(request):
    try:
        member = Member.objects.get(user=request.user)
    except Member.DoesNotExist:
        return Response({'error': 'member profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    borrowings = Borrowing.objects.filter(member=member).order_by('borrowing_date')
    if not borrowings.exists():
        return Response({'message': 'Sorry, you got no borrowing history'}, status=status.HTTP_200_OK)
    
    serializer = BorrowingSerializer(borrowings, many=True)
    return Response({'message': 'borrowing history retrieved successfully', 'history': serializer.data}, status=status.HTTP_200_OK)



#helper function for calculating the fine 
def calculate_fine(borrowing):
    today = date.today()
    days_overdue = 0
    fine_amount = 0

    #so for book still out and overdue
    if borrowing.returning_date is None and borrowing.due_date < today:
        days_overdue = (today - borrowing.due_date).days
        fine_amount = days_overdue * 0.50

    #if book returned late
    elif borrowing.returning_date is not None and borrowing.due_date < borrowing.returning_date:
        days_overdue = (borrowing.returning_date - borrowing.due_date).days
        fine_amount = days_overdue * 0.50

    return {
        'days_overdue': days_overdue,
        'fine_amount': fine_amount,
    }


#GET/api/fines/
@extend_schema(description='View current fines')
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def view_fines(request):
    try:
        member = Member.objects.get(user=request.user)
    except Member.DoesNotExist:
        return Response({'error': 'Oops, member profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    #get all borrowings that are overdue
    #borrowing is overdue if due_date has passed and book has not been returned 
    borrowings = Borrowing.objects.filter(member=member)        

    fines = []
    total_fine = 0
    for borrowing in borrowings:
        fine = calculate_fine(borrowing)
        if fine['fine_amount'] > 0:
            fines.append({
                'book': borrowing.book.title,
                'due_date': borrowing.due_date,
                'days_overdue': fine['days_overdue'],
                'fine_amount': f'GHS {fine["fine_amount"]:.2f}',
            })
            total_fine += fine['fine_amount']

    if not fines:
        return Response(
            {'message': 'you have no fines'},
            status=status.HTTP_200_OK
        )
    
    return Response({
        'fines': fines,
        'total_fine': f'${total_fine:.2f}'
    }, status=status.HTTP_200_OK)



# GET /api/fines/history/
@extend_schema(description='View fine history with pagination, filtering and sorting')
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fine_history(request):
    try:
        member = Member.objects.get(user=request.user)
    except Member.DoesNotExist:
        return Response(
            {'error': 'member profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    borrowings = Borrowing.objects.filter(member=member)
    status_filter = request.query_params.get('status', None)
    sort_by = request.query_params.get('sort', '-borrowing_date')

    fines = []

    for borrowing in borrowings:
        fine = calculate_fine(borrowing)
        fine_amount = fine['fine_amount']
        days_overdue = fine['days_overdue']

        if fine_amount > 0:
            paid = Payment.objects.filter(
                borrowing=borrowing,
                status='success'
            ).exists()
            fine_status = 'paid' if paid else 'unpaid'
            fines.append({
                'borrowing_id': borrowing.id,
                'book': borrowing.book.title,
                'due_date': borrowing.due_date,
                'days_overdue': days_overdue,
                'fine_amount': f'GHS {fine_amount:.2f}',
                'fine_status': fine_status,
                'borrowing_date': borrowing.borrowing_date,
                'returning_date': borrowing.returning_date,
            })
        
    #apply status filter
    if status_filter in ['paid', 'unpaid']:
        fines = [f for f in fines if f['fine_status'] == status_filter]

    # apply sorting
    reverse = True
    sort_key = 'borrowing_date'

    if sort_by == 'borrowing_date':
        sort_key = 'borrowing_date'
        reverse = False
    elif sort_by == '-borrowing_date':
        sort_key = 'borrowing_date'
        reverse = True
    elif sort_by == 'fine_amount':
        sort_key = 'fine_amount'
        reverse = False
    elif sort_by == '-fine_amount':
        sort_key = 'fine_amount'
        reverse = True
    elif sort_by == 'days_overdue':
        sort_key = 'days_overdue'
        reverse = False
    elif sort_by == '-days_overdue':
        sort_key = 'days_overdue'
        reverse = True

    fines = sorted(fines, key=lambda x: x[sort_key], reverse=reverse)

    # pagination
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 10))
    start = (page - 1) * page_size
    end = start + page_size
    paginated_fines = fines[start:end]

    return Response({
        'total_fines': len(fines),
        'page': page,
        'page_size': page_size,
        'total_pages': (len(fines) + page_size - 1) // page_size,
        'fines': paginated_fines,
    }, status=status.HTTP_200_OK)
    











# GET /api/users/
@extend_schema(description='List all users - admin only')
@api_view(['GET'])
@permission_classes([IsAdminOnly])
def list_users(request):
    members = Member.objects.all().order_by('id')

    if not members.exists():
        return Response(
            {'message': 'no users found'},
            status=status.HTTP_200_OK
        )
    
    serializer = MemberSerializer(members, many=True)
    return Response({
        'message': 'users retrieved successfully',
        'users': serializer.data
    }, status=status.HTTP_200_OK)

# PUT /api/users/<id>/
@extend_schema(description='Update a user - admin only')
@api_view(['PUT'])
@permission_classes([IsAdminOnly])
def update_user(request, pk):
    try:
        member = Member.objects.get(pk=pk)
    except Member.DoesNotExist:
        return Response(
            {'error': 'user not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    serializer = MemberSerializer(member, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'user updated successfully',
            'user': serializer.data
        }, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# DELETE /api/users/<id>/
@extend_schema(description='Delete a user - admin only')
@api_view(['DELETE'])
@permission_classes([IsAdminOnly])
def delete_user(request, pk):
    try:
        member = Member.objects.get(pk=pk)
    except Member.DoesNotExist:
        return Response(
            {'error': 'user not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
     # delete the linked User object — this cascades and deletes the Member too
    member.user.delete()
    return Response(
        {'message': 'user deleted successfully'},
        status=status.HTTP_204_NO_CONTENT
    )


#POST/api/payments
@extend_schema(request=PAYMENT_REQUEST, description='Initialize Paystack payment for a fine')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initialize_payment(request):
    borrowing_id = request.data.get('borrowing_id')
    if not borrowing_id:
        return Response({'error': 'borrowing_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        member = Member.objects.get(user=request.user)
    except Member.DoesNotExist:
        return Response({'error': 'member profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    try:
        borrowing = Borrowing.objects.get(pk=borrowing_id, member=member)
    except Borrowing.DoesNotExist:
        return Response({'error': 'borrowing record not found'}, status=status.HTTP_404_NOT_FOUND)
    
    fine = calculate_fine(borrowing)
    fine_amount = fine['fine_amount']

    if fine_amount == 0:
        return Response(
        {'message': 'you have no fine for this borrowing'},
        status=status.HTTP_200_OK
    )
    #checking if fine has already been paid
    already_paid = Payment.objects.filter(borrowing=borrowing, status='success').exists()
    if already_paid:
        return Response({'message': 'uhm sorry fine for this borrowing has already been paid'}, status=status.HTTP_400_BAD_REQUEST)
    
    # generate a unique reference for this transaction
    reference = str(uuid.uuid4()).replace('-', '')[:20]

     # initialize payment with Paystack
    headers = {
        'Authorization': f'Bearer {os.getenv("PAYSTACK_SECRET_KEY")}',
        'Content-Type': 'application/json',
    }
    payload = {
        'email': request.user.email,
        'amount': int(fine_amount * 100),  # convert to pesewas
        'reference': reference,
        'callback_url': 'http://127.0.0.1:8000/api/payments/verify/',
        'metadata': {
            'borrowing_id': borrowing_id,
            'member_id': member.id,
        }
    }
    response = http_requests.post(
        'https://api.paystack.co/transaction/initialize',
        json=payload,
        headers=headers
    )
    if response.status_code != 200:
        return Response(
            {'error': 'failed to initialize payment, please try again'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    response_data = response.json()

    # create a pending payment record
    Payment.objects.create(
        member=member,
        borrowing=borrowing,
        amount=fine_amount,
        reference=reference,
        status='pending'
    )

    return Response({
        'message': 'payment initialized successfully',
        'payment_url': response_data['data']['authorization_url'],
        'reference': reference,
        'amount': f'GHS {fine_amount:.2f}',
    }, status=status.HTTP_200_OK)


#GET/api/payments/verify/<reference>/
@extend_schema(description='Verify Paystack payment status')
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verify_payment(request, reference):
    headers = {
        'Authorization': f'Bearer {os.getenv("PAYSTACK_SECRET_KEY")}',
        'Content-Type': 'application/json'
    }
    response = http_requests.get(
        f'https://api.paystack.co/transaction/verify/{reference}',
        headers=headers
    )
    if response.status_code != 200:
        return Response({'error': 'failed to verify payment'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    response_data = response.json()
    paystack_status = response_data['data']['status']

    try:
        payment = Payment.objects.get(reference=reference)
    except Payment.DoesNotExist:
        return Response({'error': 'payment record not found'})
    
    if paystack_status == 'success':
        payment.status = 'success'
        payment.save()
        return Response({
            'message': 'payment verified successfully',
            'reference': reference,
            'amount': f'GHS {payment.amount:.2f}',
            'status': 'success'
            }, status=status.HTTP_200_OK)
    else:
        payment.status = 'failed'
        payment.save()
        return Response({
            'message': 'payment failed or not completed',
            'status': paystack_status,
        }, status=status.HTTP_400_BAD_REQUEST)

