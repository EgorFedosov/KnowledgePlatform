from abc import ABC, abstractmethod

from werkzeug.security import generate_password_hash

from models.profile import Administrator, Expert, Specialist, User
from models.reputation import Rating
from services import currentUser, require, requireRole
from storage import Database

ADMIN_ONLY = "Действие доступно только администратору"


class ProfileService(ABC):
    @abstractmethod
    def register(self, user: User) -> User: ...

    @abstractmethod
    def login(self, name: str, password: str) -> User: ...

    @abstractmethod
    def updateProfile(self, user: User) -> User: ...

    @abstractmethod
    def updateRating(self, userId: int, rating: Rating) -> User: ...

    @abstractmethod
    def blockUser(self, id: int) -> User: ...

    @abstractmethod
    def unblockUser(self, id: int) -> User: ...

    @abstractmethod
    def grantExpert(self, id: int) -> User: ...

    @abstractmethod
    def revokeExpert(self, id: int) -> User: ...

    @abstractmethod
    def getUser(self, id: int) -> User | None: ...

    @abstractmethod
    def getUsers(self, name: str) -> list[User]: ...


class ProfileServiceImpl(ProfileService):
    def __init__(self, database: Database):
        self.database = database

    def register(self, user: User) -> User:
        user.name = user.name.strip()
        self._checkName(user)
        self._checkPassword(user.password)
        user.password = generate_password_hash(user.password)
        return self.database.save(user)

    def login(self, name: str, password: str) -> User:
        user = self.database.findByCredentials(name.strip(), password)
        require(user is not None, "Неверное имя или пароль")
        require(not user.isBlocked, "Аккаунт заблокирован")
        return user

    def updateProfile(self, user: User) -> User:
        require(currentUser() is not None and currentUser().id == user.id, "Можно изменять только свой профиль")
        stored = self.database.findUser(user.id)
        user.name = user.name.strip()
        self._checkName(user)
        if user.password:
            self._checkPassword(user.password)
            user.password = generate_password_hash(user.password)
        else:
            user.password = stored.password
        return self.database.updateUser(user)

    def updateRating(self, userId: int, rating: Rating) -> User:
        return self.database.updateUserRating(userId, rating)

    def blockUser(self, id: int) -> User:
        user = self._target(id)
        require(not user.isBlocked, "Аккаунт уже заблокирован")
        user.isBlocked = True
        return self.database.updateUser(user)

    def unblockUser(self, id: int) -> User:
        user = self._target(id)
        require(user.isBlocked, "Аккаунт не заблокирован")
        user.isBlocked = False
        return self.database.updateUser(user)

    def grantExpert(self, id: int) -> User:
        user = self._target(id)
        require(not isinstance(user, Expert), "Пользователь уже эксперт")
        return self.database.updateUser(Expert(**vars(user)))

    def revokeExpert(self, id: int) -> User:
        user = self._target(id)
        require(isinstance(user, Expert), "Пользователь не является экспертом")
        return self.database.updateUser(Specialist(**vars(user)))

    def getUser(self, id: int) -> User | None:
        return self.database.findUser(id)

    def getUsers(self, name: str) -> list[User]:
        requireRole(Administrator, ADMIN_ONLY)
        return self.database.findUsers(name.strip())

    def _target(self, id: int) -> User:
        requireRole(Administrator, ADMIN_ONLY)
        user = self.database.findUser(id)
        require(user is not None, "Пользователь не найден")
        require(isinstance(user, Specialist), "Действие недоступно для администратора")
        return user

    def _checkName(self, user: User):
        require(bool(user.name), "Имя не может быть пустым")
        owner = self.database.findUserByName(user.name)
        require(owner is None or owner.id == user.id, "Имя пользователя уже занято")

    @staticmethod
    def _checkPassword(password: str):
        require(len(password) >= 4, "Пароль должен содержать не менее 4 символов")
