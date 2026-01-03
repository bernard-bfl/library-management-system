from libraryms1 import get_connection

books_table = """CREATE TABLE IF NOT EXISTS books (
id SERIAL PRIMARY KEY,
title VARCHAR(60),
author VARCHAR(60),
published_year DATE,
is_available BOOLEAN DEFAULT TRUE
);"""

members_table = """CREATE TABLE IF NOT EXISTS members (
id SERIAL PRIMARY KEY,
name VARCHAR(60),
membership_date DATE,
email VARCHAR(60),
location VARCHAR(30),
age VARCHAR(5)
);"""

borrowings_table ="""CREATE TABLE IF NOT EXISTS borrowings (
id SERIAL PRIMARY KEY,
book_id INTEGER REFERENCES books(id),
member_id INTEGER REFERENCES members(id),
borrowing_date DATE,
returning_date DATE
);"""

def initialize():
    #this creates the books, members and borrowings table
    conn =get_connection()
    cur = conn.cursor()
    try:
        cur.execute(books_table)
        cur.execute(members_table)
        cur.execute(borrowings_table)
        conn.commit()
        print(f"Tables created successfully")
        if cur:
            cur.close()
        if conn:
            conn.close()
    except Exception as e:
        print(f"Sorry, error creating tables", e)
        conn.rollback()

def add_book(title, author, published_year):
    #this adds a book to the library
    try:
        conn = get_connection()
        cur = conn.cursor()
        sql = """INSERT INTO books (title, author, published_year) VALUES (%s, %s, %s) RETURNING id;"""
        cur.execute(sql, (title, author, published_year))
        new_id = cur.fetchone()[0]
        conn.commit()
        print(f"Yay, book added with id = {new_id}")
        if cur:
            cur.close()
        if conn:
            conn.close()
    except Exception as e:
        print(f"Error adding book to library", e)
        conn.rollback()
    
def list_books():
    #this lists the books in the library
    sql = """SELECT id, title, author, published_year FROM books ORDER BY id;"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(sql,)
        rows = cur.fetchall()
        if not rows:
            print(f"No book found")
        print(f"id | title | author | published_year")
        for r in rows:
            print(f"{r[0]} | {r[1]} | {r[2]} | {r[3]}")
        if cur:
            cur.close()
        if conn:
            conn.close()
    except Exception as e:
        print(f"Sorry, unable to list books", e)
        conn.rollback()
    
def search_book(keyword):
    #this searches for a book in the library with your provided keyword
    sql = """SELECT title, author, published_year FROM books WHERE title ILIKE %s OR author LIKE %s ORDER BY title;"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(sql, (f"%{keyword}%", f"%{keyword}%"))
        rows = cur.fetchall()
        if not rows:
            print(f"Oops, no book found with a keyword like that")
            return
        for r in rows:
            print(r)
        if cur:
            cur.close()
        if conn:
            conn.close()
    except Exception as e:
        print(f"Error matching a book like that", e)
        conn.rollback()

def update_book(id, title=None, author=None, published_year=None):
    conn = get_connection()
    cur = conn.cursor()
    try:
        updates = []
        value = []
        if title is not None:
            updates.append("title = %s")
            value.append(title)
        if author is not None:
            updates.append("author = %s")
            value.append(author)
        if published_year is not None:
            updates.append("year = %s")
            value.append(published_year)
        if not updates:
            print(f"Sorry, nothing to update")
            return
        value.append(id)
        sql = "UPDATE books SET title =%s, author = %s, published_year = %s WHERE id = %s;"
        cur.execute(sql, (title, author, published_year, id))
        conn.commit()
        print(f"Book successfully updated")
        if cur:
            cur.close()
        if conn:
            conn.close()
    except Exception as e:
        print(f"Sorry, error updating book", e)
        conn.rollback()

def delete_book(id):
    conn = get_connection()
    cur = conn.cursor()
    sql = """DELETE FROM books WHERE id =%s;"""
    try:
        cur.execute(sql, (id,))
        conn.commit()
        print(f"Book has been deleted from the library system")
        if cur:
            cur.close()
        if conn:
            conn.close()
    except Exception as e:
        print(f"Oops book was unable to be deleted from the library system", e)
        conn.rollback()
def add_member(name, membership_date, email, location, age):
    #this adds a member of the library  to the system
    conn = get_connection()
    cur = conn.cursor()
    sql = """INSERT INTO members (name, membership_date, email, location, age) VALUES (%s, %s, %s, %s, %s) 
            RETURNING id;"""
    try:
        cur.execute(sql, (name, membership_date, email, location, age))
        new_id = cur.fetchone()[0]
        print(f"New member has been added with id = {new_id}")
        conn.commit()
        if cur:
            cur.close()
        if conn:
            conn.close()
    except Exception as e:
        print(f"Oops, unable to add member",e)
