from dataclasses import dataclass

USEFUL_POINTS = 1
BEST_ANSWER_POINTS = 10


@dataclass
class Rating:
    id: int | None
    value: int
    comment_id: int
    author_id: int
