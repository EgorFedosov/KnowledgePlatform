import sqlite3
from datetime import datetime

from models.content import Comment, Question, QuestionStatus, ReviewStatus, Tag
from models.notification import Notification, NotificationType
from models.profile import Role, User, create_user
from models.reputation import Rating

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL,
    rating INTEGER NOT NULL DEFAULT 0, reputation_status TEXT NOT NULL, is_blocked INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL, created_at TEXT NOT NULL,
    status TEXT NOT NULL, author_id INTEGER NOT NULL REFERENCES users(id));
CREATE TABLE IF NOT EXISTS tags (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS question_tags (
    question_id INTEGER REFERENCES questions(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id), PRIMARY KEY (question_id, tag_id));
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY, text TEXT NOT NULL, created_at TEXT NOT NULL, is_best_answer INTEGER NOT NULL,
    review_status TEXT NOT NULL, review_note TEXT NOT NULL DEFAULT '',
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    author_id INTEGER NOT NULL REFERENCES users(id));
CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY, value INTEGER NOT NULL,
    comment_id INTEGER NOT NULL REFERENCES comments(id) ON DELETE CASCADE,
    author_id INTEGER NOT NULL REFERENCES users(id));
CREATE TABLE IF NOT EXISTS subscriptions (
    user_id INTEGER REFERENCES users(id),
    question_id INTEGER REFERENCES questions(id) ON DELETE CASCADE, PRIMARY KEY (user_id, question_id));
CREATE TABLE IF NOT EXISTS search_index (
    question_id INTEGER PRIMARY KEY REFERENCES questions(id) ON DELETE CASCADE, content TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY, type TEXT NOT NULL, text TEXT NOT NULL, date TEXT NOT NULL,
    recipient_id INTEGER NOT NULL REFERENCES users(id),
    question_id INTEGER REFERENCES questions(id) ON DELETE SET NULL);
