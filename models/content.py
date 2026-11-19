from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from models.profile import Expert, Specialist
from models.reputation import Rating


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
    createdAt: datetime = field(default_factory=datetime.now)
    isBestAnswer: bool = False
    reviewStatus: str = ReviewStatus.NOT_REVIEWED
    author: Specialist | None = None
    reviewer: Expert | None = None
    ratings: list[Rating] = field(default_factory=list)
    questionId: int | None = None
    remark: str = ""


@dataclass
class Question:
    id: int | None
    title: str
    description: str
    createdAt: datetime = field(default_factory=datetime.now)
    author: Specialist | None = None
    tags: list[Tag] = field(default_factory=list)
    comments: list[Comment] = field(default_factory=list)
    subscribers: list[Specialist] = field(default_factory=list)
    status: str = QuestionStatus.OPEN
