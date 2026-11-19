from flask import g, render_template

from controllers import loginRequired
from models.content import Comment, Question
from models.notification import Notification
from models.reputation import Rating
from services.notification import NotificationService


class NotificationController:
    def __init__(self, notificationService: NotificationService):
        self.notificationService = notificationService

    def notifySubscribers(self, question: Question) -> None:
        self.notificationService.notifySubscribers(question)

    def notifyAuthor(self, comment: Comment) -> None:
        self.notificationService.notifyAuthor(comment)

    def notifyPoints(self, userId: int, rating: Rating) -> None:
        self.notificationService.notifyPoints(userId, rating)

    def getNotifications(self, userId: int) -> list[Notification]:
        return self.notificationService.getNotifications(userId)

    def bindRoutes(self, app):
        app.add_url_rule("/notifications", "notifications", loginRequired(self.notificationsWindow))
        app.context_processor(self.badge)

    def notificationsWindow(self):
        return render_template("notifications.html", notifications=self.getNotifications(g.user.id))

    def badge(self):
        return {"notificationCount": len(self.getNotifications(g.user.id)) if g.get("user") else 0}
