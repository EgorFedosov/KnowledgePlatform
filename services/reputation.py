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
    def rateComment(self, rating: Rating) -> Rating: ...

    @abstractmethod
    def addPoints(self, commentId: int) -> Rating: ...

    @abstractmethod
    def assignStatus(self, userId: int) -> str: ...


class ReputationServiceImpl(ReputationService):
    def __init__(self, database: Database, profileService: ProfileService, notificationService: NotificationService):
        self.database = database
        self.profileService = profileService
        self.notificationService = notificationService

    def rateComment(self, rating: Rating) -> Rating:
        comment = self.database.findComment(rating.commentId)
        require(comment is not None, "Ответ не найден")
        require(isinstance(rating.author, Specialist), "Оценивать ответы могут только специалисты")
        require(comment.author.id != rating.author.id, "Нельзя оценить свой ответ")
        require(not any(r.author.id == rating.author.id and r.value == USEFUL_POINTS for r in comment.ratings),
                "Вы уже оценили этот ответ")
        rating.value = USEFUL_POINTS
        return self._reward(comment.author.id, rating)

    def addPoints(self, commentId: int) -> Rating:
        comment = self.database.findComment(commentId)
        question = self.database.findQuestion(comment.questionId)
        rating = Rating(None, BEST_ANSWER_POINTS, question.author, commentId)
        return self._reward(comment.author.id, rating)

    def assignStatus(self, userId: int) -> str:
        user = self.profileService.getUser(userId)
        user.reputationStatus = next(name for limit, name in STATUSES if user.rating >= limit)
        self.database.updateUser(user)
        return user.reputationStatus

    def _reward(self, userId: int, rating: Rating) -> Rating:
        self.database.saveRating(rating)
        self.profileService.updateRating(userId, rating)
        self.assignStatus(userId)
        self.notificationService.notifyPoints(userId, rating)
        return rating
