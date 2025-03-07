from datetime import datetime
from http import HTTPStatus
from uuid import uuid4

from flask import jsonify, make_response, request
from flask_jwt_extended import current_user, jwt_required
from flask_restx import Namespace, Resource, fields
from sqlalchemy import and_, func, insert, select, update

import src.models as md
import src.p_models as pmd
from src.auth.oauth import admin_required
from src.utils import (
    PAYMENT_METHODS,
    atomic_transaction,
    calculate_due_date,
    check_overdue_and_create_fine,
    session,
    sql_compile,
)

borrow_namespace = Namespace("Borrows", description="Borrow / Return operations", path="/")

borrow_book_input = borrow_namespace.model(
    "BorrowBookInput",
    {
        "book_id": fields.Integer(required=True, description="Book ID"),
        "borrower_id": fields.Integer(required=True, description="Borrower ID"),
    },
)


return_book_input = borrow_namespace.model(
    "ReturnBookInput",
    {
        "borrow_id": fields.Integer(required=True, description="Borrower ID"),
    },
)

pay_fine_input = borrow_namespace.model(
    "PayFineInput",
    {
        "method": fields.String(
            required=True,
            description="Payment method",
            enum=PAYMENT_METHODS,
        ),
    },
)


@borrow_namespace.route("/borrow-book")
class BorrowBook(Resource):
    @borrow_namespace.expect(borrow_book_input)
    @admin_required
    @atomic_transaction
    def post(self):
        data = request.json
        book_id = data["book_id"]
        borrower_id = data["borrower_id"]
        stmt = select(func.count()).where(md.Borrow.borrowed_by_id == borrower_id)
        queries = [sql_compile(stmt)]
        borrow_count = session.scalar(stmt)
        if borrow_count >= 5:
            return make_response(
                jsonify(
                    error="Borrower has reached the maximum limit of 5 borrowed books",
                    queries=queries,
                ),
                HTTPStatus.BAD_REQUEST,
            )

        stmt = select(md.Book.id, md.Book.current_quantity).where(md.Book.id == book_id)
        queries.append(sql_compile(stmt))
        book = session.execute(stmt).mappings().first()
        if not book:
            return make_response(
                jsonify(error="Book not found", queries=queries), HTTPStatus.NOT_FOUND
            )

        if book.current_quantity == 0:
            return make_response(
                jsonify(error="Book is out of stock or is borrowed", queries=queries),
                HTTPStatus.BAD_REQUEST,
            )

        due_date = calculate_due_date()
        stmt = insert(md.Borrow).values(
            book_id=book_id,
            borrowed_by_id=borrower_id,
            given_by_id=current_user.id,
            borrow_date=datetime.now(),
            due_date=due_date,
        )
        queries.append(sql_compile(stmt))
        session.execute(stmt)
        stmt = (
            update(md.Book)
            .where(md.Book.id == book_id)
            .values(current_quantity=md.Book.current_quantity - 1)
        )
        queries.append(sql_compile(stmt))
        session.execute(stmt)
        return make_response(
            jsonify(message="Book borrowed successfully", queries=queries), HTTPStatus.CREATED
        )


@borrow_namespace.route("/return-book")
class ReturnBook(Resource):
    @borrow_namespace.expect(return_book_input)
    @admin_required
    @atomic_transaction
    def post(self):
        data = request.json
        borrow_id = data["borrow_id"]
        stmt = select(md.Borrow).where(md.Borrow.id == borrow_id)
        queries = [sql_compile(stmt)]
        borrow = session.scalars(stmt).first()
        if not borrow:
            return make_response(
                jsonify(error="Borrow record not found", queries=queries), HTTPStatus.NOT_FOUND
            )
        if borrow.is_returned:
            return make_response(
                jsonify(error="Book already returned", queries=queries), HTTPStatus.BAD_REQUEST
            )
        now = datetime.now()
        stmt = (
            update(md.Borrow)
            .where(md.Borrow.id == borrow_id)
            .values(is_returned=True, return_date=now, received_by_id=current_user.id)
        )
        queries.append(sql_compile(stmt))
        session.execute(stmt)
        stmt = (
            update(md.Book)
            .where(md.Book.id == borrow.book_id)
            .values(current_quantity=md.Book.current_quantity + 1)
        )
        queries.append(sql_compile(stmt))
        session.execute(stmt)
        overdue_query = check_overdue_and_create_fine(borrow, now, commit=False)
        if overdue_query:
            queries.append(overdue_query)

        session.commit()
        return make_response(
            jsonify(message="Book returned successfully", queries=queries), HTTPStatus.OK
        )


