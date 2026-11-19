import unittest

from flask import Flask, g

from models.content import Comment, Question, Tag
from models.profile import Administrator, Specialist
from services import ServiceError
from services.content import ContentServiceImpl
from services.notification import NotificationServiceImpl
from services.profile import ProfileServiceImpl
from services.reputation import ReputationServiceImpl
from services.search import SearchServiceImpl
from storage import Database


class ServicesTest(unittest.TestCase):
    def setUp(self):
        self.context = Flask(__name__).app_context()
        self.context.push()
        self.database = Database(":memory:")
        self.profile = ProfileServiceImpl(self.database)
        self.notification = NotificationServiceImpl(self.database)
        self.search = SearchServiceImpl(self.database)
        self.reputation = ReputationServiceImpl(self.database, self.profile, self.notification)
        self.content = ContentServiceImpl(self.database, self.search, self.notification, self.reputation)
        self.admin = self.profile.register(Administrator(None, "admin", "12345"))
        self.author, self.other, expert = (self.profile.register(Specialist(None, n, "12345"))
                                           for n in ("author", "other", "expert"))
        g.user = self.admin
        self.expert = self.profile.grantExpert(expert.id)
        self.question = self.content.createQuestion(Question(None, "Кеш в Spring", "Как?", author=self.author),
                                                    [Tag(None, "java"), Tag(None, "spring")])
        self.answer = self.content.createComment(Comment(None, "@Cacheable", author=self.other,
                                                         questionId=self.question.id))

    def tearDown(self):
        self.context.pop()

    def test_best_answer_only_by_question_author(self):
        g.user = self.other
        with self.assertRaisesRegex(ServiceError, "только автор"):
            self.content.markBestAnswer(self.answer.id)

    def test_second_best_answer_is_forbidden(self):
        second = self.content.createComment(Comment(None, "Caffeine", author=self.expert, questionId=self.question.id))
        g.user = self.author
        self.content.markBestAnswer(self.answer.id)
        with self.assertRaisesRegex(ServiceError, "уже выбран"):
            self.content.markBestAnswer(second.id)

    def test_comment_in_closed_question_is_forbidden(self):
        g.user = self.expert
        self.content.closeQuestion(self.question.id)
        with self.assertRaisesRegex(ServiceError, "закрыта"):
            self.content.createComment(Comment(None, "Поздно", author=self.other, questionId=self.question.id))

    def test_blocked_user_cannot_login(self):
        self.profile.blockUser(self.other.id)
        with self.assertRaisesRegex(ServiceError, "заблокирован"):
            self.profile.login("other", "12345")

    def test_question_deleted_with_comments_and_ratings_tags_remain(self):
        g.user = self.author
        self.content.markBestAnswer(self.answer.id)
        self.database.deleteQuestion(self.question.id)
        self.assertIsNone(self.database.findComment(self.answer.id))
        self.assertEqual(self.database.countRatings(), 0)
        self.assertEqual([t.name for t in self.database.findTags()], ["java", "spring"])

    def test_best_answer_gives_points_and_notification(self):
        g.user = self.author
        self.content.markBestAnswer(self.answer.id)
        self.assertEqual(self.profile.getUser(self.other.id).rating, 10)
        self.assertIn("лучшим", self.notification.getNotifications(self.other.id)[0].text)

    def test_search_by_keywords_and_tags(self):
        self.assertEqual(len(self.search.search("кеш", [Tag(None, "spring")])), 1)
        self.assertEqual(self.search.search("кеш", [Tag(None, "sql")]), [])


if __name__ == "__main__":
    unittest.main()
