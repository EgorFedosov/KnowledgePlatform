from abc import ABC, abstractmethod

from models.content import Comment, Question
from models.notification import Notification, NotificationType
from models.profile import User
from models.reputation import BEST_ANSWER_POINTS, Rating
from storage import Database


class NotificationService(ABC):
    @abstractmethod
    def notifySubscribers(self, question: Question) -> None: ...

    @abstractmethod
    def notifyAuthor(self, comment: Comment) -> None: ...

    @abstractmethod
    def notifyPoints(self, userId: int, rating: Rating) -> None: ...

    @abstractmethod
    def getNotifications(self, userId: int) -> list[Notification]: ...


class NotificationServiceImpl(NotificationService):
    def __init__(self, database: Database):
        self.database = database

    def notifySubscribers(self, question: Question) -> None:
        for user, tag in self.database.findTopicSubscribers(question):
            self._send(NotificationType.NEW_QUESTION, f"В теме «{tag}» задан вопрос «{question.title}»",
                       user, question.id)

    def notifyAuthor(self, comment: Comment) -> None:
        question = self.database.findQuestion(comment.questionId)
        if question.author.id != comment.author.id:
            self._send(NotificationType.NEW_ANSWER,
                       f"{comment.author.name} ответил(а) на ваш вопрос «{question.title}»",
                       question.author, question.id)

    def notifyPoints(self, userId: int, rating: Rating) -> None:
        reason = "Ваш ответ выбран лучшим" if rating.value == BEST_ANSWER_POINTS else "Ваш ответ отметили полезным"
        points = f"+{rating.value} {'балл' if rating.value == 1 else 'баллов'}"
        comment = self.database.findComment(rating.commentId)
        self._send(NotificationType.POINTS, f"{reason}: {points}", self.database.findUser(userId), comment.questionId)

    def getNotifications(self, userId: int) -> list[Notification]:
        return self.database.findNotifications(userId)

    def _send(self, type: str, text: str, recipient: User, questionId: int):
        self.database.save(Notification(None, type, text, recipient=recipient, questionId=questionId))