@borrow_namespace.route("/borrows")
class Borrows(Resource):
    @jwt_required()
    def get(self):
        stmt = select(md.Borrow).where(md.Borrow.borrowed_by_id == current_user.id)
        borrows = session.execute(stmt).scalars().all()
        borrows = [pmd.ListBorrowSchema.model_validate(borrow) for borrow in borrows]
        return make_response(
            jsonify(
                {
                    "borrows": [borrow.model_dump() for borrow in borrows],
                    "queries": [sql_compile(stmt)],
                }
            )
        )


@borrow_namespace.route("/borrows/<int:borrow_id>")
class Borrow(Resource):
    @jwt_required()
    def get(self, borrow_id):
        stmt = select(md.Borrow).where(
            and_(md.Borrow.id == borrow_id, md.Borrow.borrowed_by_id == current_user.id)
        )
        borrow = session.execute(stmt).scalars().first()
        if not borrow:
            return make_response(
                jsonify(error="Borrow record not found", queries=[sql_compile(stmt)]),
                HTTPStatus.NOT_FOUND,
            )

        borrow = pmd.DetailBorrowSchema.model_validate(borrow)
        return make_response(
            jsonify({"borrow": borrow.model_dump(), "queries": [sql_compile(stmt)]})
        )


@borrow_namespace.route("/borrows-admin/<int:user_id>")
class BorrowsAdmin(Resource):
    @admin_required
    @borrow_namespace.doc(params={"user_id": "User ID"})
    def get(self, user_id):
        stmt = select(md.Borrow).where(md.Borrow.borrowed_by_id == user_id)
        borrows = session.execute(stmt).scalars().all()
        borrows = [pmd.ListBorrowSchema.model_validate(borrow) for borrow in borrows]
        return make_response(
            jsonify(
                {
                    "borrows": [borrow.model_dump() for borrow in borrows],
                    "queries": [sql_compile(stmt)],
                }
            )
        )


@borrow_namespace.route("/borrows-admin/<int:user_id>/<int:borrow_id>")
class BorrowAdmin(Resource):
    @admin_required
    def get(self, user_id, borrow_id):
        stmt = select(md.Borrow).where(
            and_(md.Borrow.id == borrow_id, md.Borrow.borrowed_by_id == user_id)
        )
        borrow = session.execute(stmt).scalars().first()
        if not borrow:
            return make_response(
                jsonify(error="Borrow record not found", queries=[sql_compile(stmt)]),
                HTTPStatus.NOT_FOUND,
            )

        borrow = pmd.DetailBorrowSchema.model_validate(borrow)
        return make_response(
            jsonify({"borrow": borrow.model_dump(), "queries": [sql_compile(stmt)]})
        )


@borrow_namespace.route("/fines")
class Fines(Resource):
    @jwt_required()
    def get(self):
        stmt = select(md.Fine).where(
            md.Fine.borrow.has(md.Borrow.borrowed_by_id == current_user.id)
        )
        # Calculate total fines using the same filters
        total_query = (
            select(func.sum(md.Fine.amount).label("total_fines"))
            .join(md.Borrow, md.Fine.borrow_id == md.Borrow.id)
            .join(md.UserAccount, md.Borrow.borrowed_by_id == md.UserAccount.id)
        ).where(md.UserAccount.id == current_user.id)

        queries = []
        status = request.args.get("status")
        paid_query = total_query.where(md.Fine.paid.is_(True))
        unpaid_query = total_query.where(md.Fine.paid.is_(False))
        paid = None
        unpaid = None

        if status == "paid":
            stmt = stmt.where(md.Fine.paid.is_(True))
            queries = [sql_compile(paid_query)]
            paid = session.execute(paid_query).scalar()
        elif status == "unpaid":
            stmt = stmt.where(md.Fine.paid.is_(False))
            queries = [sql_compile(unpaid_query)]
            unpaid = session.execute(unpaid_query).scalar()
        else:
            paid = session.execute(paid_query).scalar()
            unpaid = session.execute(unpaid_query).scalar()
            queries = [sql_compile(stmt), sql_compile(paid_query), sql_compile(unpaid_query)]

        queries.insert(0, sql_compile(stmt))
        fines = session.execute(stmt).scalars().all()
        fines = [pmd.FineListSchema.model_validate(fine) for fine in fines]
        return make_response(
            jsonify(
                {
                    "fines": [fine.model_dump() for fine in fines],
                    "total_paid": paid,
                    "total_unpaid": unpaid,
                    "queries": queries,
                }
            )
        )


