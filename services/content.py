from abc import ABC, abstractmethod

from models.content import Comment, Question, QuestionStatus, ReviewStatus, Tag
from models.profile import Expert, Specialist
from services import currentUser, require, requireRole
from services.notification import NotificationService
from services.reputation import ReputationService
from services.search import SearchService
from storage import Database

EXPERT_ONLY = "Действие доступно только эксперту"


class ContentService(ABC):
    @abstractmethod
    def createQuestion(self, question: Question, tags: list[Tag]) -> Question: ...

    @abstractmethod
    def createComment(self, comment: Comment) -> Comment: ...

    @abstractmethod
    def markBestAnswer(self, commentId: int) -> Comment: ...

    @abstractmethod
    def reviewComment(self, commentId: int, status: str, remark: str = "") -> Comment: ...

    @abstractmethod
    def subscribe(self, userId: int, questionId: int) -> None: ...

    @abstractmethod
    def closeQuestion(self, questionId: int) -> Question: ...

    @abstractmethod
    def updateTags(self, questionId: int, tags: list[Tag]) -> Question: ...

    @abstractmethod
    def getQuestion(self, questionId: int) -> Question: ...

    @abstractmethod
    def getQuestions(self) -> list[Question]: ...


class ContentServiceImpl(ContentService):
    def __init__(self, database: Database, searchService: SearchService,
                 notificationService: NotificationService, reputationService: ReputationService):
        self.database = database
        self.searchService = searchService
        self.notificationService = notificationService
        self.reputationService = reputationService

    def createQuestion(self, question: Question, tags: list[Tag]) -> Question:
        require(isinstance(question.author, Specialist), "Задавать вопросы могут только специалисты")
        question.title, question.description = question.title.strip(), question.description.strip()
        require(bool(question.title and question.description), "Укажите заголовок и описание")
        question.tags = self._cleanTags(tags)
        question = self.database.save(question)
        self.searchService.indexQuestion(question)
        self.notificationService.notifySubscribers(question)
        return question

    def createComment(self, comment: Comment) -> Comment:
        require(isinstance(comment.author, Specialist), "Отвечать могут только специалисты")
        question = self.getQuestion(comment.questionId)
        require(question.status != QuestionStatus.CLOSED, "Тема закрыта, оставлять ответы нельзя")
        comment.text = comment.text.strip()
        require(bool(comment.text), "Ответ не может быть пустым")
        comment = self.database.save(comment)
        self.notificationService.notifyAuthor(comment)
        return comment

    def markBestAnswer(self, commentId: int) -> Comment:
        comment = self._comment(commentId)
        question = self.getQuestion(comment.questionId)
        user = currentUser()
        require(user is not None and question.author.id == user.id, "Выбрать лучший ответ может только автор вопроса")
        require(question.status != QuestionStatus.SOLVED, "Лучший ответ уже выбран")
        require(question.status == QuestionStatus.OPEN, "Тема закрыта")
        require(comment.author.id != user.id, "Нельзя выбрать лучшим свой ответ")
        comment = self.database.updateBestAnswer(commentId)
        self.database.updateQuestionStatus(question.id, QuestionStatus.SOLVED)
        self.reputationService.addPoints(commentId)
        return comment

    def reviewComment(self, commentId: int, status: str, remark: str = "") -> Comment:
        requireRole(Expert, EXPERT_ONLY)
        comment = self._comment(commentId)
        require(comment.reviewStatus == ReviewStatus.NOT_REVIEWED, "Ответ уже проверен")
        require(status in (ReviewStatus.CONFIRMED, ReviewStatus.REJECTED), "Недопустимый статус проверки")
        comment.reviewStatus, comment.reviewer, comment.remark = status, currentUser(), remark.strip()
        return self.database.updateReview(comment)

    def subscribe(self, userId: int, questionId: int) -> None:
        require(isinstance(self.database.findUser(userId), Specialist), "Подписываться могут только специалисты")
        self.getQuestion(questionId)
        self.database.saveSubscription(userId, questionId)

    def closeQuestion(self, questionId: int) -> Question:
        requireRole(Expert, EXPERT_ONLY)
        require(self.getQuestion(questionId).status != QuestionStatus.CLOSED, "Тема уже закрыта")
        return self.database.updateQuestionStatus(questionId, QuestionStatus.CLOSED)

    def updateTags(self, questionId: int, tags: list[Tag]) -> Question:
        requireRole(Expert, EXPERT_ONLY)
        require(self.getQuestion(questionId).status != QuestionStatus.CLOSED, "Тема закрыта")
        question = self.database.updateTags(questionId, self._cleanTags(tags))
        self.searchService.indexQuestion(question)
        return question

    def getQuestion(self, questionId: int) -> Question:
        question = self.database.findQuestion(questionId)
        require(question is not None, "Вопрос не найден")
        return question

    def getQuestions(self) -> list[Question]:
        return self.database.findQuestions()

    def _comment(self, commentId: int) -> Comment:
        comment = self.database.findComment(commentId)
        require(comment is not None, "Ответ не найден")
        return comment

    @staticmethod
    def _cleanTags(tags: list[Tag]) -> list[Tag]:
        names = list(dict.fromkeys(t.name.strip().lower() for t in tags if t.name.strip()))
        require(bool(names), "Укажите хотя бы один тег")
        return [Tag(None, name) for name in names]
