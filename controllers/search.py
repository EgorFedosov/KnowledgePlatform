from flask import g, render_template, request

from controllers import login_required
from models.content import Question
from services.search import SearchService

PAGE_SIZE = 5


class SearchController:
    def __init__(self, search_service: SearchService):
        self.search_service = search_service

    def search(self, keywords: str, tags: list[str]) -> list[Question]:
        return self.search_service.search(keywords, tags)

    def get_feed(self, user_id: int) -> list[Question]:
        return self.search_service.get_feed(user_id)

    def index_question(self, question: Question) -> None:
        self.search_service.index_question(question)

    def bind(self, app):
        app.add_url_rule("/feed", "feed", login_required(self.feed_window))
        app.add_url_rule("/search", "search", login_required(self.search_window))

    def feed_window(self):
        questions = self.get_feed(g.user.id)
        pages = max(1, (len(questions) + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(max(1, request.args.get("page", 1, type=int)), pages)
        shown = questions[(page - 1) * PAGE_SIZE:page * PAGE_SIZE]
        return render_template("feed.html", questions=shown, page=page, pages=pages)

    def search_window(self):
        keywords = request.args.get("q", "")
        tags = request.args.getlist("tag")
        return render_template("search.html", questions=self.search(keywords, tags), keywords=keywords,
                               tags=tags, all_tags=self.search_service.get_tags())
