Library Management System API

A RESTful API for managing a library system built with Django REST Framework. It supports user authentication with MFA, book management, borrowing, reservations, fines, and payments via Paystack.

Tech Stack


Backend: Django, Django REST Framework
Database: PostgreSQL
Authentication: JWT (via djangorestframework-simplejwt)
Email: EmailJS (OTP delivery)
Payments: Paystack

Getting Started

Prerequisites

Python 3.10+
PostgreSQL
A Paystack account (for payments)
An EmailJS account (for OTP emails)

Installation
# clone the repository
git clone https://github.com/bernard-bfl/library-management-system.git
cd library-management-system

# create and activate virtual environment
python -m venv venv
venv\Scripts\Activate.ps1  # Windows PowerShell

# install dependencies
pip install -r requirements.txt

# set up environment variables
cp .env.example .env
# fill in your values in .env

# run migrations
python manage.py migrate

# create a superuser
python manage.py createsuperuser

# start the server
python manage.py runserver


