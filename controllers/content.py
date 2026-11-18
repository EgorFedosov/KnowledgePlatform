from flask import flash, g, redirect, render_template, request, url_for

from controllers import attempt, back, login_required, selected
from models.content import Comment, Question, ReviewStatus
from services import ServiceError
from services.content import ContentService


def split_tags(text: str) -> list[str]:
    return text.replace(";", ",").split(",")


class ContentController:
    def __init__(self, content_service: ContentService):
        self.content_service = content_service

    def create_question(self, question: Question, tags: list[str]) -> Question:
        return self.content_service.create_question(question, tags)

    def create_comment(self, comment: Comment) -> Comment:
        return self.content_service.create_comment(comment)

    def mark_best_answer(self, comment_id: int) -> Comment:
        return self.content_service.mark_best_answer(comment_id, g.user)

    def review_comment(self, comment_id: int, status: ReviewStatus, note: str = "") -> Comment:
        return self.content_service.review_comment(comment_id, status, g.user, note)

    def subscribe(self, user_id: int, question_id: int) -> None:
        self.content_service.subscribe(user_id, question_id)

    def close_question(self, question_id: int) -> Question:
        return self.content_service.close_question(question_id, g.user)

    def edit_tags(self, question_id: int, tags: list[str]) -> Question:
        return self.content_service.edit_tags(question_id, tags, g.user)

    def bind(self, app):
        rules = [("/questions/new", "new_question", self.new_question_window, ["GET", "POST"]),
                 ("/questions/<int:id>", "question", self.question_window, ["GET"]),
                 ("/questions/<int:id>/answer", "answer", self.answer, ["POST"]),
                 ("/questions/<int:id>/subscribe", "subscribe", self.subscribe_action, ["POST"]),
                 ("/comments/<int:id>/best", "best", self.best_action, ["POST"]),
                 ("/expert/review", "review", self.review_window, ["GET", "POST"]),
                 ("/expert/moderation", "moderation", self.moderation_window, ["GET", "POST"])]
        for rule, endpoint, view, methods in rules:
            app.add_url_rule(rule, endpoint, login_required(view), methods=methods)

    def new_question_window(self):
        if request.method == "POST":
            form = request.form
            try:
                question = Question(None, form["title"], form["description"], g.user)
                question = self.create_question(question, split_tags(form["tags"]))
                return redirect(url_for("question", id=question.id))
            except ServiceError as error:
                flash(str(error), "error")
        return render_template("new_question.html")

    def question_window(self, id: int):
        try:
            question = self.content_service.get_question(id)
        except ServiceError as error:
            flash(str(error), "error")
            return redirect(url_for("feed"))
        subscribed = self.content_service.is_subscribed(g.user.id, id)
        return render_template("question.html", question=question, subscribed=subscribed)

    def answer(self, id: int):
        comment = Comment(None, request.form["text"], id, g.user)
        return attempt(lambda: self.create_comment(comment), url_for("question", id=id))

    def subscribe_action(self, id: int):
        return attempt(lambda: self.subscribe(g.user.id, id), url_for("question", id=id),
                       message="Вы подписались на вопрос")

    def best_action(self, id: int):
        return attempt(lambda: self.mark_best_answer(id), back())

    def review_window(self):
        if request.method == "POST":
            status = ReviewStatus.CONFIRMED if request.form["action"] == "confirm" else ReviewStatus.REJECTED
            return attempt(lambda: self.review_comment(selected("comment_id"), status, request.form["note"]),
                           url_for("review"))
        return self._panel("review.html", self._unreviewed)

    def moderation_window(self):
        if request.method == "POST":
            def moderate():
                question_id = selected("question_id")
                if request.form["action"] == "close":
                    self.close_question(question_id)
                else:
                    self.edit_tags(question_id, split_tags(request.form["tags"]))
            return attempt(moderate, url_for("moderation"))
        return self._panel("moderation.html", self.content_service.get_active_questions)

    def _unreviewed(self, actor) -> list[tuple[Comment, str]]:
        comments = self.content_service.get_unreviewed_comments(actor)
        return [(c, self.content_service.get_question(c.question_id).title) for c in comments]

    @staticmethod
    def _panel(template: str, load):
        try:
            return render_template(template, items=load(g.user))
        except ServiceError as error:
            flash(str(error), "error")
            return redirect(url_for("feed"))
