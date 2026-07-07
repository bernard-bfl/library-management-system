import os
import random
from django.core.cache import cache
from django.contrib.auth.models import User
from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Book, Member, Reservation, Borrowing
from .serializers import BookSerializer, MemberSerializer, BorrowingSerializer, ReservationSerializer
from .email_service import send_otp_email
from .permissions import IsAdminOrReadOnly, IsAdminOnly
from datetime import date, timedelta

# Create your views here.

#authentication views
#POST/api/auth/signup
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
            {'error': 'all fields are required: username, email, password, location, age'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    #username validation 
    if User.objects.filter(username=username).exists():
        return Response(
            {'error': 'sorry, username already taken'},
            status=status.HTTP_400_BAD_REQUEST
        )
    #email validation
    if User.objects.filter(email=email).exists():
        return Response(
            {'error': 'email already registered'},
            status=status.HTTP_400_BAD_REQUEST
        )

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
        'refresh': str(refresh),
    }, status=status.HTTP_201_CREATED)

#POST/api/auth/login
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    email = request.data.get('email')
    password = request.data.get('password')

    if not all([email, password]):
        return Response(
            {'error': 'email and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response(
            {'error': 'invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    if not user.check_password(password):
        return Response(
            {'error': 'invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
     # generate 6 digit OTP
    otp = str(random.randint(100000, 999999))

    # store in cache — expires in 5 minutes
    cache.set(f'otp_{email}', otp, timeout=300)

    # sending otp via EmailJS
    email_sent = send_otp_email(email, otp)
    if not email_sent:
        cache.delete(f'otp_{email}')
        return Response(
            {'error': 'failed to send OTP, please try again'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    return Response({
        'message': 'OTP has been sent to your mail, please verify to complete login'
    }, status=status.HTTP_200_OK)



# POST /api/auth/login/verify-otp/
#second step; here we verify the otp and return jwt tokens
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    email = request.data.get('email')
    otp = request.data.get('otp')

    if not all([email, otp]):
        return Response(
            {'error': 'email and otp are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    cached_otp = cache.get(f'otp_{email}')

    if cached_otp is None:
        return Response(
            {'error': 'OTP has expired, please login again'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if cached_otp != otp:
        return Response(
            {'error': 'invalid OTP'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # delete OTP immediately so it can't be reused
    cache.delete(f'otp_{email}')

    #here after logging in django tries to fetch the user profile
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response(
            {'error': 'user not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    refresh = RefreshToken.for_user(user)

    return Response({
        'message': f'Welcome back {user.username}',
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }, status=status.HTTP_200_OK)



# GET /api/auth/profile/
# PUT /api/auth/profile/
@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def profile(request):
    try:
        member = Member.objects.get(user=request.user)
    except Member.DoesNotExist:
        return Response(
            {'error': 'member profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
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
@api_view(['GET', 'POST'])
@permission_classes([IsAdminOrReadOnly])
def book_list_create(request):
    if request.method == 'GET':
        books = Book.ojects.all().order_by('id')
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
    except Book.DoesNotExist:
        return Response(
            {'error': 'Sorry, no active borrowing found for this book'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    #setting return date to today 
    borrowing.return_date = date.today()
    borrowing.save()

    book.is_available = True
    book.save()

    serializer = BookSerializer(borrowing)
    return Response(
        {'message': 'book returned successfully',
         'borrowing': serializer.data},
         status=status.HTTP_200_OK
    )


#POST/api/renew/
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
        'message': 'book renewed renewed successfully, new dute date is' + str(borrowing.due_date),
        'borrowing': serializer.data
    }, status=status.HTTP_200_OK)

#POST/api/reserve
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
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def cancel_reservation(request):
    book_id = request.data.get('book_id')
    if not book_id:
        return Response({'error': 'book_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        member = Member.objects.get(pk=book_id)
    except Book.DoesNotExist:
        return Response({'error': 'book not found'}, status=status.HTTP_404_NOT_FOUND)
    
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


        