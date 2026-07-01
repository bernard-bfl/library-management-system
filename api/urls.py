from django.urls import path 
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    #auth
    path('auth/signup/', views.signup, name='signup'),
    path('auth/login/', views.login, name='login'),
    path('auth/login/verify-otp/', views.verify_otp, name='verify-otp'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/profile/', views.profile, name='profile'),


    #books
    path('books/', views.book_list_create, name='book-list-create'),
    path('books/<int:pk>/', views.book_detail, name='book-detail'),
    path('books/search/', views.book_search, name='book-search'),
]


