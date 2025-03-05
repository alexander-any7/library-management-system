import unittest
from datetime import datetime, timedelta
from http import HTTPStatus
from random import choice, choices, randint

from faker import Faker
from flask_jwt_extended import create_access_token
from sqlalchemy import and_
from werkzeug.security import generate_password_hash

import src.models as md
from src import create_app
from src.models import Base
from src.utils import VALID_USER_TYPES, engine, session

fake = Faker()


def populate_test_db():
    users = [
        md.UserAccount(
            email=fake.email(),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            password=generate_password_hash("password"),
            role=i,
        )
        for i in VALID_USER_TYPES
    ]
    session.add_all(users)
    session.commit()

    categories = [md.Category(name=fake.word(), added_by_id=users[2].id) for _ in range(2)]
    session.add_all(categories)
    session.commit()

    books = [
        md.Book(
            title=fake.sentence(3),
            author=fake.name(),
            category_id=choice(categories).id,
            isbn=fake.isbn13(),
            original_quantity=10,
            current_quantity=10,
            location=fake.word(),
            date_added=fake.date_this_decade(),
            added_by_id=users[2].id,
        )
        for _ in range(10)
    ]
    session.add_all(books)
    session.commit()

    return users


class AllTestCase(unittest.TestCase):
    def setUp(self):
        # Create the application instance
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()

        # Create the test client
        self.client = self.app.test_client()

        # Use create all to make sure the model matches the sql create statement
        Base.metadata.create_all(engine)

        # Populate the test database
        self.users = populate_test_db()
        self.student = self.users[0]
        self.external = self.users[1]
        self.admin = self.users[2]

        self.student_token = create_access_token(
            identity=self.student, additional_claims={"role": self.student.role}
        )
        self.external_token = create_access_token(
            identity=self.external, additional_claims={"role": self.external.role}
        )
        self.admin_token = create_access_token(
            identity=self.admin, additional_claims={"role": self.admin.role}
        )

    def tearDown(self):
        # Drop all tables
        Base.metadata.drop_all(engine)

        # Remove the session
        session.close()

        # Pop the application context
        self.app_context.pop()

    def test_open_routes(self):
        # Example test case
        response = self.client.get("/books")
        self.assertTrue(response.json["books"])
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/categories")
        self.assertTrue(response.json["categories"])
        self.assertEqual(response.status_code, 200)

    def test_insert_book(self):
        books_count = session.query(md.Book).count()
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        data = {
            "title": fake.sentence(3),
            "author": fake.name(),
            "category_id": randint(1, 2),
            "isbn": fake.isbn13(),
            "quantity": 1,
            "location": fake.word(),
        }
        response = self.client.post("/books", json=data, headers=headers)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        book = session.query(md.Book).where(md.Book.id == response.json["book_id"]).first()
        self.assertEqual(session.query(md.Book).count(), books_count + 1)
        self.assertTrue(book)
        self.assertTrue(book.added_by_id == self.admin.id)

    def test_update_book(self):
        book = session.query(md.Book).first()
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        data = {
            "quantity": 2,
            "location": fake.word(),
        }
        response = self.client.put(f"/books/{book.id}", json=data, headers=headers)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        book = session.query(md.Book).where(md.Book.id == book.id).first()
        self.assertTrue(book)
        self.assertTrue(book.current_quantity == 2)
        self.assertTrue(book.location == data["location"])

    def test_search_books(self):
        book = session.query(md.Book.author, md.Book.title, md.Category.name).first()
        response = self.client.get(f"/books?author={book.author[:4]}")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(response.json["books"])
        self.assertTrue(response.json["books"][0]["author"] == book.author)

        response = self.client.get(f"/books?title={book.title[:4]}")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(response.json["books"])
        self.assertTrue(response.json["books"][0]["title"] == book.title)

        response = self.client.get(f"/books?category={book.name}")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(response.json["books"])
        self.assertTrue(response.json["books"][0]["book_category"] == book.name)

    def test_borrow_a_book(self):
        book = session.query(md.Book).first()
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        data = {
            "book_id": book.id,
            "borrower_id": self.student.id,
        }
        response = self.client.post("/borrow-book", json=data, headers=headers)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        borrowed = (
            session.query(md.Borrow)
            .where(and_(md.Borrow.book_id == book.id, md.Borrow.borrowed_by_id == self.student.id))
            .first()
        )
        self.assertTrue(borrowed)
        self.assertFalse(borrowed.is_returned)
        self.assertTrue(borrowed.given_by_id == self.admin.id)

    def test_calculate_overdue_fines(self):
        student_2 = md.UserAccount(
            email=fake.email(),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            password=generate_password_hash("password"),
            role="student",
        )
        session.add(student_2)
        session.flush()
        books = choices(session.query(md.Book).all(), k=6)
        for book in books[:2]:
            borrow_date = datetime.now() - timedelta(days=randint(1, 60))
            due_date = borrow_date + timedelta(days=randint(3, 30))
            session.add(
                md.Borrow(
                    book_id=book.id,
                    borrowed_by_id=self.student.id,
                    given_by_id=self.admin.id,
                    received_by_id=self.admin.id,
                    is_returned=False,
                    borrow_date=borrow_date,
                    due_date=due_date,
                )
            )
        for book in books[3:]:
            borrow_date = datetime.now() - timedelta(days=randint(1, 60))
            due_date = borrow_date + timedelta(days=randint(3, 30))
            session.add(
                md.Borrow(
                    book_id=book.id,
                    borrowed_by_id=student_2.id,
                    given_by_id=self.admin.id,
                    received_by_id=self.admin.id,
                    is_returned=False,
                    borrow_date=borrow_date,
                    due_date=due_date,
                )
            )
        session.commit()
