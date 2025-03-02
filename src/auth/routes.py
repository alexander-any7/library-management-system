from flask import Response, jsonify, make_response, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    current_user,
    jwt_required,
)
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

refresh_input = auth_namespace.model(
    "RefreshInput",
    {
        "refresh_token": fields.String(required=True, description="Refresh Token"),
    },
)


@auth_namespace.route("/register", methods=["POST"])
@auth_namespace.expect(register_input)
class Register(Resource):
    def post(self):
        data = request.json
        print(data)
        return Response(status=201)


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
            return make_response(
                jsonify(message="Wrong username or password", query=str(stmt)), 401
            )

        additional_claims = {"role": user.role}
        access_token = create_access_token(identity=user, additional_claims=additional_claims)
        refresh_token = create_refresh_token(identity=user, additional_claims=additional_claims)
        return jsonify(access_token=access_token, refresh_token=refresh_token, query=str(stmt))


@auth_namespace.route("/refresh")
class Refresh(Resource):
    @jwt_required(refresh=True)
    def post(self):
        """Create a new access token from a refresh token"""
        access_token = create_access_token(
            identity=current_user, additional_claims={"role": current_user.role}
        )
        return make_response(jsonify(access_token=access_token), 200)
