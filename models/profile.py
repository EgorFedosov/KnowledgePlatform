from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    SPECIALIST = "Специалист"
    EXPERT = "Эксперт"
    ADMIN = "Администратор"


@dataclass
class User(ABC):
    id: int | None
    name: str
    password: str
    rating: int = 0
    reputation_status: str = "Новичок"
    is_blocked: bool = False

    @property
    @abstractmethod
    def role(self) -> Role: ...


class Specialist(User):
    role = Role.SPECIALIST


class Expert(Specialist):
    role = Role.EXPERT


class Administrator(User):
    role = Role.ADMIN


USER_CLASSES = {Role.SPECIALIST: Specialist, Role.EXPERT: Expert, Role.ADMIN: Administrator}


def create_user(role, **fields) -> User:
    return USER_CLASSES[Role(role)](**fields)
