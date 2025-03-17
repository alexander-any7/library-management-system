from flask import jsonify, make_response
from flask_jwt_extended import current_user, jwt_required
from flask_restx import Namespace, Resource
from sqlalchemy import and_, select, text

import src.models as md
import src.p_models as pmd
from src.utils import atomic_transaction, session, sql_compile

notifications_namespace = Namespace("Notifications", description="Notification operations", path="/")


@notifications_namespace.route("/notifications")
class Notifications(Resource):
    @jwt_required
    def get(self):
        user_id = current_user.id
        stmt = select(md.Notification).where(
            and_(md.Notification.user_id == user_id, md.Notification.is_read.is_(False))
        )
        query = sql_compile(stmt)
        notifications = session.execute(stmt).scalars().all()
        notifications = [
            pmd.NotificationListSchema.model_validate(notification)
            for notification in notifications
        ]
        return make_response(
            jsonify(
                {
                    "notifications": [notification.model_dump() for notification in notifications],
                    "queries": [query],
                }
            )
        )


@notifications_namespace.route("/notifications/<int:notification_id>")
class NotificationDetail(Resource):
    @jwt_required
    @atomic_transaction
    def post(self, notification_id):
        user_id = current_user.id
        stmt = f"UPDATE notification SET is_read = TRUE WHERE id = {notification_id} AND user_id = {user_id}"
        result = session.execute(text(stmt))
        if result.rowcount == 0:
            return make_response(
                jsonify(error="Notification not found or is already read", queries=stmt), 404
            )

        return make_response(jsonify(message="Notification marked as read", queries=stmt))
