from datetime import datetime
from http import HTTPStatus

from flask import jsonify, make_response, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    current_user,
    jwt_required,
)
from flask_restx import Namespace, Resource, fields
from sqlalchemy import text

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
        books_received = tuple()
        books_given = tuple()
        fines_collected = tuple()
        borrows = tuple()
        stmt = f"SELECT id, email, first_name, last_name, is_active, role FROM user_account WHERE id = {user_id}"
        user = session.execute(text(stmt)).mappings().first()
        if not user:
            return make_response(
                jsonify(message="User not found", queries=[sql_compile(stmt)]),
                HTTPStatus.NOT_FOUND,
            )
        queries = [stmt]
        if request.args.get("detail") == "true":
            stmt = f"""SELECT borrow.id AS borrow_id, borrow.borrow_date, borrow.received_by_id, borrow.is_returned, borrow.book_id, book.title AS borrowed_book, fine.id AS fine_id, fine.amount AS fine_amount, fine.paid AS fine_paid, fine.date_created AS fine_date_created, fine.collected_by_id AS fine_collected_by_id, fine.date_paid AS fine_date_paid
                      FROM borrow
                      JOIN book ON book.id = borrow.book_id
                      LEFT JOIN fine ON fine.borrow_id = borrow.id
                      WHERE borrow.borrowed_by_id = {user_id};
            """
            queries.append(sql_compile(stmt))
            borrows = session.execute(text(stmt)).mappings().all()
            if user.role == "admin":
                stmt = f"""SELECT borrow.id AS borrow_id, borrow.borrow_date, borrow.borrowed_by_id, borrow.is_returned, borrow.book_id, borrow.return_date, book.title AS borrowed_book
                          FROM borrow
                          JOIN book ON book.id = borrow.book_id
                          WHERE borrow.received_by_id = {user_id};
                    """
                queries.append(sql_compile(stmt))
                books_received = session.execute(text(stmt)).mappings().all()

                stmt = f"""
                        SELECT fine.id AS fine_id, fine.borrow_id, fine.amount AS fine_amount, fine.paid AS fine_paid, fine.date_created AS fine_date_created, fine.collected_by_id, fine.date_paid AS fine_date_paid, borrow.borrow_date, borrow.borrowed_by_id, borrow.received_by_id, borrow.is_returned, borrow.book_id, book.title AS borrowed_book
                        FROM fine
                        JOIN borrow ON borrow.id = fine.borrow_id
                        JOIN book ON book.id = borrow.book_id
                        WHERE fine.collected_by_id = {user_id};
                    """
                fines_collected = session.execute(text(stmt)).mappings().all()

                stmt = f"""SELECT borrow.id AS borrow_id, borrow.borrow_date, borrow.borrowed_by_id, borrow.is_returned, borrow.book_id, book.title AS borrowed_book
                          FROM borrow
                          JOIN book ON book.id = borrow.book_id
                          WHERE borrow.given_by_id = {user_id};"""
                queries.append(sql_compile(stmt))
                books_given = session.execute(text(stmt)).mappings().all()

        user = {
            "email": user.email,
            "first_name": user.first_name,
            "id": user.id,
            "is_active": user.is_active == 1,
            "last_name": user.last_name,
            "role": user.role,
            "books_borrowed": [
                {
                    "borrow_date": datetime.fromisoformat(borrow.borrow_date),
                    "borrowed_book": borrow.borrowed_book,
                    "id": borrow.borrow_id,
                    "is_returned": borrow.is_returned == 1,
                    "fines": [
                        {
                            "id": borrow.fine_id,
                            "amount": borrow.fine_amount,
                            "borrow": borrow.borrowed_book,
                            "date_created": datetime.fromisoformat(borrow.fine_date_created),
                            "date_paid": datetime.fromisoformat(borrow.fine_date_paid),
                            "paid": borrow.fine_paid == 1,
                        }
                    ],
                }
                for borrow in borrows
            ],
            "books_given": (
                [
                    {
                        "id": borrow.borrow_id,
                        "borrow_date": datetime.fromisoformat(borrow.borrow_date),
                        "borrowed_book": borrow.borrowed_book,
                        "is_returned": borrow.is_returned == 1,
                    }
                    for borrow in books_given
                ]
            ),
            "fines_collected": (
                [
                    {
                        "id": fine.fine_id,
                        "amount": fine.fine_amount,
                        "date_created": datetime.fromisoformat(fine.fine_date_created),
                        "date_paid": datetime.fromisoformat(fine.fine_date_paid),
                        "borrow_id": fine.borrow_id,
                        "paid": fine.fine_paid == 1,
                        "borrowed_book": fine.borrowed_book,
                    }
                    for fine in fines_collected
                ]
            ),
            "books_received": (
                [
                    {
                        "id": borrow.borrow_id,
                        "borrow_date": datetime.fromisoformat(borrow.borrow_date),
                        "borrowed_book": borrow.borrowed_book,
                        "is_returned": borrow.is_returned == 1,
                        "return_date": datetime.fromisoformat(borrow.return_date),
                    }
                    for borrow in books_received
                ]
            ),
        }
        return make_response(jsonify(user=user, queries=queries))

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
        update_data = []
        for name in tuple(update_user_input.keys()):
            if name in data:
                update_data.append(f"{name}='{request.json[name]}'")

        update_stmt = f"UPDATE user_account SET {', '.join(update_data)} WHERE id={user_id}"
        queries = [update_stmt]
        result = session.execute(text(update_stmt))
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
        stmt = f"UPDATE user_account SET is_active = FALSE WHERE email = '{email}' AND is_active = TRUE"
        queries = [stmt]
        result = session.execute(text(stmt))
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
        stmt = f"UPDATE user_account SET is_active = TRUE WHERE email = '{email}' AND is_active = FALSE"
        queries = [stmt]
        result = session.execute(text(stmt))
        if result.rowcount == 0:
            return make_response(
                jsonify(message="User not found or already active", queries=queries),
                HTTPStatus.NOT_FOUND,
            )
        return make_response(
            jsonify(message="User activated successfully", queries=queries), HTTPStatus.OK
        )
