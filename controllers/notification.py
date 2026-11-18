from flask import g, render_template

from controllers import login_required
from models.content import Comment, Question
from models.notification import Notification
from models.reputation import Rating
from services.notification import NotificationService


class NotificationController:
    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service

    def notify_subscribers(self, question: Question) -> None:
        self.notification_service.notify_subscribers(question)

    def notify_author(self, comment: Comment) -> None:
        self.notification_service.notify_author(comment)

    def notify_points(self, user_id: int, rating: Rating) -> None:
        self.notification_service.notify_points(user_id, rating)

    def get_notifications(self, user_id: int) -> list[Notification]:
        return self.notification_service.get_notifications(user_id)

    def bind(self, app):
        app.add_url_rule("/notifications", "notifications", login_required(self.notifications_window))
        app.context_processor(self.badge)

    def notifications_window(self):
        return render_template("notifications.html", notifications=self.get_notifications(g.user.id))

    def badge(self):
        return {"notification_count": len(self.get_notifications(g.user.id)) if g.get("user") else 0}
