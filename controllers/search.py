from flask import g, render_template, request

from controllers import loginRequired
from models.content import Question, Tag
from services.search import SearchService

PAGE_SIZE = 5


class SearchController:
    def __init__(self, searchService: SearchService):
        self.searchService = searchService

    def search(self, keywords: str, tags: list[Tag]) -> list[Question]:
        return self.searchService.search(keywords, tags)

    def getFeed(self, userId: int) -> list[Question]:
        return self.searchService.getFeed(userId)

    def indexQuestion(self, question: Question) -> None:
        self.searchService.indexQuestion(question)

    def bindRoutes(self, app):
        app.add_url_rule("/feed", "feed", loginRequired(self.feedWindow))
        app.add_url_rule("/search", "search", loginRequired(self.searchWindow))

    def feedWindow(self):
        questions = self.getFeed(g.user.id)
        pages = max(1, (len(questions) + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(max(1, request.args.get("page", 1, type=int)), pages)
        shown = questions[(page - 1) * PAGE_SIZE:page * PAGE_SIZE]
        return render_template("feed.html", questions=shown, page=page, pages=pages)

    def searchWindow(self):
        keywords = request.args.get("q", "")
        chosen = request.args.getlist("tag")
        allTags = sorted({t.name for q in self.getFeed(g.user.id) for t in q.tags})
        questions = self.search(keywords, [Tag(None, name) for name in chosen])
        return render_template("search.html", questions=questions, keywords=keywords, tags=chosen, allTags=allTags)
