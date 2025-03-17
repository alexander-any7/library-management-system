from datetime import datetime
from http import HTTPStatus

from flask import jsonify, make_response, request
from flask_jwt_extended import current_user, jwt_required
from flask_restx import Namespace, Resource, fields
from sqlalchemy import text

import src.p_models as pmd
from src.auth.oauth import admin_required
from src.utils import atomic_transaction, session, sql_compile

book_namespace = Namespace("Books", description="Book operations", path="/")

new_book_input = book_namespace.model(
    "NewBookInput",
    {
        "title": fields.String(required=True, description="Title"),
        "author": fields.String(required=True, description="Author"),
        "category_id": fields.Integer(required=True, description="Category ID"),
        "isbn": fields.String(required=True, description="ISBN"),
        "quantity": fields.Integer(required=True, description="Quantity"),
        "location": fields.String(required=True, description="Location"),
    },
)

update_book_input = book_namespace.model(
    "UpdateBookInput",
    {
        "title": fields.String(description="Title"),
        "author": fields.String(description="Author"),
        "category_id": fields.Integer(description="Category ID"),
        "isbn": fields.String(description="ISBN"),
        "quantity": fields.Integer(description="Quantity"),
        "location": fields.String(description="Location"),
    },
)


@book_namespace.route("/categories")
class Categories(Resource):
    def get(self):
        stmt = "SELECT category.id, category.name \nFROM category"
        categories = session.execute(text(stmt)).mappings().all()
        categories = [pmd.ListCategorySchema.model_validate(category) for category in categories]
        return jsonify(
            {
                "categories": [category.model_dump() for category in categories],
                "queries": [sql_compile(stmt)],
            }
        )


@book_namespace.route("/categories/<int:category_id>")
@book_namespace.doc(params={"category_id": "Category ID"})
class Category(Resource):
    @jwt_required(optional=True)
    def get(self, category_id):
        detail = False
        stmt = "SELECT category.id, category.name, category.added_by_id, book.id AS book_id, book.author, book.is_available, book.location, book.title"
        if request.args.get("detail") == "true" and current_user and current_user.role == "admin":
            detail = True
            stmt += """,user_account.id AS added_by_user_id, user_account.first_name || ' ' || user_account.last_name AS category_added_by
                FROM category
                LEFT OUTER JOIN user_account ON user_account.id = category.added_by_id
                LEFT OUTER JOIN book ON category.id = book.category_id"""
        else:
            stmt += "\nFROM category \n LEFT OUTER JOIN book ON category.id = book.category_id"
        stmt += f" \nWHERE category.id = {category_id}"
        category = session.execute(text(stmt)).mappings().all()
        organized_data = {
            "id": None,
            "name": None,
            "added_by_id": None,
            "books": [],
        }
        if detail:
            organized_data["category_added_by"] = None

        for row in category:
            if organized_data["id"] is None:
                organized_data["id"] = row.id
                organized_data["name"] = row.name
                organized_data["added_by_id"] = row.added_by_id
                if detail:
                    organized_data["category_added_by"] = row.category_added_by

            if row.book_id is not None:
                organized_data["books"].append(
                    {
                        "id": row.book_id,
                        "author": row.author,
                        "is_available": row.is_available,
                        "location": row.location,
                        "title": row.title,
                    }
                )

        return jsonify({"category": organized_data, "queries": [sql_compile(stmt)]})


@book_namespace.route("/books")
class Books(Resource):
    def get(self):
        stmt = """SELECT book.id, book.title, book.author, book.isbn, book.category_id, book.original_quantity, book.current_quantity, book.date_added, book.added_by_id, book.is_available, book.location, category.name as book_category
        FROM book JOIN category ON category.id = book.category_id
        """
        title = request.args.get("title")
        or_list = []
        if title:
            # or_list.append(md.Book.title.ilike(f"%{title}%"))
            or_list.append(f"lower(book.title) LIKE lower('%{title}%')")

        author = request.args.get("author")
        if author:
            # or_list.append(md.Book.author.ilike(f"%{author}%"))
            or_list.append(f"lower(book.author) LIKE lower('%{author}%')")

        isbn = request.args.get("isbn")
        if isbn:
            # or_list.append(md.Book.isbn.ilike(f"%{isbn}%"))
            or_list.append(f"lower(book.isbn) LIKE ('%{isbn}%')")

        category = request.args.get("category")
        if category:
            # or_list.append(md.Category.name == category)
            or_list.append(f"category.name = '{category}'")

        if or_list:
            stmt = stmt + " WHERE " + " OR ".join(or_list)

        stmt += " ORDER BY book.title ASC"

        books = session.execute(text(stmt)).mappings().all()
        books = [pmd.ListBookSchema.model_validate(book) for book in books]
        return make_response(
            jsonify(
                {"books": [book.model_dump() for book in books], "queries": [sql_compile(stmt)]}
            )
        )

    @admin_required
    @atomic_transaction
    @book_namespace.expect(new_book_input)
    def post(self):
        data = request.json
        stmt = f"""INSERT INTO book (title, author, isbn, category_id, original_quantity, current_quantity, date_added, added_by_id, is_available, location)
            VALUES ('{data["title"]}', '{data["author"]}', '{data["isbn"]}', {data["category_id"]}, {data["quantity"]}, '{data["quantity"]}', '{datetime.now()}', {current_user.id}, 1, '{data["location"]}')
        """
        queries = [stmt]
        session.execute(text(stmt))
        stmt = "SELECT id FROM book ORDER BY id DESC LIMIT 1"
        queries.append(stmt)
        book = session.execute(text(stmt)).mappings().first()
        return make_response(jsonify(book_id=book.id, queries=queries), HTTPStatus.CREATED)


