from datetime import timedelta

from sqlalchemy.dialects.postgresql import dialect as PostgresDialect  # noqa
from sqlalchemy.dialects.sqlite import dialect as SqliteDialect


class Config:
    SECRET_KEY = "super-secret"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=60)
    JWT_SECRET_KEY = "super-secret-jwt"
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRES_MINUTES = 30
    DB = "sqlite"
    DIALECT = SqliteDialect
    SQLALCHEMY_DATABASE_URI = "sqlite:///db.sqlite"
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    SQLALCHEMY_ECHO = True
    DEBUG = True
    JWT_VERIFY_SUB = False


class DevConfig(Config):
    pass


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False


config_dict: dict[str, Config] = {
    "dev": DevConfig,
    "testing": TestConfig,
}
