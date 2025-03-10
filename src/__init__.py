from flask import Flask
from flask_jwt_extended import JWTManager
from flask_restx import Api
from sqlalchemy import select, text  # noqa

from config import config_dict, DevConfig
from sql import CREATE_POSTGRES, CREATE_SQLITE
from src import models as md
from src.auth.routes import auth_namespace
from src.books import book_namespace
from src.borrows import borrow_namespace
from src.reports import reports_namespace
from src.utils import session
from flask_cors import CORS


def create_app(db="sqlite", config=config_dict['dev']):
    app = Flask(__name__)
    CORS(app, origins="*")
    app.config.from_object(config)
    authorizations = {
        "Bearer Auth": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "add a JWT with ** Bearer &lt;JWT&gt; to authorize",
        }
    }

    api = Api(app, authorizations=authorizations, security="Bearer Auth")
    jwt = JWTManager(app)

    if config.DB == "sqlite":
        statements = CREATE_SQLITE.split(";")
    elif config.DB == "postgres":
        statements = CREATE_POSTGRES.split(";")  # noqa

    if isinstance(config, DevConfig):
        print("Creating tables")
        # for stmt in statements:
        #     session.execute(text(stmt))
        # session.commit()

    @jwt.user_identity_loader
    def user_identity_lookup(user):
        return user.id

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        stmt = select(md.UserAccount.id, md.UserAccount.first_name, md.UserAccount.role).where(
            md.UserAccount.id == identity
        )
        res = session.execute(stmt).mappings().first()
        return res

    api.add_namespace(book_namespace, path="")
    api.add_namespace(auth_namespace, path="")
    api.add_namespace(borrow_namespace, path="")
    api.add_namespace(reports_namespace, path="")

    return app