@book_namespace.route("/books/<int:book_id>")
@book_namespace.doc(params={"book_id": "Book ID"})
class Book(Resource):
    @jwt_required(optional=True)
    def get(self, book_id):
        detail = False
        stmt = "SELECT book.id, book.title, book.author, book.isbn, book.category_id, book.current_quantity, book.is_available, book.location, book.date_added, category.name AS category_name"
        if request.args.get("detail") == "true" and current_user and current_user.role == "admin":
            detail = True
            stmt += ",     book.original_quantity, book.added_by_id, added_by.first_name AS added_by_first_name, added_by.last_name AS added_by_last_name, borrow.borrow_date, borrow.due_date, borrow.is_returned, borrowed_by.first_name AS borrowed_by_first_name, borrowed_by.last_name AS borrowed_by_last_name"
            stmt += "\nFROM book \n JOIN category ON category.id = book.category_id \n JOIN user_account AS added_by ON added_by.id = book.added_by_id \n LEFT OUTER JOIN borrow ON book.id = borrow.book_id \n LEFT OUTER JOIN user_account AS borrowed_by ON borrowed_by.id = borrow.borrowed_by_id"
        else:
            stmt += "\nFROM book \n JOIN category ON category.id = book.category_id"
        stmt += f"\nWHERE book.id = {book_id}"

        book = session.execute(text(stmt)).mappings().all()
        data = {
            "id": None,
            "author": None,
            "title": None,
            "book_category": None,
            "current_quantity": None,
            "is_available": None,
            "isbn": None,
            "location": None,
        }
        if detail:
            data["borrows"] = []

        for row in book:
            if data["id"] is None:
                data["id"] = row.id
                data["author"] = row.author
                data["title"] = row.title
                data["book_category"] = row.category_name
                data["current_quantity"] = row.current_quantity
                data["is_available"] = row.is_available == 1
                data["isbn"] = row.isbn
                data["location"] = row.location
                if detail:
                    data["book_added_by"] = row.added_by_first_name + " " + row.added_by_last_name
                    data["date_added"] = datetime.fromisoformat(row.date_added)
                    data["original_quantity"] = row.original_quantity
                    # data["category_id"] = row.category_id
                else:
                    break

            data["borrows"].append(
                {
                    "id": row.id,
                    "borrowed_by": row.borrowed_by_first_name + " " + row.borrowed_by_last_name,
                    "borrowed_book": row.title,
                    "borrow_date": datetime.fromisoformat(row.borrow_date),
                    "due_date": datetime.fromisoformat(row.due_date),
                    "is_returned": row.is_returned == 1,
                }
            )

        return jsonify({"book": data, "queries": [sql_compile(stmt)]})

    @book_namespace.expect(update_book_input)
    @admin_required
    @atomic_transaction
    def put(self, book_id):
        # Get the fields to update from the request
        update_data = []
        field_names = list(update_book_input.keys())
        for name in field_names:
            if name in request.json:
                if name == "quantity":
                    update_data.append(f"current_quantity={request.json[name]}")
                else:
                    update_data.append(f"{name}='{request.json[name]}'")

        # If no fields to update, return an error
        if not update_data:
            return make_response(
                jsonify(error="No fields to update", queries=[]), HTTPStatus.NOT_MODIFIED
            )

        # Build the update statement dynamically
        update_stmt = f"UPDATE book SET {', '.join(update_data)} WHERE id={book_id}"
        queries = [sql_compile(update_stmt)]
        result = session.execute(text(update_stmt))
        if result.rowcount == 0:
            return make_response(jsonify(error="Book not found"), 404)
        return make_response(
            jsonify(message="Book updated successfully", queries=queries), HTTPStatus.OK
        )

    @admin_required
    @atomic_transaction
    def delete(self, book_id):
        stmt = f"SELECT id FROM book WHERE id = {book_id}"
        queries = [stmt]
        book_exists = session.execute(text(stmt)).mappings().first()
        if not book_exists:
            return make_response(
                jsonify(error="Book not found", queries=queries), HTTPStatus.NOT_FOUND
            )

        stmt = f"SELECT EXISTS (SELECT 1 FROM borrow WHERE borrow.book_id = {book_id}) AS borrow_exists"
        queries.append(sql_compile(stmt))
        borrow_exists = book_exists = session.execute(text(stmt)).mappings().first()
        if borrow_exists["borrow_exists"]:
            return make_response(
                jsonify(
                    error="Book has an existing borrow record, and cannot be deleted",
                    queries=queries,
                ),
                HTTPStatus.BAD_REQUEST,
            )

        stmt = f"DELETE FROM book WHERE book.id = {book_id}"
        queries.append(stmt)
        session.execute(text(stmt))
        return make_response(
            jsonify(message="Book deleted successfully", queries=queries), HTTPStatus.OK
        )
