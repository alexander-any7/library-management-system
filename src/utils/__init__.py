import os
from datetime import datetime, timedelta
from functools import wraps

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.sql.elements import DQLDMLClauseElement
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config, config_dict
from src.models import Borrow

PAYMENT_METHODS = ("cash", "debit", "credit", "paypal", "stripe")
VALID_USER_TYPES = ("student", "external", "admin")


def hash_password(password):
    return generate_password_hash(password)


def check_password(password, password_hash):
    return check_password_hash(password_hash, password)


config: Config = config_dict[os.getenv("FLASK_ENV", "testing")]

engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=config.SQLALCHEMY_ECHO)
dialect = config.DIALECT

session = scoped_session(sessionmaker(bind=engine))


def sql_compile(clause: DQLDMLClauseElement, dialect=dialect) -> str:
    if isinstance(clause, str):
        clauses = clause.split("\n")
        return "\n".join([line.strip() for line in clauses if line.strip()])
    return str(clause.compile(dialect=dialect(), compile_kwargs={"literal_binds": True}))


def calculate_due_date(**kwargs):
    return kwargs.get("date", datetime.now()) + timedelta(days=14)


def calculate_fine(**kwargs):
    """
    Calculate the fine based on the number of days past the given date.

    Keyword Arguments:
    date (datetime): The date to calculate the fine from.

    Returns:
    int: The calculated fine. Returns 0 if the date is not provided or if the date is in the future.
    """
    date: datetime = kwargs.get("date")
    if date is None:
        return 0
    if not isinstance(date, datetime):
        date = datetime.fromisoformat(date)
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


def check_overdue_and_create_fine(borrow: Borrow, now: datetime = None, commit=True):
    """
    Checks if a borrowed item is overdue and creates a fine if it is.
    Args:
        borrow (Borrow): The borrow instance containing borrowing details.
        now (datetime, optional): The current date and time. Defaults to None, in which case the current date and time will be used.
        commit (bool, optional): Whether to commit the transaction to the database. Defaults to True.
    Returns:
        str: The SQL query string that was executed.
    """
    if now is None:
        now = datetime.now()
    due_date = borrow.due_date
    if not isinstance(due_date, datetime):
        due_date = datetime.fromisoformat(due_date)

    if due_date.date() < now.date():
        fine = calculate_fine(date=borrow.due_date)
        fine_stmt = f"INSERT INTO fine (borrow_id, amount, date_created) VALUES ({borrow.id}, {fine}, '{now}')"
        session.execute(text(fine_stmt))

        overdue_stmt = f"INSERT INTO notification (user_id, message, sent_date, is_read) VALUES ({borrow.borrowed_by_id}, 'You have overdue fines', '{datetime.now()}', 0)"
        session.execute(text(overdue_stmt))
        session.commit()

        if commit:
            session.commit()

        return (fine_stmt, overdue_stmt)
