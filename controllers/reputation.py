from flask import g

from controllers import attempt, back, login_required
from models.reputation import USEFUL_POINTS, Rating
from services.reputation import ReputationService


class ReputationController:
    def __init__(self, reputation_service: ReputationService):
        self.reputation_service = reputation_service

    def rate_comment(self, rating: Rating) -> Rating:
        return self.reputation_service.rate_comment(rating)

    def add_points(self, comment_id: int) -> Rating:
        return self.reputation_service.add_points(comment_id)

    def assign_status(self, user_id: int) -> str:
        return self.reputation_service.assign_status(user_id)

    def bind(self, app):
        app.add_url_rule("/comments/<int:id>/rate", "rate", login_required(self.rate_action), methods=["POST"])

    def rate_action(self, id: int):
        return attempt(lambda: self.rate_comment(Rating(None, USEFUL_POINTS, id, g.user.id)), back())
