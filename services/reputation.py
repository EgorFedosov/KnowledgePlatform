from abc import ABC, abstractmethod

from models.profile import Specialist
from models.reputation import BEST_ANSWER_POINTS, USEFUL_POINTS, Rating
from services import require
from services.notification import NotificationService
from services.profile import ProfileService
from storage import Database

STATUSES = [(300, "Знаток"), (50, "Активный участник"), (0, "Новичок")]


class ReputationService(ABC):
    @abstractmethod
    def rate_comment(self, rating: Rating) -> Rating: ...

    @abstractmethod
    def add_points(self, comment_id: int) -> Rating: ...

    @abstractmethod
    def assign_status(self, user_id: int) -> str: ...


class ReputationServiceImpl(ReputationService):
    def __init__(self, db: Database, profile_service: ProfileService, notification_service: NotificationService):
        self.db = db
        self.profile_service = profile_service
        self.notification_service = notification_service

    def rate_comment(self, rating: Rating) -> Rating:
        comment = self.db.find_comment(rating.comment_id)
        require(comment is not None, "Ответ не найден")
        require(isinstance(self.profile_service.get_user(rating.author_id), Specialist),
                "Оценивать ответы могут только специалисты")
        require(comment.author.id != rating.author_id, "Нельзя оценить свой ответ")
        require(not any(r.author_id == rating.author_id and r.value == USEFUL_POINTS for r in comment.ratings),
                "Вы уже оценили этот ответ")
        rating.value = USEFUL_POINTS
        return self._reward(comment.author.id, rating)

    def add_points(self, comment_id: int) -> Rating:
        comment = self.db.find_comment(comment_id)
        question = self.db.find_question(comment.question_id)
        return self._reward(comment.author.id, Rating(None, BEST_ANSWER_POINTS, comment_id, question.author.id))

    def assign_status(self, user_id: int) -> str:
        rating = self.profile_service.get_user(user_id).rating
        status = next(name for limit, name in STATUSES if rating >= limit)
        self.db.update_user_status(user_id, status)
        return status

    def _reward(self, user_id: int, rating: Rating) -> Rating:
        self.db.save_rating(rating)
        self.profile_service.update_rating(user_id, rating)
        self.assign_status(user_id)
        self.notification_service.notify_points(user_id, rating)
        return rating
