import sqlite3
from datetime import datetime
from functools import singledispatchmethod

from werkzeug.security import check_password_hash

from models.content import Comment, Question, Tag
from models.notification import Notification
from models.profile import User, roleName, userOfRole
from models.reputation import Rating

SCHEMA_VERSION = 2

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL,
    rating INTEGER NOT NULL, reputationStatus TEXT NOT NULL, isBlocked INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL, createdAt TEXT NOT NULL,
    status TEXT NOT NULL, authorId INTEGER NOT NULL REFERENCES users(id));
CREATE TABLE IF NOT EXISTS tags (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS questionTags (
    questionId INTEGER REFERENCES questions(id) ON DELETE CASCADE,
    tagId INTEGER REFERENCES tags(id), PRIMARY KEY (questionId, tagId));
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY, text TEXT NOT NULL, createdAt TEXT NOT NULL, isBestAnswer INTEGER NOT NULL,
    reviewStatus TEXT NOT NULL, remark TEXT NOT NULL DEFAULT '',
    questionId INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    authorId INTEGER NOT NULL REFERENCES users(id), reviewerId INTEGER REFERENCES users(id));
CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY, value INTEGER NOT NULL,
    commentId INTEGER NOT NULL REFERENCES comments(id) ON DELETE CASCADE,
    authorId INTEGER NOT NULL REFERENCES users(id));
CREATE TABLE IF NOT EXISTS subscriptions (
    userId INTEGER REFERENCES users(id),
    questionId INTEGER REFERENCES questions(id) ON DELETE CASCADE, PRIMARY KEY (userId, questionId));
CREATE TABLE IF NOT EXISTS searchIndex (
    questionId INTEGER PRIMARY KEY REFERENCES questions(id) ON DELETE CASCADE, content TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY, type TEXT NOT NULL, text TEXT NOT NULL, date TEXT NOT NULL,
    recipientId INTEGER NOT NULL REFERENCES users(id),
    questionId INTEGER REFERENCES questions(id) ON DELETE SET NULL);
