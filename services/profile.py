from abc import ABC, abstractmethod

from werkzeug.security import check_password_hash, generate_password_hash

from models.profile import Administrator, Expert, Role, Specialist, User
from models.reputation import Rating
from services import ServiceError, require
from storage import Database


class ProfileService(ABC):
    @abstractmethod
    def register(self, user: User) -> User: ...

    @abstractmethod
    def login(self, name: str, password: str) -> User: ...

    @abstractmethod
    def update_profile(self, user: User, password: str = "") -> User: ...

    @abstractmethod
    def update_rating(self, user_id: int, rating: Rating) -> User: ...

    @abstractmethod
    def block_user(self, id: int, actor: User) -> User: ...

    @abstractmethod
    def unblock_user(self, id: int, actor: User) -> User: ...

    @abstractmethod
    def grant_expert(self, id: int, actor: User) -> User: ...

    @abstractmethod
    def revoke_expert(self, id: int, actor: User) -> User: ...

    @abstractmethod
    def get_user(self, id: int) -> User | None: ...

    @abstractmethod
    def find_users(self, name: str, actor: User) -> list[User]: ...


class ProfileServiceImpl(ProfileService):
    def __init__(self, db: Database):
        self.db = db

    def register(self, user: User) -> User:
        self._check_credentials(user.name, user.password)
        require(self.db.find_by_credentials(user.name) is None, "Имя пользователя уже занято")
        user.password = generate_password_hash(user.password)
        return self.db.save_user(user)

    def login(self, name: str, password: str) -> User:
        user = self.db.find_by_credentials(name.strip())
        require(user is not None and check_password_hash(user.password, password), "Неверное имя или пароль")
        require(not user.is_blocked, "Аккаунт заблокирован")
        return user

    def update_profile(self, user: User, password: str = "") -> User:
        user.name = user.name.strip()
        require(bool(user.name), "Имя не может быть пустым")
        owner = self.db.find_by_credentials(user.name)
        require(owner is None or owner.id == user.id, "Имя пользователя уже занято")
        if password:
            self._check_credentials(user.name, password)
            user.password = generate_password_hash(password)
        return self.db.update_user(user)

    def update_rating(self, user_id: int, rating: Rating) -> User:
        return self.db.update_user_rating(user_id, rating.value)

    def block_user(self, id: int, actor: User) -> User:
        return self._set_blocked(id, actor, True)

    def unblock_user(self, id: int, actor: User) -> User:
        return self._set_blocked(id, actor, False)

    def grant_expert(self, id: int, actor: User) -> User:
        user = self._target(id, actor)
        require(user.role == Role.SPECIALIST, "Доступ эксперта можно выдать только специалисту")
        return self.db.update_user_role(id, Role.EXPERT)

    def revoke_expert(self, id: int, actor: User) -> User:
        user = self._target(id, actor)
        require(isinstance(user, Expert), "Пользователь не является экспертом")
        return self.db.update_user_role(id, Role.SPECIALIST)

    def get_user(self, id: int) -> User | None:
        return self.db.find_user(id)

    def find_users(self, name: str, actor: User) -> list[User]:
        self._require_admin(actor)
        return self.db.find_users(name.strip())

    def _set_blocked(self, id: int, actor: User, blocked: bool) -> User:
        user = self._target(id, actor)
        require(user.is_blocked != blocked, "Аккаунт уже заблокирован" if blocked else "Аккаунт не заблокирован")
        user.is_blocked = blocked
        return self.db.update_user(user)

    def _target(self, id: int, actor: User) -> User:
        self._require_admin(actor)
        user = self.db.find_user(id)
        require(user is not None, "Пользователь не найден")
        require(isinstance(user, Specialist), "Действие недоступно для администратора")
        return user

    @staticmethod
    def _require_admin(actor: User):
        if not isinstance(actor, Administrator):
            raise ServiceError("Действие доступно только администратору")

    @staticmethod
    def _check_credentials(name: str, password: str):
        require(bool(name.strip()), "Имя не может быть пустым")
        require(len(password) >= 4, "Пароль должен содержать не менее 4 символов")
