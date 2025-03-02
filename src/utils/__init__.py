from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(self, password):
    return generate_password_hash(password)


def check_password(password, password_hash):
    return check_password_hash(password_hash, password)


db = "sqlite"
if db == "sqlite":
    engine = create_engine("sqlite:///db.sqlite")
elif db == "postgres":
    engine = engine = create_engine("sqlite:///db.sqlite")
else:
    raise ValueError("Invalid database")


session = Session(engine)
