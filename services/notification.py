from abc import ABC, abstractmethod

from models.content import Comment, Question
from models.notification import Notification, NotificationType
from models.reputation import BEST_ANSWER_POINTS, Rating
from storage import Database


class NotificationService(ABC):
    @abstractmethod
    def notify_subscribers(self, question: Question) -> None: ...

    @abstractmethod
    def notify_author(self, comment: Comment) -> None: ...

    @abstractmethod
    def notify_points(self, user_id: int, rating: Rating) -> None: ...

    @abstractmethod
    def get_notifications(self, user_id: int) -> list[Notification]: ...


class NotificationServiceImpl(NotificationService):
    def __init__(self, db: Database):
        self.db = db

    def notify_subscribers(self, question: Question) -> None:
        for user_id, tag in self.db.find_topic_subscribers(question):
            text = f"В теме «{tag}» задан вопрос «{question.title}»"
            self._send(NotificationType.NEW_QUESTION, text, user_id, question.id)

    def notify_author(self, comment: Comment) -> None:
        question = self.db.find_question(comment.question_id)
        if question.author.id != comment.author.id:
            text = f"{comment.author.name} ответил(а) на ваш вопрос «{question.title}»"
            self._send(NotificationType.NEW_ANSWER, text, question.author.id, question.id)

    def notify_points(self, user_id: int, rating: Rating) -> None:
        reason = "Ваш ответ выбран лучшим" if rating.value == BEST_ANSWER_POINTS else "Ваш ответ отметили полезным"
        points = f"+{rating.value} {'балл' if rating.value == 1 else 'баллов'}"
        comment = self.db.find_comment(rating.comment_id)
        self._send(NotificationType.POINTS, f"{reason}: {points}", user_id, comment.question_id)

    def get_notifications(self, user_id: int) -> list[Notification]:
        return self.db.find_notifications(user_id)

    def _send(self, type: NotificationType, text: str, user_id: int, question_id: int):
        self.db.save_notification(Notification(None, type, text, user_id, question_id))
