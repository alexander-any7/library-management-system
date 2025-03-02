from flask import Response, jsonify, request
from flask_restx import Namespace, Resource
from sqlalchemy import select

import src.models as md
import src.p_models as pmd
from src.auth.oauth import staff_required
from src.utils import session

book_namespace = Namespace("Books", description="Book operations", path="/")


@book_namespace.route("/books")
class Books(Resource):
    def get(self):
        stmt = select(md.Book, md.Category.name).join(md.Category)
        res = session.scalars(stmt)
        books = res.all()
        books = [pmd.ListBookSchema.model_validate(book) for book in books]
        return jsonify({"books": [book.model_dump() for book in books], "query": str(stmt)})

    @staff_required
    def post(self):
        data = request.json
        print(data)
        return Response(status=201)


@book_namespace.route("/books/<int:id>")
@book_namespace.doc(params={"id": "Book ID"})
class Book(Resource):
    def get(self, id):
        stmt = select(md.Book).where(md.Book.id == id).join(md.Category).join(md.UserAccount)
        res = session.scalars(stmt)
        book = res.first()
        book = pmd.BookDetailSchema.model_validate(book)
        return jsonify({"book": book.model_dump(), "query": str(stmt)})
