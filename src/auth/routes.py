from flask import Response, jsonify, request
from flask_jwt_extended import create_access_token, create_refresh_token
from flask_restx import Namespace, Resource, fields
from sqlalchemy import select

from src import models as md
from src.utils import check_password, session

auth_namespace = Namespace("Auth", description="Authentication operations", path="/")


register_input = auth_namespace.model(
    "RegisterInput",
    {
        "email": fields.String(required=True, description="Email"),
        "first_name": fields.String(required=True, description="First Name"),
        "last_name": fields.String(required=True, description="Last Name"),
        "password": fields.String(required=True, description="Password"),
    },
)

login_input = auth_namespace.model(
    "LoginInput",
    {
        "email": fields.String(required=True, description="Email"),
        "password": fields.String(required=True, description="Password"),
    },
)


@auth_namespace.route("/login", methods=["POST"])
@auth_namespace.expect(login_input)
class Login(Resource):
    def post(self):
        email = request.json.get("email", None)
        password = request.json.get("password", None)

        stmt = select(
            md.UserAccount.id, md.UserAccount.email, md.UserAccount.password, md.UserAccount.role
        ).where(md.UserAccount.email == email)
        user = session.execute(stmt).mappings().first()
        if not user or not check_password(password, user.password):
            return jsonify(message="Wrong username or password", query=str(stmt)), 401

        additional_claims = {"role": user.role}
        access_token = create_access_token(identity=user, additional_claims=additional_claims)
        refresh_token = create_refresh_token(identity=user, additional_claims=additional_claims)
        return jsonify(access_token=access_token, refresh_token=refresh_token)


@auth_namespace.route("/register", methods=["POST"])
@auth_namespace.expect(register_input)
class Register(Resource):
    def post(self):
        data = request.json
        print(data)
        return Response(status=201)
