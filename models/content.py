from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from models.profile import User
from models.reputation import Rating, USEFUL_POINTS


class QuestionStatus(StrEnum):
    OPEN = "Открыт"
    SOLVED = "Решён"
    CLOSED = "Закрыт"


class ReviewStatus(StrEnum):
    NOT_REVIEWED = "Не проверен"
    CONFIRMED = "Подтверждён"
    REJECTED = "Отклонён"


@dataclass
class Tag:
    id: int | None
    name: str


@dataclass
class Comment:
    id: int | None
    text: str
    question_id: int
    author: User
    created_at: datetime = field(default_factory=datetime.now)
    is_best_answer: bool = False
    review_status: ReviewStatus = ReviewStatus.NOT_REVIEWED
    review_note: str = ""
    ratings: list[Rating] = field(default_factory=list)

    @property
    def useful_count(self) -> int:
        return sum(1 for r in self.ratings if r.value == USEFUL_POINTS)


@dataclass
class Question:
    id: int | None
    title: str
    description: str
    author: User
    created_at: datetime = field(default_factory=datetime.now)
    status: QuestionStatus = QuestionStatus.OPEN
    tags: list[Tag] = field(default_factory=list)
    comments: list[Comment] = field(default_factory=list)
