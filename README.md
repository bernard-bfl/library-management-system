# Library Management System API

A RESTful API for managing a library system built with Django REST Framework. It supports user authentication with MFA, book management, borrowing, reservations, fines, and payments via Paystack.

---

## Tech Stack

- **Backend:** Django, Django REST Framework
- **Database:** PostgreSQL
- **Authentication:** JWT (via djangorestframework-simplejwt)
- **Email:** EmailJS (OTP delivery)
- **Payments:** Paystack

---

## Getting Started

### Prerequisites
- Python 3.10+
- PostgreSQL
- A Paystack account (for payments)
- An EmailJS account (for OTP emails)

### Installation

```bash
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
```

### Environment Variables

Create a `.env` file in the root directory with the following:

```
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432

EMAILJS_SERVICE_ID=your_emailjs_service_id
EMAILJS_TEMPLATE_ID=your_emailjs_template_id
EMAILJS_FORGOT_PASSWORD_TEMPLATE_ID=your_forgot_password_template_id
EMAILJS_PUBLIC_KEY=your_emailjs_public_key
EMAILJS_PRIVATE_KEY=your_emailjs_private_key

PAYSTACK_SECRET_KEY=your_paystack_secret_key
PAYSTACK_PUBLIC_KEY=your_paystack_public_key
```

---

## Roles

| Role | Description |
|------|-------------|
| Superuser | Full access including Django admin dashboard |
| Admin (is_staff=True) | Can manage books and users |
| Member (is_staff=False) | Can borrow, return, reserve books and pay fines |

---

## API Endpoints

### Authentication

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/api/auth/signup/` | Register a new account | Public |
| POST | `/api/auth/login/` | Login and receive OTP | Public |
| POST | `/api/auth/login/verify-otp/` | Verify OTP and receive JWT tokens | Public |
| POST | `/api/auth/token/refresh/` | Refresh access token | Public |
| GET | `/api/auth/profile/` | View profile | Authenticated |
| PUT | `/api/auth/profile/` | Update profile | Authenticated |
| POST | `/api/auth/logout/` | Logout and blacklist refresh token | Authenticated |
| POST | `/api/auth/forgot-password/` | Request password reset OTP | Public |
| POST | `/api/auth/forgot-password/verify-otp/` | Verify password reset OTP | Public |
| POST | `/api/auth/forgot-password/reset/` | Reset password | Public |

---

### Books

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/api/books/` | List all books | Authenticated |
| POST | `/api/books/` | Add a new book | Admin only |
| GET | `/api/books/<id>/` | Get a single book | Authenticated |
| PUT | `/api/books/<id>/` | Update a book | Admin only |
| DELETE | `/api/books/<id>/` | Delete a book | Admin only |
| GET | `/api/books/search/?q=keyword` | Search books by title or author | Authenticated |

---

### Borrowing

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/api/borrow/` | Borrow a book | Authenticated |
| POST | `/api/return/` | Return a borrowed book | Authenticated |
| POST | `/api/renew/` | Renew a borrowed book | Authenticated |

#### Borrow a Book
```json
POST /api/borrow/
{
    "book_id": 1
}
```

#### Return a Book
```json
POST /api/return/
{
    "book_id": 1
}
```

#### Renew a Book
```json
POST /api/renew/
{
    "book_id": 1
}
```
> Renewal is not allowed if another member has an active reservation for the book.

---

### Reservations

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/api/reserve/` | Reserve a borrowed book | Authenticated |
| DELETE | `/api/reserve/cancel/` | Cancel a reservation | Authenticated |

#### Reserve a Book
```json
POST /api/reserve/
{
    "book_id": 1
}
```
> You can only reserve a book that is currently borrowed by someone else.

---

### History & Fines

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/api/history/` | View borrowing history | Authenticated |
| GET | `/api/fines/` | View current fines | Authenticated |
| GET | `/api/fines/history/` | View fine history with filters | Authenticated |

#### Fine History Query Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `status` | Filter by paid or unpaid | `?status=paid` |
| `sort` | Sort results | `?sort=fine_amount` or `?sort=-days_overdue` |
| `page` | Page number | `?page=1` |
| `page_size` | Results per page | `?page_size=10` |

> Fine rate: **GHS 0.50 per day overdue**

---

### Payments

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/api/payments/` | Initialize Paystack payment for a fine | Authenticated |
| GET | `/api/payments/verify/<reference>/` | Verify payment status | Authenticated |

#### Initialize Payment
```json
POST /api/payments/
{
    "borrowing_id": 1
}
```
Returns a `payment_url` — redirect the user to this URL to complete payment on Paystack's hosted page.

#### Verify Payment
```
GET /api/payments/verify/abc123def456/
```
Call this after the user completes payment to confirm and update the payment status.

---

### Admin User Management

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/api/users/` | List all users | Admin only |
| PUT | `/api/users/<id>/update/` | Update a user | Admin only |
| DELETE | `/api/users/<id>/delete/` | Delete a user | Admin only |

---

## Authentication Flow

All protected endpoints require a JWT access token in the Authorization header:

```
Authorization: Bearer <access_token>
```

### Login Flow (MFA)
1. `POST /api/auth/login/` with email and password
2. Check your email for a 6-digit OTP (expires in 5 minutes)
3. `POST /api/auth/login/verify-otp/` with email and OTP
4. Receive `access` and `refresh` tokens

### Token Refresh
When the access token expires (after 30 minutes), use the refresh token:
```json
POST /api/auth/token/refresh/
{
    "refresh": "<refresh_token>"
}
```

### Forgot Password Flow
1. `POST /api/auth/forgot-password/` with your email
2. Check your email for a 6-digit OTP
3. `POST /api/auth/forgot-password/verify-otp/` with email and OTP
4. `POST /api/auth/forgot-password/reset/` with email and new password

---

## Notes

- Due date for borrowed books is set to **14 days** from the borrowing date
- Fines are calculated at **GHS 0.50 per day overdue**
- OTPs expire in **5 minutes**
- Access tokens expire in **30 minutes**
- Refresh tokens expire in **1 day**
- Paystack test card: `4084 0840 8408 4081`, CVV: `408`, OTP: `123456`



