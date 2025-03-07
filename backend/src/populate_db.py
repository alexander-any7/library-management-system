from datetime import datetime, timedelta
from random import choice, choices, randint

from faker import Faker
from sqlalchemy import select
from werkzeug.security import generate_password_hash

from src.models import Book, Borrow, Category, Fine, UserAccount
from src.utils import session

fake = Faker()

students = []
externals = []
admins = []
categories = []
books = []

for i in range(10):
    students.append(
        UserAccount(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            role="student",
            password=generate_password_hash("password"),
            email=fake.email(),
            is_active=True,
        )
    )

    if i % 2 == 0:
        externals.append(
            UserAccount(
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                role="external",
                password=generate_password_hash("password"),
                email=fake.email(),
                is_active=True,
            )
        )

    if i % 4 == 0:
        admins.append(
            UserAccount(
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                role="admin",
                password=generate_password_hash("password"),
                email=fake.email(),
                is_active=True,
            )
        )

session.add_all(students)
session.add_all(externals)
session.add_all(admins)
session.commit()

students = session.scalars(select(UserAccount).where(UserAccount.role == "student")).all()
admins = session.scalars(select(UserAccount).where(UserAccount.role == "admin")).all()
externals = session.scalars(select(UserAccount).where(UserAccount.role == "external")).all()

for i in range(5):
    categories.append(Category(name=fake.word(), added_by_id=choice(admins).id))


session.add_all(categories)
session.commit()
categories = session.scalars(select(Category)).all()

cat_dict = {}
num = 50
for cat in categories:
    cat_dict[cat.id] = str(num)
    num += 50

letters = ("A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N")

for i in range(20):
    category = choice(categories).id
    l_name = fake.last_name()
    location = f"{choice(letters)}-{cat_dict[category]}-{l_name[:3].upper()}"
    f_name = fake.first_name()
    books.append(
        Book(
            title=fake.sentence(randint(2, 6)),
            author=f"{f_name} {l_name}",
            isbn=fake.isbn13(),
            category_id=category,
            date_added=datetime.now(),
            added_by_id=choice(admins).id,
            location=location,
        )
    )

session.add_all(books)
session.commit()

books = session.scalars(select(Book)).all()

b_choices = choices(books, k=10)
borrows = []
for i in b_choices:
    borrow_date = datetime.now() - timedelta(days=randint(1, 60))
    due_date = borrow_date + timedelta(days=randint(3, 30))
    borrows.append(
        Borrow(
            book_id=i.id,
            borrowed_by_id=choice(students).id,
            given_by_id=choice(admins).id,
            received_by_id=choice(admins).id if choice((True, False)) else None,
            borrow_date=borrow_date,
            due_date=due_date,
            comments=fake.sentence(10),
        )
    )

session.add_all(borrows)
session.commit()

borrows = session.scalars(select(Borrow)).all()
fines = []
for i in borrows:
    if i.due_date < datetime.now():
        days = datetime.now() - i.due_date
        amount = days.days * 5
        paid = choice((True, False))
        method = choice(("cash", "card", "mpesa"))
        fines.append(
            Fine(
                borrow_id=i.id,
                amount=amount,
                paid=paid,
                payment_method=method if paid else None,
                collected_by_id=choice(admins).id if paid and method == "cash" else None,
                date_created=datetime.now(),
                date_paid=datetime.now() if paid else None,
                transaction_id=fake.uuid4() if paid and method != "cash" else None,
            )
        )

session.add_all(fines)
session.commit()