"""


class Database:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)

    def _all(self, sql, *args):
        return self.conn.execute(sql, args).fetchall()

    def _one(self, sql, *args):
        return self.conn.execute(sql, args).fetchone()

    def _run(self, sql, *args) -> int:
        with self.conn:
            return self.conn.execute(sql, args).lastrowid

    def is_empty(self) -> bool:
        return self._one("SELECT COUNT(*) FROM users")[0] == 0


    def _user(self, row) -> User | None:
        if row is None:
            return None
        return create_user(row["role"], id=row["id"], name=row["name"], password=row["password"],
                           rating=row["rating"], reputation_status=row["reputation_status"],
                           is_blocked=bool(row["is_blocked"]))

    def find_by_credentials(self, name: str) -> User | None:
        return self._user(self._one("SELECT * FROM users WHERE name = ?", name))

    def find_user(self, user_id: int) -> User | None:
        return self._user(self._one("SELECT * FROM users WHERE id = ?", user_id))

    def find_users(self, name: str) -> list[User]:
        return [self._user(r) for r in self._all("SELECT * FROM users WHERE name LIKE ? ORDER BY id", f"%{name}%")]

    def save_user(self, user: User) -> User:
        user.id = self._run(
            "INSERT INTO users (name, password, role, rating, reputation_status, is_blocked) VALUES (?, ?, ?, ?, ?, ?)",
            user.name, user.password, user.role, user.rating, user.reputation_status, user.is_blocked)
        return user

    def update_user(self, user: User) -> User:
        self._run("UPDATE users SET name = ?, password = ?, rating = ?, reputation_status = ?, is_blocked = ? WHERE id = ?",
                  user.name, user.password, user.rating, user.reputation_status, user.is_blocked, user.id)
        return user

    def update_user_role(self, user_id: int, role: Role) -> User:
        self._run("UPDATE users SET role = ? WHERE id = ?", role, user_id)
        return self.find_user(user_id)

    def update_user_rating(self, user_id: int, points: int) -> User:
        self._run("UPDATE users SET rating = rating + ? WHERE id = ?", points, user_id)
        return self.find_user(user_id)

    def update_user_status(self, user_id: int, status: str):
        self._run("UPDATE users SET reputation_status = ? WHERE id = ?", status, user_id)


    def _tags(self, question_id: int) -> list[Tag]:
        rows = self._all("SELECT t.* FROM tags t JOIN question_tags qt ON qt.tag_id = t.id "
                         "WHERE qt.question_id = ? ORDER BY t.name", question_id)
        return [Tag(r["id"], r["name"]) for r in rows]

    def _question(self, row) -> Question | None:
        if row is None:
            return None
        return Question(row["id"], row["title"], row["description"], self.find_user(row["author_id"]),
                        datetime.fromisoformat(row["created_at"]), QuestionStatus(row["status"]),
                        self._tags(row["id"]), self.find_comments(row["id"]))

    def find_question(self, question_id: int) -> Question | None:
        return self._question(self._one("SELECT * FROM questions WHERE id = ?", question_id))

    def find_questions(self) -> list[Question]:
        return [self._question(r) for r in self._all("SELECT * FROM questions ORDER BY created_at DESC, id DESC")]

    def find_questions_by_status(self, *statuses: QuestionStatus) -> list[Question]:
        return [q for q in self.find_questions() if q.status in statuses]

    def save_question(self, question: Question, tags: list[str]) -> Question:
        question.id = self._run(
            "INSERT INTO questions (title, description, created_at, status, author_id) VALUES (?, ?, ?, ?, ?)",
            question.title, question.description, question.created_at.isoformat(), question.status,
            question.author.id)
        return self.update_tags(question.id, tags)

    def update_tags(self, question_id: int, tags: list[str]) -> Question:
        self._run("DELETE FROM question_tags WHERE question_id = ?", question_id)
        for name in tags:
            self._run("INSERT OR IGNORE INTO tags (name) VALUES (?)", name)
            tag_id = self._one("SELECT id FROM tags WHERE name = ?", name)["id"]
            self._run("INSERT OR IGNORE INTO question_tags VALUES (?, ?)", question_id, tag_id)
        return self.find_question(question_id)

    def update_question_status(self, question_id: int, status: QuestionStatus):
        self._run("UPDATE questions SET status = ? WHERE id = ?", status, question_id)

    def delete_question(self, question_id: int):
        self._run("DELETE FROM questions WHERE id = ?", question_id)

    def find_tags(self) -> list[Tag]:
        return [Tag(r["id"], r["name"]) for r in self._all("SELECT * FROM tags ORDER BY name")]

    def find_user_tag_names(self, user_id: int) -> set[str]:
        rows = self._all("SELECT DISTINCT t.name FROM tags t JOIN question_tags qt ON qt.tag_id = t.id "
                         "WHERE qt.question_id IN (SELECT id FROM questions WHERE author_id = ? "
                         "UNION SELECT question_id FROM subscriptions WHERE user_id = ?)", user_id, user_id)
        return {r["name"] for r in rows}


    def save_index(self, question_id: int, content: str):
        self._run("INSERT OR REPLACE INTO search_index VALUES (?, ?)", question_id, content)

    def find_by_keywords_and_tags(self, words: list[str], tags: list[str]) -> list[Question]:
        sql = "SELECT q.* FROM questions q JOIN search_index i ON i.question_id = q.id WHERE 1 = 1"
        args = []
        for word in words:
            sql += " AND i.content LIKE ?"
            args.append(f"%{word}%")
        for tag in tags:
            sql += (" AND q.id IN (SELECT qt.question_id FROM question_tags qt "
                    "JOIN tags t ON t.id = qt.tag_id WHERE t.name = ?)")
            args.append(tag)
        return [self._question(r) for r in self._all(sql + " ORDER BY q.created_at DESC, q.id DESC", *args)]


    def _comment(self, row) -> Comment | None:
        if row is None:
            return None
        return Comment(row["id"], row["text"], row["question_id"], self.find_user(row["author_id"]),
                       datetime.fromisoformat(row["created_at"]), bool(row["is_best_answer"]),
                       ReviewStatus(row["review_status"]), row["review_note"], self.find_ratings(row["id"]))

    def find_comment(self, comment_id: int) -> Comment | None:
        return self._comment(self._one("SELECT * FROM comments WHERE id = ?", comment_id))

    def find_comments(self, question_id: int) -> list[Comment]:
        return [self._comment(r) for r in self._all("SELECT * FROM comments WHERE question_id = ? ORDER BY id",
                                                     question_id)]

    def find_comments_by_status(self, status: ReviewStatus) -> list[Comment]:
        return [self._comment(r) for r in self._all("SELECT * FROM comments WHERE review_status = ? ORDER BY id",
                                                     status)]

    def save_comment(self, comment: Comment) -> Comment:
        comment.id = self._run(
            "INSERT INTO comments (text, created_at, is_best_answer, review_status, question_id, author_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            comment.text, comment.created_at.isoformat(), comment.is_best_answer, comment.review_status,
            comment.question_id, comment.author.id)
        return comment

    def update_best_answer(self, comment_id: int) -> Comment:
        self._run("UPDATE comments SET is_best_answer = 1 WHERE id = ?", comment_id)
        return self.find_comment(comment_id)

    def update_review(self, comment_id: int, status: ReviewStatus, note: str) -> Comment:
        self._run("UPDATE comments SET review_status = ?, review_note = ? WHERE id = ?", status, note, comment_id)
        return self.find_comment(comment_id)

    def find_ratings(self, comment_id: int) -> list[Rating]:
        rows = self._all("SELECT * FROM ratings WHERE comment_id = ?", comment_id)
        return [Rating(r["id"], r["value"], r["comment_id"], r["author_id"]) for r in rows]

    def count_ratings(self) -> int:
        return self._one("SELECT COUNT(*) FROM ratings")[0]

    def save_rating(self, rating: Rating) -> Rating:
        rating.id = self._run("INSERT INTO ratings (value, comment_id, author_id) VALUES (?, ?, ?)",
                              rating.value, rating.comment_id, rating.author_id)
        return rating


    def save_subscription(self, user_id: int, question_id: int):
        self._run("INSERT OR IGNORE INTO subscriptions VALUES (?, ?)", user_id, question_id)

    def is_subscribed(self, user_id: int, question_id: int) -> bool:
        return self._one("SELECT 1 FROM subscriptions WHERE user_id = ? AND question_id = ?",
                         user_id, question_id) is not None

    def find_topic_subscribers(self, question: Question) -> list[tuple[int, str]]:
        tag_ids = [t.id for t in question.tags]
        marks = ",".join("?" * len(tag_ids))
        rows = self._all(f"SELECT s.user_id, MIN(t.name) AS tag FROM subscriptions s "
                         f"JOIN question_tags qt ON qt.question_id = s.question_id JOIN tags t ON t.id = qt.tag_id "
                         f"WHERE t.id IN ({marks}) AND s.user_id != ? GROUP BY s.user_id",
                         *tag_ids, question.author.id)
        return [(r["user_id"], r["tag"]) for r in rows]


    def save_notification(self, n: Notification) -> Notification:
        n.id = self._run("INSERT INTO notifications (type, text, date, recipient_id, question_id) VALUES (?, ?, ?, ?, ?)",
                         n.type, n.text, n.date.isoformat(), n.recipient_id, n.question_id)
        return n

    def find_notifications(self, user_id: int) -> list[Notification]:
        rows = self._all("SELECT * FROM notifications WHERE recipient_id = ? ORDER BY date DESC, id DESC", user_id)
        return [Notification(r["id"], NotificationType(r["type"]), r["text"], r["recipient_id"], r["question_id"],
                             datetime.fromisoformat(r["date"])) for r in rows]
