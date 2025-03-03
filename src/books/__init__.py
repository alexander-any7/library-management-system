from datetime import datetime
from http import HTTPStatus

from flask import jsonify, make_response, request
from flask_jwt_extended import current_user
from flask_restx import Namespace, Resource, fields
from sqlalchemy import delete, insert, select, update

import src.models as md
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
        "location": fields.String(description="Location"),
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


@book_namespace.route("/books")
class Books(Resource):
    def get(self):
        stmt = select(md.Book, md.Category.name).join(md.Category)
        title = request.args.get("title")
        if title:
            stmt = stmt.where(md.Book.title.ilike(f"%{title}%"))

        author = request.args.get("author")
        if author:
            stmt = stmt.where(md.Book.author.ilike(f"%{author}%"))

        isbn = request.args.get("isbn")
        if isbn:
            stmt = stmt.where(md.Book.isbn.ilike(f"%{isbn}%"))

        category = request.args.get("category")
        if category:
            stmt = stmt.where(md.Category.name == category)

        res = session.scalars(stmt)
        books = res.all()
        books = [pmd.ListBookSchema.model_validate(book) for book in books]
        return jsonify(
            {"books": [book.model_dump() for book in books], "queries": [sql_compile(stmt)]}
        )

    @admin_required
    @atomic_transaction
    @book_namespace.expect(new_book_input)
    def post(self):
        data = request.json
        book = md.Book(
            title=data["title"],
            author=data["author"],
            category_id=data["category_id"],
            isbn=data["isbn"],
            original_quantity=data["quantity"],
            current_quantity=data["quantity"],
            date_added=datetime.now(),
            added_by_id=current_user.id,
        )

        # Generate INSERT statement
        query = sql_compile(
            insert(md.Book).values(
                title=book.title,
                author=book.author,
                category_id=book.category_id,
                isbn=book.isbn,
                original_quantity=book.original_quantity,
                current_quantity=book.current_quantity,
                date_added=book.date_added,
                added_by_id=book.added_by_id,
            )
        )

        session.add(book)
        return make_response(jsonify(book_id=book.id, queries=[query]), HTTPStatus.CREATED)


@book_namespace.route("/books/<int:book_id>")
@book_namespace.doc(params={"book_id": "Book ID"})
class Book(Resource):
    def get(self, book_id):
        stmt = select(md.Book).where(md.Book.id == book_id).join(md.Category).join(md.UserAccount)
        res = session.scalars(stmt)
        book = res.first()
        book = pmd.BookDetailSchema.model_validate(book)
        return jsonify({"book": book.model_dump(), "queries": [sql_compile(stmt)]})

    @book_namespace.expect(update_book_input)
    @admin_required
    @atomic_transaction
    def put(self, book_id):
        # Get the fields to update from the request
        update_data = {}
        field_names = list(update_book_input.keys())
        for name in field_names:
            if name in request.json:
                if name == "quantity":
                    update_data["current_quantity"] = request.json[name]
                else:
                    update_data[name] = request.json[name]

        # If no fields to update, return an error
        if not update_data:
            return make_response(
                jsonify(error="No fields to update", queries=[]), HTTPStatus.NOT_MODIFIED
            )

        # Build the update statement dynamically
        update_stmt = update(md.Book).where(md.Book.id == book_id).values(**update_data)
        queries = [sql_compile(update_stmt)]
        result = session.execute(update_stmt)
        if result.rowcount == 0:
            return make_response(jsonify(error="Book not found"), 404)
        return make_response(
            jsonify(message="Book updated successfully", queries=queries), HTTPStatus.OK
        )

    @admin_required
    @atomic_transaction
    def delete(self, book_id):
        book_exists_stmt = select(md.Book.id).where(md.Book.id == book_id)
        queries = [sql_compile(book_exists_stmt)]
        book_exists = session.scalars(book_exists_stmt).first()
        if not book_exists:
            return make_response(
                jsonify(error="Book not found", queries=queries), HTTPStatus.NOT_FOUND
            )

        borrow_exists_stmt = (
            select(md.Borrow.id)
            .where(md.Borrow.book_id == book_id, md.Borrow.is_returned.is_(False))
            .exists()
        )
        queries.append("SELECT " + sql_compile(borrow_exists_stmt))
        borrow_exists = session.scalar(select(borrow_exists_stmt))
        if borrow_exists:
            return make_response(
                jsonify(
                    error="Book is borrowed and not returned yet, cannot delete",
                    queries=queries,
                ),
                HTTPStatus.BAD_REQUEST,
            )

        delete_stmt = delete(md.Book).where(md.Book.id == book_id)
        queries.append(sql_compile(delete_stmt))
        session.execute(delete_stmt)
        return make_response(
            jsonify(message="Book deleted successfully", queries=queries), HTTPStatus.OK
        )
