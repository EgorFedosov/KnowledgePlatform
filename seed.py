from models.content import Comment, Question, ReviewStatus
from models.profile import Administrator, Specialist
from models.reputation import USEFUL_POINTS, Rating

PASSWORD = "12345"


def seed(profile, content, reputation):
    admin = profile.register(Administrator(None, "admin", PASSWORD))
    ivanov, petrova, sidorov, kozlov = (profile.register(Specialist(None, name, PASSWORD))
                                        for name in ("ivanov", "petrova", "sidorov", "kozlov"))
    petrova = profile.grant_expert(petrova.id, admin)

    build = content.create_question(Question(
        None, "Как ускорить сборку проекта?", "Сборка на Gradle занимает больше пяти минут. Что можно ускорить?",
        sidorov), ["gradle"])
    jpa = content.create_question(Question(
        None, "Кеширование запросов в JPA", "Как включить кеш второго уровня в Hibernate?", kozlov),
        ["java", "spring"])
    join = content.create_question(Question(
        None, "Чем отличается JOIN от UNION?", "Когда что использовать в запросах?", petrova), ["sql"])
    content.subscribe(ivanov.id, jpa.id)
    spring = content.create_question(Question(
        None, "Как настроить кеш в Spring?", "Нужно кешировать результаты запросов к базе данных. "
        "Какой способ выбрать?", ivanov), ["java", "spring"])

    best = content.create_comment(Comment(None, "Используйте @Cacheable и настройте CacheManager.", spring.id, petrova))
    content.create_comment(Comment(None, "Можно подключить библиотеку Caffeine.", spring.id, sidorov))
    content.create_comment(Comment(None, "JOIN объединяет строки таблиц, UNION — результаты запросов.", join.id, kozlov))
    content.create_comment(Comment(None, "Включите hibernate.cache.use_second_level_cache.", jpa.id, petrova))
    content.create_comment(Comment(None, "Попробуйте включить org.gradle.caching=true.", build.id, kozlov))

    for user in (sidorov, kozlov):
        reputation.rate_comment(Rating(None, USEFUL_POINTS, best.id, user.id))
    content.mark_best_answer(best.id, ivanov)
    content.review_comment(best.id, ReviewStatus.CONFIRMED, petrova)
