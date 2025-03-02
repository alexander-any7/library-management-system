from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import dialect as PostgresDialect
from sqlalchemy.dialects.sqlite import dialect as SqliteDialect
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import DQLDMLClauseElement
from werkzeug.security import check_password_hash, generate_password_hash


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