def list_members():
    #here we list all the members of the library
    sql = """SELECT id, name, membership_date, email, location, age FROM members ORDER BY id;"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql)
        rows = cur.fetchall()
        if not rows:
            print(f"Sorry, no member found")
        print(f"id | name | membership_date | email | location | age")
        for r in rows:
            print(f"{r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]}")
        if cur:
            cur.close()
        if conn:
            conn.close()
    except Exception as e:
        print(f"Sorry, unable to list members", e)
def search_member(keyword):
    sql = """SELECT id, name, membership_date, email, location, age FROM members WHERE name ILIKE %s ORDER BY id;"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(sql, (f"%{keyword}%",))
        rows = cur.fetchall()
        if not rows:
            print(f"Enter a valid keyword")
            return
        for r in rows:
            print(r)
        if cur:
            cur.close()
        if conn:
            conn.close()
    except Exception as e:
        print(f"Oops, no member found with a name like that", e)
def update_member_info(id, name=None, membership_date=None, email=None, location=None, age=None):
    try:
        conn = get_connection()
        cur = conn.cursor()
        updates = []
        value = []
        if name is not None:
            updates.append("name = %s")
            value.append(name)
        if membership_date is not None:
            updates.append("membership_date = %s")
            value.append(membership_date)
        if email is not None:
            updates.append("email = %s")
            value.append(email)
        if location is not None:
            updates.append("location = %s")
            value.append(location)
        if age is not None:
            updates.append("age = %s")
            value.append(age)
        if not updates:
            print(f"No info to update")
            return
        value.append(id)
        sql = "UPDATE members SET name = %s, membership_date = %s, email = %s, location = %s, age = %s WHERE id = %s"
        cur.execute(sql, (name, membership_date, email, location, age, id))
        conn.commit()
        print(f"Member info updated successfully")
        if cur:
            cur.close()
        if conn:
            conn.close()
    except Exception as e:
        print(f"Oops, unable to update member info", e)
        conn.rollback()
def delete_member(id):
    try:
        conn = get_connection()
        cur = conn.cursor()
        sql = """DELETE FROM members WHERE id = %s"""
        cur.execute(sql, (id,))
        if cur.rowcount == 0:
            print(f"Sorry, member with that id")
        else:
            print(f"Member has been deleted from the system")
        conn.commit()
    except Exception as e:
        print(f"Error deleting member from the system", e)
        conn.rollback()
    finally:
        cur.close()
        conn.close()
def borrow_book(book_id, member_id):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT is_available FROM books WHERE id = %s""",
              (book_id,)
        )
        result = cur.fetchone()
        if result is None:
            print(f"Book doesn't esist")
            return
        if result[0] is False:
            print(f"Ooops, book is already borrowed")
            return
        #inserting into borrowing
        cur.execute(
            """INSERT INTO borrowings (book_id, member_id, borrowing_date) VALUES (%s, %s, CURRENT_DATE)""",
            (book_id, member_id)
            )
        cur.execute(
            "UPDATE books SET is_available = FALSE WHERE id = %s",
            (book_id,)
        )
        conn.commit()
        print(f"Book has been borrowed successfully")
        if cur:
            cur.close()
        if conn:
            conn.close()
    except Exception as e:
        print(f"Ooops, error borrowing book", e)
        conn.rollback()
def return_book(book_id, member_id, returning_date):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """SELECT is_available FROM books WHERE id = %s""", (book_id,)
        )
        result = cur.fetchone()
        if result is None:
            print(f"This book doesn't belong to this library")
            return
        if result is True:
            print(f"Book is not currently borrwed")
            return
        cur.execute(
            "UPDATE borrowings SET returning_date = CURRENT_DATE WHERE book_id = %s AND member_id = %s AND returning_date IS NULL",
            (book_id, member_id)
        ) 
        cur.execute(
            "UPDATE books SET is_available = TRUE WHERE id = %s", (book_id,)
        )
        conn.commit()
        print(f"Book returned successfully")
        if cur:
            cur.close()
        if conn:
            conn.close()
    except Exception as e:
        print(f"Error returning book", e)
        conn.rollback()
def listing_borrowed_books():
    conn = get_connection()
    cur = conn.cursor()
    sql = """
            SELECT b.title,
                b.author,
                m.name,
                br.borrowing_date FROM borrowings br
                JOIN books b ON br.book_id = b.id
                JOIN members m ON br.member_id = m.id
                WHERE br.returning_date IS NULL
                ORDER BY br.borrowing_date;"""
    try:
        cur.execute(sql)
        rows = cur.fetchall()
        if not rows:
            print(f"No books are currently borrowed")
            return
        print(f"Title | Author | Borrowed by | Borrowed date")
        for r in rows:
            print(f"{r[0]} | {r[1]} | {r[2]} | {r[3]}")
    except Exception as e:
        print(f"Error listing borrowed books", e)
if __name__ == "__main__":
    listing_borrowed_books()
    
    
    
    
    

        




