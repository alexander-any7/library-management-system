from http import HTTPStatus

from flask import jsonify, make_response, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    current_user,
    jwt_required,
)
from flask_restx import Namespace, Resource, fields
from sqlalchemy import and_, insert, or_, select, text, update
from sqlalchemy.orm import joinedload

from src import models as md
from src import p_models as pmd
from src.auth.oauth import admin_required
from src.utils import atomic_transaction, check_password, hash_password, session, sql_compile

auth_namespace = Namespace("Auth", description="Authentication operations", path="/")


register_input = auth_namespace.model(
    "RegisterInput",
    {
        "email": fields.String(required=True, description="Email"),
        "first_name": fields.String(required=True, description="First Name"),
        "last_name": fields.String(required=True, description="Last Name"),
        "password": fields.String(required=True, description="Password"),
        "role": fields.String(
            required=True, description="User Type", enum=["student", "external"]
        ),
    },
)

login_input = auth_namespace.model(
    "LoginInput",
    {
        "email": fields.String(required=True, description="Email"),
        "password": fields.String(required=True, description="Password"),
    },
)

make_admin_input = auth_namespace.model(
    "MakeAdminInput",
    {
        "email": fields.String(required=True, description="Email"),
    },
)
update_user_input = auth_namespace.model(
    "UpdateUserInput",
    {
        "first_name": fields.String(required=True, description="First Name"),
        "last_name": fields.String(required=True, description="Last Name"),
        "role": fields.String(required=True, description="Role", enum=["student", "external"]),
    },
)


@auth_namespace.route("/register", methods=["POST"])
@auth_namespace.expect(register_input)
class Register(Resource):
    @atomic_transaction
    def post(self):
        data = request.json
        email = data.get("email", None)
        first_name = data.get("first_name", None)
        last_name = data.get("last_name", None)
        password = data.get("password", None)
        role = data.get("role", None)

        if not all([email, first_name, last_name, password, role]):
            return make_response(
                jsonify(message="Missing required fields"), HTTPStatus.BAD_REQUEST
            )
        if role not in ("student", "external"):
            return make_response(
                jsonify(message="Invalid role. Must be one of student or external"),
                HTTPStatus.BAD_REQUEST,
            )
        stmt = f"SELECT EXISTS (SELECT 1 FROM user_account WHERE email = '{email}') AS user_exists"
        queries = [stmt]
        user = session.execute(text(stmt)).mappings().first()
        if user["user_exists"]:
            return make_response(
                jsonify(message="User with email already exists", query=sql_compile(stmt)),
                HTTPStatus.BAD_REQUEST,
            )
        password = hash_password(password)
        stmt = f"INSERT INTO user_account (email, first_name, last_name, password, role) VALUES ('{email}', '{first_name}', '{last_name}', '{password}', '{role}')"
        queries.append(stmt)
        session.execute(text(stmt))
        return make_response(
            jsonify(message="User created successfully", queries=[queries]), HTTPStatus.CREATED
        )


@auth_namespace.route("/login", methods=["POST"])
@auth_namespace.expect(login_input)
class Login(Resource):
    def post(self):
        email = request.json.get("email", None)
        password = request.json.get("password", None)
        stmt = f"SELECT id, email, password, role, is_active FROM user_account WHERE email = '{email}'"
        user = session.execute(text(stmt)).mappings().first()
        if not user or not user.is_active or not check_password(password, user.password):
            return make_response(
                jsonify(message="Wrong username or password", queries=[stmt]),
                HTTPStatus.UNAUTHORIZED,
            )

        additional_claims = {"role": user.role}
        access_token = create_access_token(identity=user, additional_claims=additional_claims)
        refresh_token = create_refresh_token(identity=user, additional_claims=additional_claims)
        return jsonify(access_token=access_token, refresh_token=refresh_token, queries=[stmt])


@auth_namespace.route("/refresh")
class Refresh(Resource):
    @jwt_required(refresh=True)
    def post(self):
        """Create a new access token from a refresh token"""
        access_token = create_access_token(
            identity=current_user, additional_claims={"role": current_user.role}
        )
        return make_response(jsonify(access_token=access_token))


@auth_namespace.route("/make-admin")
class MakeAdmin(Resource):
    @auth_namespace.expect(make_admin_input)
    @admin_required
    @atomic_transaction
    def post(self):
        """Make a user an admin"""
        data = request.json
        email = data.get("email", None)
        stmt = (
            f"SELECT id, email, role FROM user_account WHERE email = '{email}' AND role != 'admin'"
        )
        queries = [stmt]
        user = session.execute(text(stmt)).scalars().first()
        if not user:
            return make_response(
                jsonify(message="User not found or already an admin", queries=queries),
                HTTPStatus.NOT_FOUND,
            )
        stmt = f"UPDATE user_account SET role = 'admin' WHERE email = '{email}'"
        queries.append(stmt)
        session.execute(text(stmt))
        return make_response(
            jsonify(message="User is now an admin", queries=queries), HTTPStatus.OK
        )


