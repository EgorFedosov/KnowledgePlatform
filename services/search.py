from abc import ABC, abstractmethod

from models.content import Question, Tag
from storage import Database


class SearchService(ABC):
    @abstractmethod
    def search(self, keywords: str, tags: list[Tag]) -> list[Question]: ...

    @abstractmethod
    def getFeed(self, userId: int) -> list[Question]: ...

    @abstractmethod
    def indexQuestion(self, question: Question) -> None: ...


class SearchServiceImpl(SearchService):
    def __init__(self, database: Database):
        self.database = database

    def search(self, keywords: str, tags: list[Tag]) -> list[Question]:
        return self.database.findByKeywordsAndTags(keywords, tags)

    def getFeed(self, userId: int) -> list[Question]:
        interests = self.database.findUserTagNames(userId)
        return sorted(self.database.findQuestions(), key=lambda q: not interests & {t.name for t in q.tags})

    def indexQuestion(self, question: Question) -> None:
        self.database.saveIndex(question)
