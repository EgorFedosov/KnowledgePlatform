from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class NotificationType(StrEnum):
    NEW_QUESTION = "Новый вопрос"
    NEW_ANSWER = "Новый ответ"
    POINTS = "Баллы"


@dataclass
class Notification:
    id: int | None
    type: NotificationType
    text: str
    recipient_id: int
    question_id: int | None
    date: datetime = field(default_factory=datetime.now)