@auth_namespace.route("/users")
class ListUsers(Resource):
    @admin_required
    def get(self):
        stmt = "SELECT id, email, first_name, last_name, is_active, role FROM user_account \n"
        email = request.args.get("email")
        ors = []
        if email:
            ors.append(f"LOWER(email) LIKE LOWER('%{email}%')")

        name = request.args.get("name")
        if name:
            ors.append(
                f"LOWER(first_name) LIKE LOWER('%{name}%') OR LOWER(last_name) LIKE LOWER('%{name}%')"
            )

        if ors:
            stmt += "\n WHERE " + " OR ".join(ors)

        stmt += "\nORDER BY first_name"
        users = session.execute(text(stmt)).mappings().all()
        users = [pmd.ListUsersSchema.model_validate(user) for user in users]
        return {"users": [user.model_dump() for user in users], "queries": [sql_compile(stmt)]}


@auth_namespace.route("/users/<int:user_id>")
@auth_namespace.doc(params={"user_id": "User ID"})
class GetUser(Resource):
    @admin_required
    def get(self, user_id):
        stmt = select(md.UserAccount).where(md.UserAccount.id == user_id)
        user = session.execute(stmt).scalars().first()
        if not user:
            return make_response(
                jsonify(message="User not found", queries=[sql_compile(stmt)]),
                HTTPStatus.NOT_FOUND,
            )
        schema = pmd.UserDetailSchema
        queries = [sql_compile(stmt)]
        if request.args.get("detail") == "true":
            stmt = (
                stmt.join(md.Borrow, md.Borrow.borrowed_by_id == md.UserAccount.id)
                .join(md.Fine, md.Fine.borrow_id == md.Borrow.id)  # Join Fine with Borrow
                .options(
                    joinedload(md.UserAccount.books_borrowed).joinedload(
                        md.Borrow.fines
                    )  # Eager load Borrow and Fines
                )
            )
            queries.append(sql_compile(stmt))
            user = session.scalars(stmt).first()
            schema = pmd.MoreUserDetailSchema

        user = schema.model_validate(user)
        return make_response(jsonify(user=user.model_dump(), queries=queries))

    @auth_namespace.expect(update_user_input)
    @admin_required
    @atomic_transaction
    def put(self, user_id):
        data = request.json
        valid_roles = ("student", "external")
        role = data.get("role", None)
        if role and role not in valid_roles:
            return make_response(
                jsonify(message=f"Invalid role. Must be one of {valid_roles}", queries=[]),
                HTTPStatus.BAD_REQUEST,
            )
        update_data = {}
        for name in tuple(update_user_input.keys()):
            if name in data:
                update_data[name] = data[name]

        update_stmt = (
            update(md.UserAccount).where(md.UserAccount.id == user_id).values(update_data)
        )
        queries = [sql_compile(update_stmt)]
        result = session.execute(update_stmt)
        if result.rowcount == 0:
            return make_response(
                jsonify(message="User not found", queries=queries), HTTPStatus.NOT_FOUND
            )
        return make_response(
            jsonify(message="User updated successfully", queries=queries), HTTPStatus.OK
        )


@auth_namespace.route("/deactivate-user")
class DeactivateUser(Resource):
    @admin_required
    @atomic_transaction
    def post(self):
        data = request.json
        email = data.get("email", None)
        stmt = (
            update(md.UserAccount)
            .where(and_(md.UserAccount.email == email, md.UserAccount.is_active.is_(True)))
            .values(is_active=False)
        )
        queries = [sql_compile(stmt)]
        result = session.execute(stmt)
        if result.rowcount == 0:
            return make_response(
                jsonify(message="User not found or already deactivated", queries=queries),
                HTTPStatus.NOT_FOUND,
            )
        return make_response(
            jsonify(message="User deactivated successfully", queries=queries), HTTPStatus.OK
        )


@auth_namespace.route("/activate-user")
class ActivateUser(Resource):
    @admin_required
    @atomic_transaction
    def post(self):
        data = request.json
        email = data.get("email", None)
        stmt = (
            update(md.UserAccount)
            .where(and_(md.UserAccount.email == email, md.UserAccount.is_active.is_(False)))
            .values(is_active=True)
        )
        queries = [sql_compile(stmt)]
        result = session.execute(stmt)
        if result.rowcount == 0:
            return make_response(
                jsonify(message="User not found or already deactivated", queries=queries),
                HTTPStatus.NOT_FOUND,
            )
        return make_response(
            jsonify(message="User deactivated successfully", queries=queries), HTTPStatus.OK
        )
