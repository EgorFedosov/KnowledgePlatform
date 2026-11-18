from abc import ABC, abstractmethod

from models.content import Question, Tag
from storage import Database


class SearchService(ABC):
    @abstractmethod
    def search(self, keywords: str, tags: list[str]) -> list[Question]: ...

    @abstractmethod
    def get_feed(self, user_id: int) -> list[Question]: ...

    @abstractmethod
    def index_question(self, question: Question) -> None: ...

    @abstractmethod
    def get_tags(self) -> list[Tag]: ...


class SearchServiceImpl(SearchService):
    def __init__(self, db: Database):
        self.db = db

    def search(self, keywords: str, tags: list[str]) -> list[Question]:
        return self.db.find_by_keywords_and_tags(keywords.lower().split(), tags)

    def get_feed(self, user_id: int) -> list[Question]:
        interests = self.db.find_user_tag_names(user_id)
        questions = self.db.find_questions()
        return sorted(questions, key=lambda q: not interests & {t.name for t in q.tags})

    def index_question(self, question: Question) -> None:
        words = [question.title, question.description] + [t.name for t in question.tags]
        self.db.save_index(question.id, " ".join(words).lower())

    def get_tags(self) -> list[Tag]:
        return self.db.find_tags()