@borrow_namespace.route("/fines/<int:fine_id>")
class Fine(Resource):
    @jwt_required()
    def get(self, fine_id):
        stmt = select(md.Fine).where(
            and_(
                md.Fine.id == fine_id,
                md.Fine.borrow.has(md.Borrow.borrowed_by_id == current_user.id),
            )
        )
        fine = session.execute(stmt).scalars().first()
        if not fine:
            return make_response(
                jsonify(error="Fine record not found", queries=[sql_compile(stmt)]),
                HTTPStatus.NOT_FOUND,
            )

        fine = pmd.FineListSchema.model_validate(fine)
        return make_response(jsonify({"fine": fine.model_dump(), "queries": [sql_compile(stmt)]}))


@borrow_namespace.route("/fines-admin/<int:user_id>")
class FinesAdmin(Resource):
    @admin_required
    def get(self, user_id):
        stmt = select(md.Fine).where(md.Fine.borrow.has(md.Borrow.borrowed_by_id == user_id))
        fines = session.execute(stmt).scalars().all()
        fines = [pmd.FineListSchema.model_validate(fine) for fine in fines]
        return make_response(
            jsonify(
                {
                    "fines": [fine.model_dump() for fine in fines],
                    "queries": [sql_compile(stmt)],
                }
            )
        )


@borrow_namespace.route("/fines-admin/<int:user_id>/<int:fine_id>")
class FineAdmin(Resource):
    @admin_required
    def get(self, user_id, fine_id):
        stmt = select(md.Fine).where(
            and_(
                md.Fine.id == fine_id,
                md.Fine.borrow.has(md.Borrow.borrowed_by_id == user_id),
            )
        )
        fine = session.execute(stmt).scalars().first()
        if not fine:
            return make_response(
                jsonify(error="Fine record not found", queries=[sql_compile(stmt)]),
                HTTPStatus.NOT_FOUND,
            )

        fine = pmd.FineListSchema.model_validate(fine)
        return make_response(jsonify({"fine": fine.model_dump(), "queries": [sql_compile(stmt)]}))


@borrow_namespace.route("/pay-fine/<int:fine_id>")
class PayFine(Resource):
    @jwt_required()
    @atomic_transaction
    def post(self, fine_id):
        method = request.json.get("method")
        if method not in PAYMENT_METHODS:
            return make_response(
                jsonify(error=f"Invalid payment method. Must be one of {PAYMENT_METHODS}"),
                HTTPStatus.BAD_REQUEST,
            )
        if method == "cash" and current_user.role != "admin":
            return make_response(
                jsonify(
                    error="Only admins can accept fines in cash in person at the library",
                    queries=[],
                ),
                HTTPStatus.FORBIDDEN,
            )
        stmt = (
            select(md.Fine.id, md.Fine.amount, md.Fine.paid, md.Borrow.borrowed_by_id)
            .where(and_(md.Fine.id == fine_id, md.Fine.paid.is_(False)))
            .join(md.Borrow)
        )
        queries = [sql_compile(stmt)]
        fine = session.execute(stmt).mappings().first()
        if not fine:
            return make_response(
                jsonify(error="Fine not found or is already paid", queries=queries),
                HTTPStatus.NOT_FOUND,
            )

        if method == "cash":
            stmt = (
                update(md.Fine)
                .where(md.Fine.id == fine_id)
                .values(
                    paid=True,
                    date_paid=datetime.now(),
                    payment_method="cash",
                    collected_by_id=current_user.id,
                )
            )
        else:
            if current_user.role != "admin" and fine.borrowed_by_id != current_user.id:
                return make_response(
                    jsonify(
                        error="You can only pay fines for your own borrowed books using online payment",
                        queries=queries,
                    ),
                    HTTPStatus.FORBIDDEN,
                )
            # do something to process online payment
            stmt = (
                update(md.Fine)
                .where(md.Fine.id == fine_id)
                .values(
                    paid=True,
                    date_paid=datetime.now(),
                    payment_method=method,
                    transaction_id=uuid4().hex,
                    collected_by_id=current_user.id if current_user.role == "admin" else None,
                )
            )
        queries.append(sql_compile(stmt))
        session.execute(stmt)
        return make_response(
            jsonify(message="Fine paid successfully", queries=queries), HTTPStatus.OK
        )
