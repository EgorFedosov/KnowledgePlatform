from flask import g

from controllers import attempt, back, loginRequired
from models.reputation import USEFUL_POINTS, Rating
from services.reputation import ReputationService


class ReputationController:
    def __init__(self, reputationService: ReputationService):
        self.reputationService = reputationService

    def rateComment(self, rating: Rating) -> Rating:
        return self.reputationService.rateComment(rating)

    def addPoints(self, commentId: int) -> Rating:
        return self.reputationService.addPoints(commentId)

    def assignStatus(self, userId: int) -> str:
        return self.reputationService.assignStatus(userId)

    def bindRoutes(self, app):
        app.add_url_rule("/comments/<int:id>/rate", "rate", loginRequired(self.rateAction), methods=["POST"])

    def rateAction(self, id: int):
        return attempt(lambda: self.rateComment(Rating(None, USEFUL_POINTS, g.user, id)), back())
