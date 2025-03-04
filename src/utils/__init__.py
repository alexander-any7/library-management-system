from datetime import datetime, timedelta
from functools import wraps

from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import dialect as PostgresDialect
from sqlalchemy.dialects.sqlite import dialect as SqliteDialect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import DQLDMLClauseElement
from werkzeug.security import check_password_hash, generate_password_hash

PAYMENT_METHODS = ("cash", "debit", "credit", "paypal", "stripe")
VALID_USER_TYPES = ("student", "external", "admin")


def hash_password(self, password):
    return generate_password_hash(password)


def check_password(password, password_hash):
    return check_password_hash(password_hash, password)


db = "sqlite"
if db == "sqlite":
    engine = create_engine("sqlite:///db.sqlite", echo=True)
    dialect = SqliteDialect
elif db == "postgres":
    engine = engine = create_engine("postgresql://postgres:12345@localhost/library", echo=True)
    dialect = PostgresDialect
else:
    raise ValueError("Invalid database")


session = Session(engine)


def sql_compile(clause: DQLDMLClauseElement):
    return str(clause.compile(dialect=dialect(), compile_kwargs={"literal_binds": True}))


def calculate_due_date(**kwargs):
    return kwargs.get("date", datetime.now()) + timedelta(days=14)


def calculate_fine(**kwargs):
    date: datetime = kwargs.get("date")
    if date is None:
        return 0
    days = (datetime.now() - date).days
    return days * 100 if days > 0 else 0


def atomic_transaction(func):
    """
    Decorator to wrap a function in an atomic transaction.
    Uses the global `session` object.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)  # Execute the function
            session.commit()  # Commit the transaction if no errors
            return result
        except SQLAlchemyError as e:
            session.rollback()  # Rollback on SQLAlchemy errors
            raise e
        except Exception as e:
            session.rollback()  # Rollback on any other errors
            raise e

    return wrapper
