from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from models.profile import User


class NotificationType(StrEnum):
    NEW_QUESTION = "Новый вопрос"
    NEW_ANSWER = "Новый ответ"
    POINTS = "Баллы"


@dataclass
class Notification:
    id: int | None
    type: str
    text: str
    date: datetime = field(default_factory=datetime.now)
    recipient: User | None = None
    questionId: int | None = None
