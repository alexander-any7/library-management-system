from datetime import datetime

from flask import jsonify, make_response, request
from flask_restx import Namespace, Resource
from sqlalchemy import and_, func, select

import src.models as md
import src.p_models as pmd
from src.auth.oauth import admin_required
from src.utils import VALID_USER_TYPES, session, sql_compile

reports_namespace = Namespace("Reports", description="Reports operations", path="/")


@reports_namespace.route("/overdue-report")
class OverdueReports(Resource):
    @admin_required
    def get(self):
        today = datetime.now().date()
        user_type = request.args.get("user_type")
        # Base query to select borrow records and user roles where the book is overdue and not returned
        stmt = (
            select(md.Borrow, md.UserAccount.role).where(
                and_(
                    md.Borrow.due_date < today,  # Filter by due date
                    md.Borrow.is_returned.is_(False),  # Filter by books not returned
                )
            )
            # Explicitly specify the join condition between Borrow and UserAccount
            .join(md.UserAccount, md.Borrow.borrowed_by)  # Use the borrowed_by relationship
        )

        if request.args.get("sort") == "asc":
            stmt = stmt.order_by(md.Borrow.due_date.asc())

        elif request.args.get("sort") == "desc":
            stmt = stmt.order_by(md.Borrow.due_date.desc())

        if user_type in VALID_USER_TYPES:
            stmt = stmt.where(md.Borrow.borrowed_by.has(md.UserAccount.role == user_type))

        borrows = session.execute(stmt).scalars().all()
        borrows = [pmd.AdminListBorrowSchema.model_validate(borrow) for borrow in borrows]
        return make_response(
            jsonify(
                {
                    "borrows": [borrow.model_dump() for borrow in borrows],
                    "queries": [sql_compile(stmt)],
                }
            )
        )


@reports_namespace.route("/fines-report")
class CollectedFines(Resource):
    @admin_required
    def get(self):
        stmt = (
            select(md.Fine, md.UserAccount.id, md.UserAccount.role)  # Select Fine and UserAccount
            .where(md.Fine.paid.is_(True))  # Filter fines that are paid
            .join(md.Borrow, md.Fine.borrow_id == md.Borrow.id)  # Join Fine with Borrow
            .join(
                md.UserAccount, md.Borrow.borrowed_by_id == md.UserAccount.id
            )  # Join Borrow with UserAccount
        )
        user_type = request.args.get("user_type")
        if user_type in VALID_USER_TYPES:
            stmt = stmt.where(md.UserAccount.role == user_type)

        if request.args.get("sort_date_paid") == "asc":
            stmt = stmt.order_by(md.Fine.date_paid.asc())

        elif request.args.get("sort_date_paid") == "desc":
            stmt = stmt.order_by(md.Fine.date_paid.desc())

        if request.args.get("sort_date_created") == "asc":
            stmt = stmt.order_by(md.Fine.date_created.asc())

        elif request.args.get("sort_date_created") == "desc":
            stmt = stmt.order_by(md.Fine.date_created.desc())

        fines = session.execute(stmt).scalars().all()
        fines = [pmd.AdminFineListSchema.model_validate(fine) for fine in fines]
        return make_response(
            jsonify(
                {
                    "fines": [fine.model_dump() for fine in fines],
                    "queries": [sql_compile(stmt)],
                }
            )
        )


@reports_namespace.route("/borrowing-trends")
class Trends(Resource):
    @admin_required
    def get(self):
        valid_time_filter = ("day", "week", "month", "year")
        user_type = request.args.get("user_type")
        time_filter = request.args.get("time")
        category = request.args.get("category")

        stmt = select(md.Borrow)
        if user_type in VALID_USER_TYPES:
            stmt = stmt.where(md.Borrow.borrowed_by.has(role=user_type))

        if time_filter in valid_time_filter:
            stmt = stmt.where(
                func.extract(time_filter, md.Borrow.borrow_date)
                == func.extract(time_filter, datetime.now())
            )

        if category:
            stmt = stmt.join(md.Book).where(md.Book.category_id == category)

        borrows = session.execute(stmt).scalars().all()
        borrows = [pmd.AdminListBorrowSchema.model_validate(borrow) for borrow in borrows]
        return make_response(
            jsonify(
                {
                    "borrows": [borrow.model_dump() for borrow in borrows],
                    "queries": [sql_compile(stmt)],
                }
            )
        )
