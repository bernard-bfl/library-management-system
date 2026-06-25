from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework import status
from rest_framework.response import Response
from .models import Book, Member, Bororwing, Reservation
from .serializers import BookSerializer, MemberSerializer, BorrowingSerializer, ReservationSerializer

# Create your views here.

@api_view(['GET', 'POST'])
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
def book_search(request):
    keyword = request.query_params.get('q', '')
    if not keyword:
        return Response({'error': 'Please provide a search keyword'}, status=status.HTTP_400_BAD_REQUEST)
    books = Book.objects.filter(title__icontains=keyword) | Book.objects.filter(author__icontains=keyword)
    serializer = BookSerializer(books, many=True)
    return Response(serializer.data)