"""


class Database:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        if self._one("PRAGMA user_version")[0] != SCHEMA_VERSION:
            self._dropTables()
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self.conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    def _dropTables(self):
        tables = self._all("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
        for table in tables:
            self.conn.execute(f"DROP TABLE {table['name']}")
        self.conn.commit()

    def _all(self, sql, *args):
        return self.conn.execute(sql, args).fetchall()

    def _one(self, sql, *args):
        return self.conn.execute(sql, args).fetchone()

    def _run(self, sql, *args) -> int:
        with self.conn:
            return self.conn.execute(sql, args).lastrowid

    def isEmpty(self) -> bool:
        return self._one("SELECT COUNT(*) FROM users")[0] == 0

    @singledispatchmethod
    def save(self, entity):
        raise TypeError(f"Нельзя сохранить {type(entity).__name__}")

    @save.register
    def _(self, user: User) -> User:
        user.id = self._run(
            "INSERT INTO users (name, password, role, rating, reputationStatus, isBlocked) VALUES (?, ?, ?, ?, ?, ?)",
            user.name, user.password, roleName(user), user.rating, user.reputationStatus, user.isBlocked)
        return user

    @save.register
    def _(self, question: Question) -> Question:
        question.id = self._run(
            "INSERT INTO questions (title, description, createdAt, status, authorId) VALUES (?, ?, ?, ?, ?)",
            question.title, question.description, question.createdAt.isoformat(), question.status,
            question.author.id)
        return self.updateTags(question.id, question.tags)

    @save.register
    def _(self, comment: Comment) -> Comment:
        comment.id = self._run(
            "INSERT INTO comments (text, createdAt, isBestAnswer, reviewStatus, questionId, authorId) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            comment.text, comment.createdAt.isoformat(), comment.isBestAnswer, comment.reviewStatus,
            comment.questionId, comment.author.id)
        return comment

    @save.register
    def _(self, notification: Notification) -> Notification:
        notification.id = self._run(
            "INSERT INTO notifications (type, text, date, recipientId, questionId) VALUES (?, ?, ?, ?, ?)",
            notification.type, notification.text, notification.date.isoformat(), notification.recipient.id,
            notification.questionId)
        return notification

    def _user(self, row) -> User | None:
        if row is None:
            return None
        return userOfRole(row["role"], id=row["id"], name=row["name"], password=row["password"],
                          rating=row["rating"], reputationStatus=row["reputationStatus"],
                          isBlocked=bool(row["isBlocked"]))

    def findByCredentials(self, name: str, password: str) -> User | None:
        user = self.findUserByName(name)
        return user if user and check_password_hash(user.password, password) else None

    def findUser(self, id: int) -> User | None:
        return self._user(self._one("SELECT * FROM users WHERE id = ?", id))

    def findUserByName(self, name: str) -> User | None:
        return self._user(self._one("SELECT * FROM users WHERE name = ?", name))

    def findUsers(self, name: str) -> list[User]:
        return [self._user(r) for r in self._all("SELECT * FROM users WHERE name LIKE ? ORDER BY id", f"%{name}%")]

    def updateUser(self, user: User) -> User:
        self._run("UPDATE users SET name = ?, password = ?, role = ?, reputationStatus = ?, isBlocked = ? WHERE id = ?",
                  user.name, user.password, roleName(user), user.reputationStatus, user.isBlocked, user.id)
        return self.findUser(user.id)

    def updateUserRating(self, userId: int, rating: Rating) -> User:
        self._run("UPDATE users SET rating = rating + ? WHERE id = ?", rating.value, userId)
        return self.findUser(userId)

    def _tags(self, questionId: int) -> list[Tag]:
        rows = self._all("SELECT t.* FROM tags t JOIN questionTags qt ON qt.tagId = t.id "
                         "WHERE qt.questionId = ? ORDER BY t.name", questionId)
        return [Tag(r["id"], r["name"]) for r in rows]

    def _question(self, row) -> Question | None:
        if row is None:
            return None
        return Question(row["id"], row["title"], row["description"], datetime.fromisoformat(row["createdAt"]),
                        self.findUser(row["authorId"]), self._tags(row["id"]), self.findComments(row["id"]),
                        self.findSubscribers(row["id"]), row["status"])

    def findQuestion(self, id: int) -> Question | None:
        return self._question(self._one("SELECT * FROM questions WHERE id = ?", id))

    def findQuestions(self) -> list[Question]:
        return [self._question(r) for r in self._all("SELECT * FROM questions ORDER BY createdAt DESC, id DESC")]

    def updateTags(self, questionId: int, tags: list[Tag]) -> Question:
        self._run("DELETE FROM questionTags WHERE questionId = ?", questionId)
        for tag in tags:
            self._run("INSERT OR IGNORE INTO tags (name) VALUES (?)", tag.name)
            tagId = self._one("SELECT id FROM tags WHERE name = ?", tag.name)["id"]
            self._run("INSERT OR IGNORE INTO questionTags VALUES (?, ?)", questionId, tagId)
        return self.findQuestion(questionId)

    def updateQuestionStatus(self, questionId: int, status: str) -> Question:
        self._run("UPDATE questions SET status = ? WHERE id = ?", status, questionId)
        return self.findQuestion(questionId)

    def deleteQuestion(self, questionId: int):
        self._run("DELETE FROM questions WHERE id = ?", questionId)

    def findTags(self) -> list[Tag]:
        return [Tag(r["id"], r["name"]) for r in self._all("SELECT * FROM tags ORDER BY name")]

    def findUserTagNames(self, userId: int) -> set[str]:
        rows = self._all("SELECT DISTINCT t.name FROM tags t JOIN questionTags qt ON qt.tagId = t.id "
                         "WHERE qt.questionId IN (SELECT id FROM questions WHERE authorId = ? "
                         "UNION SELECT questionId FROM subscriptions WHERE userId = ?)", userId, userId)
        return {r["name"] for r in rows}

    def saveIndex(self, question: Question) -> str:
        index = " ".join([question.title, question.description] + [t.name for t in question.tags]).lower()
        self._run("INSERT OR REPLACE INTO searchIndex VALUES (?, ?)", question.id, index)
        return index

    def findByKeywordsAndTags(self, keywords: str, tags: list[Tag]) -> list[Question]:
        sql = "SELECT q.* FROM questions q JOIN searchIndex i ON i.questionId = q.id WHERE 1 = 1"
        args = []
        for word in keywords.lower().split():
            sql += " AND i.content LIKE ?"
            args.append(f"%{word}%")
        for tag in tags:
            sql += (" AND q.id IN (SELECT qt.questionId FROM questionTags qt "
                    "JOIN tags t ON t.id = qt.tagId WHERE t.name = ?)")
            args.append(tag.name)
        return [self._question(r) for r in self._all(sql + " ORDER BY q.createdAt DESC, q.id DESC", *args)]

    def _comment(self, row) -> Comment | None:
        if row is None:
            return None
        reviewer = self.findUser(row["reviewerId"]) if row["reviewerId"] else None
        return Comment(row["id"], row["text"], datetime.fromisoformat(row["createdAt"]), bool(row["isBestAnswer"]),
                       row["reviewStatus"], self.findUser(row["authorId"]), reviewer,
                       self.findRatings(row["id"]), row["questionId"], row["remark"])

    def findComment(self, id: int) -> Comment | None:
        return self._comment(self._one("SELECT * FROM comments WHERE id = ?", id))

    def findComments(self, questionId: int) -> list[Comment]:
        rows = self._all("SELECT * FROM comments WHERE questionId = ? ORDER BY id", questionId)
        return [self._comment(r) for r in rows]

    def updateBestAnswer(self, commentId: int) -> Comment:
        self._run("UPDATE comments SET isBestAnswer = 1 WHERE id = ?", commentId)
        return self.findComment(commentId)

    def updateReview(self, comment: Comment) -> Comment:
        self._run("UPDATE comments SET reviewStatus = ?, reviewerId = ?, remark = ? WHERE id = ?",
                  comment.reviewStatus, comment.reviewer.id, comment.remark, comment.id)
        return self.findComment(comment.id)

    def saveRating(self, rating: Rating) -> Rating:
        rating.id = self._run("INSERT INTO ratings (value, commentId, authorId) VALUES (?, ?, ?)",
                              rating.value, rating.commentId, rating.author.id)
        return rating

    def findRatings(self, commentId: int) -> list[Rating]:
        rows = self._all("SELECT * FROM ratings WHERE commentId = ?", commentId)
        return [Rating(r["id"], r["value"], self.findUser(r["authorId"]), r["commentId"]) for r in rows]

    def countRatings(self) -> int:
        return self._one("SELECT COUNT(*) FROM ratings")[0]

    def saveSubscription(self, userId: int, questionId: int):
        self._run("INSERT OR IGNORE INTO subscriptions VALUES (?, ?)", userId, questionId)

    def findSubscribers(self, questionId: int) -> list[User]:
        rows = self._all("SELECT userId FROM subscriptions WHERE questionId = ?", questionId)
        return [self.findUser(r["userId"]) for r in rows]

    def findTopicSubscribers(self, question: Question) -> list[tuple[User, str]]:
        tagIds = [t.id for t in question.tags]
        marks = ",".join("?" * len(tagIds))
        rows = self._all(f"SELECT s.userId, MIN(t.name) AS tag FROM subscriptions s "
                         f"JOIN questionTags qt ON qt.questionId = s.questionId JOIN tags t ON t.id = qt.tagId "
                         f"WHERE t.id IN ({marks}) AND s.userId != ? GROUP BY s.userId",
                         *tagIds, question.author.id)
        return [(self.findUser(r["userId"]), r["tag"]) for r in rows]

    def findNotifications(self, userId: int) -> list[Notification]:
        rows = self._all("SELECT * FROM notifications WHERE recipientId = ? ORDER BY date DESC, id DESC", userId)
        recipient = self.findUser(userId)
        return [Notification(r["id"], r["type"], r["text"], datetime.fromisoformat(r["date"]), recipient,
                             r["questionId"]) for r in rows]
