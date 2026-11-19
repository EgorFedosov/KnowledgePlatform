from abc import ABC
from dataclasses import dataclass


@dataclass
class User(ABC):
    id: int | None
    name: str
    password: str
    rating: int = 0
    reputationStatus: str = "Новичок"
    isBlocked: bool = False

    def __post_init__(self):
        if type(self) is User:
            raise TypeError("User — абстрактный класс")


class Specialist(User):
    pass


class Expert(Specialist):
    pass


class Administrator(User):
    pass


ROLES = {Specialist: "Специалист", Expert: "Эксперт", Administrator: "Администратор"}


def roleName(user: User) -> str:
    return ROLES[type(user)]


def userOfRole(role: str, **fields) -> User:
    return next(cls for cls, name in ROLES.items() if name == role)(**fields)
