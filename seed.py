from flask import g

from models.content import Comment, Question, ReviewStatus, Tag
from models.profile import Administrator, Specialist
from models.reputation import USEFUL_POINTS, Rating

PASSWORD = "12345"


def tags(*names):
    return [Tag(None, name) for name in names]


def seed(profileService, contentService, reputationService):
    admin = profileService.register(Administrator(None, "admin", PASSWORD))
    ivanov, petrova, sidorov, kozlov = (profileService.register(Specialist(None, name, PASSWORD))
                                        for name in ("ivanov", "petrova", "sidorov", "kozlov"))
    g.user = admin
    petrova = profileService.grantExpert(petrova.id)

    build = contentService.createQuestion(Question(
        None, "Как ускорить сборку проекта?", "Сборка на Gradle занимает больше пяти минут. Что можно ускорить?",
        author=sidorov), tags("gradle"))
    jpa = contentService.createQuestion(Question(
        None, "Кеширование запросов в JPA", "Как включить кеш второго уровня в Hibernate?", author=kozlov),
        tags("java", "spring"))
    join = contentService.createQuestion(Question(
        None, "Чем отличается JOIN от UNION?", "Когда что использовать в запросах?", author=petrova), tags("sql"))
    contentService.subscribe(ivanov.id, jpa.id)
    spring = contentService.createQuestion(Question(
        None, "Как настроить кеш в Spring?",
        "Нужно кешировать результаты запросов к базе данных. Какой способ выбрать?", author=ivanov),
        tags("java", "spring"))

    def answer(text, question, author):
        return contentService.createComment(Comment(None, text, author=author, questionId=question.id))

    best = answer("Используйте @Cacheable и настройте CacheManager.", spring, petrova)
    answer("Можно подключить библиотеку Caffeine.", spring, sidorov)
    answer("JOIN объединяет строки таблиц, UNION — результаты запросов.", join, kozlov)
    answer("Включите hibernate.cache.use_second_level_cache.", jpa, petrova)
    answer("Попробуйте включить org.gradle.caching=true.", build, kozlov)

    for user in (sidorov, kozlov):
        reputationService.rateComment(Rating(None, USEFUL_POINTS, user, best.id))
    g.user = ivanov
    contentService.markBestAnswer(best.id)
    g.user = petrova
    contentService.reviewComment(best.id, ReviewStatus.CONFIRMED)
    g.user = None
