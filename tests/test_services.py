import unittest

from models.content import Comment, Question
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
        self.db = Database(":memory:")
        self.profile = ProfileServiceImpl(self.db)
        self.notification = NotificationServiceImpl(self.db)
        self.search = SearchServiceImpl(self.db)
        self.reputation = ReputationServiceImpl(self.db, self.profile, self.notification)
        self.content = ContentServiceImpl(self.db, self.search, self.notification, self.reputation)
        self.admin = self.profile.register(Administrator(None, "admin", "12345"))
        self.author, self.other, self.expert = (self.profile.register(Specialist(None, n, "12345"))
                                                for n in ("author", "other", "expert"))
        self.expert = self.profile.grant_expert(self.expert.id, self.admin)
        self.question = self.content.create_question(Question(None, "Кеш в Spring", "Как?", self.author),
                                                     ["java", "spring"])
        self.answer = self.content.create_comment(Comment(None, "@Cacheable", self.question.id, self.other))

    def test_best_answer_only_by_question_author(self):
        with self.assertRaisesRegex(ServiceError, "только автор"):
            self.content.mark_best_answer(self.answer.id, self.other)

    def test_second_best_answer_is_forbidden(self):
        second = self.content.create_comment(Comment(None, "Caffeine", self.question.id, self.expert))
        self.content.mark_best_answer(self.answer.id, self.author)
        with self.assertRaisesRegex(ServiceError, "уже выбран"):
            self.content.mark_best_answer(second.id, self.author)

    def test_comment_in_closed_question_is_forbidden(self):
        self.content.close_question(self.question.id, self.expert)
        with self.assertRaisesRegex(ServiceError, "закрыта"):
            self.content.create_comment(Comment(None, "Поздно", self.question.id, self.other))

    def test_blocked_user_cannot_login(self):
        self.profile.block_user(self.other.id, self.admin)
        with self.assertRaisesRegex(ServiceError, "заблокирован"):
            self.profile.login("other", "12345")

    def test_question_deleted_with_comments_and_ratings_tags_remain(self):
        self.content.mark_best_answer(self.answer.id, self.author)
        self.db.delete_question(self.question.id)
        self.assertIsNone(self.db.find_comment(self.answer.id))
        self.assertEqual(self.db.count_ratings(), 0)
        self.assertEqual([t.name for t in self.db.find_tags()], ["java", "spring"])

    def test_best_answer_gives_points_and_notification(self):
        self.content.mark_best_answer(self.answer.id, self.author)
        self.assertEqual(self.profile.get_user(self.other.id).rating, 10)
        self.assertIn("лучшим", self.notification.get_notifications(self.other.id)[0].text)

    def test_search_by_keywords_and_tags(self):
        self.assertEqual(len(self.search.search("кеш", ["spring"])), 1)
        self.assertEqual(self.search.search("кеш", ["sql"]), [])


if __name__ == "__main__":
    unittest.main()
