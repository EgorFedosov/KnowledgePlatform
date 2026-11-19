from flask import flash, g, redirect, render_template, request, url_for

from controllers import attempt, back, loginRequired, parseTags, selected
from models.content import Comment, Question, QuestionStatus, ReviewStatus, Tag
from models.profile import Expert
from services import ServiceError
from services.content import ContentService


class ContentController:
    def __init__(self, contentService: ContentService):
        self.contentService = contentService

    def createQuestion(self, question: Question, tags: list[Tag]) -> Question:
        return self.contentService.createQuestion(question, tags)

    def createComment(self, comment: Comment) -> Comment:
        return self.contentService.createComment(comment)

    def markBestAnswer(self, commentId: int) -> Comment:
        return self.contentService.markBestAnswer(commentId)

    def reviewComment(self, commentId: int, status: str, remark: str = "") -> Comment:
        return self.contentService.reviewComment(commentId, status, remark)

    def subscribe(self, userId: int, questionId: int) -> None:
        self.contentService.subscribe(userId, questionId)

    def closeQuestion(self, questionId: int) -> Question:
        return self.contentService.closeQuestion(questionId)

    def updateTags(self, questionId: int, tags: list[Tag]) -> Question:
        return self.contentService.updateTags(questionId, tags)

    def bindRoutes(self, app):
        rules = [("/questions/new", "new_question", self.newQuestionWindow, ["GET", "POST"]),
                 ("/questions/<int:id>", "question", self.questionWindow, ["GET"]),
                 ("/questions/<int:id>/answer", "answer", self.answerAction, ["POST"]),
                 ("/questions/<int:id>/subscribe", "subscribe", self.subscribeAction, ["POST"]),
                 ("/comments/<int:id>/best", "best", self.bestAnswerAction, ["POST"]),
                 ("/expert/review", "review", self.reviewWindow, ["GET", "POST"]),
                 ("/expert/moderation", "moderation", self.moderationWindow, ["GET", "POST"])]
        for rule, endpoint, view, methods in rules:
            app.add_url_rule(rule, endpoint, loginRequired(view), methods=methods)

    def newQuestionWindow(self):
        if request.method == "POST":
            form = request.form
            try:
                question = Question(None, form["title"], form["description"], author=g.user)
                question = self.createQuestion(question, parseTags(form["tags"]))
                return redirect(url_for("question", id=question.id))
            except ServiceError as error:
                flash(str(error), "error")
        return render_template("new_question.html")

    def questionWindow(self, id: int):
        try:
            question = self.contentService.getQuestion(id)
        except ServiceError as error:
            flash(str(error), "error")
            return redirect(url_for("feed"))
        return render_template("question.html", question=question)

    def answerAction(self, id: int):
        comment = Comment(None, request.form["text"], author=g.user, questionId=id)
        return attempt(lambda: self.createComment(comment), url_for("question", id=id))

    def subscribeAction(self, id: int):
        return attempt(lambda: self.subscribe(g.user.id, id), url_for("question", id=id), "Вы подписались на вопрос")

    def bestAnswerAction(self, id: int):
        return attempt(lambda: self.markBestAnswer(id), back())

    def reviewWindow(self):
        if request.method == "POST":
            status = ReviewStatus.CONFIRMED if request.form["action"] == "confirm" else ReviewStatus.REJECTED
            return attempt(lambda: self.reviewComment(selected("commentId"), status, request.form["remark"]),
                           url_for("review"))
        items = [(c, q.title) for q in self.contentService.getQuestions() for c in q.comments
                 if c.reviewStatus == ReviewStatus.NOT_REVIEWED]
        return self._panel("review.html", items)

    def moderationWindow(self):
        if request.method == "POST":
            def moderate():
                questionId = selected("questionId")
                if request.form["action"] == "close":
                    self.closeQuestion(questionId)
                else:
                    self.updateTags(questionId, parseTags(request.form["tags"]))
            return attempt(moderate, url_for("moderation"))
        items = [q for q in self.contentService.getQuestions() if q.status != QuestionStatus.CLOSED]
        return self._panel("moderation.html", items)

    @staticmethod
    def _panel(template: str, items):
        if not isinstance(g.user, Expert):
            flash("Панель доступна только эксперту", "error")
            return redirect(url_for("feed"))
        return render_template(template, items=items)
