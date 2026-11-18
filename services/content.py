from abc import ABC, abstractmethod

from models.content import Comment, Question, QuestionStatus, ReviewStatus
from models.profile import Expert, Specialist, User
from services import ServiceError, require
from services.notification import NotificationService
from services.reputation import ReputationService
from services.search import SearchService
from storage import Database


class ContentService(ABC):
    @abstractmethod
    def create_question(self, question: Question, tags: list[str]) -> Question: ...

    @abstractmethod
    def create_comment(self, comment: Comment) -> Comment: ...

    @abstractmethod
    def mark_best_answer(self, comment_id: int, actor: User) -> Comment: ...

    @abstractmethod
    def review_comment(self, comment_id: int, status: ReviewStatus, actor: User, note: str = "") -> Comment: ...

    @abstractmethod
    def subscribe(self, user_id: int, question_id: int) -> None: ...

    @abstractmethod
    def close_question(self, question_id: int, actor: User) -> Question: ...

    @abstractmethod
    def edit_tags(self, question_id: int, tags: list[str], actor: User) -> Question: ...

    @abstractmethod
    def get_question(self, question_id: int) -> Question: ...

    @abstractmethod
    def is_subscribed(self, user_id: int, question_id: int) -> bool: ...

    @abstractmethod
    def get_unreviewed_comments(self, actor: User) -> list[Comment]: ...

    @abstractmethod
    def get_active_questions(self, actor: User) -> list[Question]: ...


class ContentServiceImpl(ContentService):
    def __init__(self, db: Database, search_service: SearchService,
                 notification_service: NotificationService, reputation_service: ReputationService):
        self.db = db
        self.search_service = search_service
        self.notification_service = notification_service
        self.reputation_service = reputation_service

    def create_question(self, question: Question, tags: list[str]) -> Question:
        self._require_specialist(question.author)
        question.title, question.description = question.title.strip(), question.description.strip()
        require(bool(question.title and question.description), "Укажите заголовок и описание")
        tags = self._clean_tags(tags)
        question = self.db.save_question(question, tags)
        self.search_service.index_question(question)
        self.notification_service.notify_subscribers(question)
        return question

    def create_comment(self, comment: Comment) -> Comment:
        self._require_specialist(comment.author)
        question = self.get_question(comment.question_id)
        require(question.status != QuestionStatus.CLOSED, "Тема закрыта, оставлять ответы нельзя")
        comment.text = comment.text.strip()
        require(bool(comment.text), "Ответ не может быть пустым")
        comment = self.db.save_comment(comment)
        self.notification_service.notify_author(comment)
        return comment

    def mark_best_answer(self, comment_id: int, actor: User) -> Comment:
        comment = self._comment(comment_id)
        question = self.get_question(comment.question_id)
        require(question.author.id == actor.id, "Выбрать лучший ответ может только автор вопроса")
        require(question.status != QuestionStatus.SOLVED, "Лучший ответ уже выбран")
        require(question.status == QuestionStatus.OPEN, "Тема закрыта")
        require(comment.author.id != actor.id, "Нельзя выбрать лучшим свой ответ")
        comment = self.db.update_best_answer(comment_id)
        self.db.update_question_status(question.id, QuestionStatus.SOLVED)
        self.reputation_service.add_points(comment_id)
        return comment

    def review_comment(self, comment_id: int, status: ReviewStatus, actor: User, note: str = "") -> Comment:
        self._require_expert(actor)
        comment = self._comment(comment_id)
        require(comment.review_status == ReviewStatus.NOT_REVIEWED, "Ответ уже проверен")
        require(status != ReviewStatus.NOT_REVIEWED, "Недопустимый статус проверки")
        return self.db.update_review(comment_id, status, note.strip())

    def subscribe(self, user_id: int, question_id: int) -> None:
        self._require_specialist(self.db.find_user(user_id))
        self.get_question(question_id)
        self.db.save_subscription(user_id, question_id)

    def close_question(self, question_id: int, actor: User) -> Question:
        self._require_expert(actor)
        require(self.get_question(question_id).status != QuestionStatus.CLOSED, "Тема уже закрыта")
        self.db.update_question_status(question_id, QuestionStatus.CLOSED)
        return self.get_question(question_id)

    def edit_tags(self, question_id: int, tags: list[str], actor: User) -> Question:
        self._require_expert(actor)
        require(self.get_question(question_id).status != QuestionStatus.CLOSED, "Тема закрыта")
        question = self.db.update_tags(question_id, self._clean_tags(tags))
        self.search_service.index_question(question)
        return question

    def get_question(self, question_id: int) -> Question:
        question = self.db.find_question(question_id)
        require(question is not None, "Вопрос не найден")
        return question

    def is_subscribed(self, user_id: int, question_id: int) -> bool:
        return self.db.is_subscribed(user_id, question_id)

    def get_unreviewed_comments(self, actor: User) -> list[Comment]:
        self._require_expert(actor)
        return self.db.find_comments_by_status(ReviewStatus.NOT_REVIEWED)

    def get_active_questions(self, actor: User) -> list[Question]:
        self._require_expert(actor)
        return self.db.find_questions_by_status(QuestionStatus.OPEN, QuestionStatus.SOLVED)

    def _comment(self, comment_id: int) -> Comment:
        comment = self.db.find_comment(comment_id)
        require(comment is not None, "Ответ не найден")
        return comment

    @staticmethod
    def _clean_tags(tags: list[str]) -> list[str]:
        tags = list(dict.fromkeys(t.strip().lower() for t in tags if t.strip()))
        require(bool(tags), "Укажите хотя бы один тег")
        return tags

    @staticmethod
    def _require_specialist(user: User | None):
        if not isinstance(user, Specialist):
            raise ServiceError("Действие доступно только специалистам")

    @staticmethod
    def _require_expert(user: User):
        if not isinstance(user, Expert):
            raise ServiceError("Действие доступно только эксперту")
