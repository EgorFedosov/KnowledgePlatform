from dataclasses import dataclass

from models.profile import Specialist

USEFUL_POINTS = 1
BEST_ANSWER_POINTS = 10


@dataclass
class Rating:
    id: int | None
    value: int
    author: Specialist | None = None
    commentId: int | None = None
