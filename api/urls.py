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

    # forgot password
    path('auth/logout/', views.logout, name='logout'),
    path('auth/forgot-password/', views.forgot_password, name='forgot-password'),
    path('auth/forgot-password/verify-otp/', views.forgot_password_verify_otp, name='forgot-password-verify-otp'),
    path('auth/forgot-password/reset/', views.reset_password, name='reset-password'),


    #books
    path('books/', views.book_list_create, name='book-list-create'),
    path('books/<int:pk>/', views.book_detail, name='book-detail'),
    path('books/search/', views.book_search, name='book-search'),

    #borrow, return, renew
    path('borrow/', views.borrow_book, name='borrow-book'),
    path('return/', views.return_book, name='return-book'),
    path('renew/', views.renew_book, name='renew-book'),

    #reservations
    path('reserve/', views.reserve_book, name='reserve-book'),
    path('reserve/cancel/', views.cancel_reservation, name='cancel-reservation'),

    # history and fines
    path('history/', views.borrowing_history, name='borrowing-history'),
    path('fines/', views.view_fines, name='view-fines'),
    

    # admin user management
    path('users/', views.list_users, name='list-users'),
    path('users/<int:pk>/update/', views.update_user, name='update-user'),
    path('users/<int:pk>/delete/', views.delete_user, name='delete-user'),

    # payments
    path('payments/', views.initialize_payment, name='initialize-payment'),
    path('payments/verify/<str:reference>/', views.verify_payment, name='verify-payment'),

    # fine history
    path('fines/history/', views.fine_history, name='fine-history'),

    ]



