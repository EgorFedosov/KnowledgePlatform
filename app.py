import os
import secrets
import threading
import webbrowser
from pathlib import Path

from flask import Flask, g, render_template, session

from controllers.content import ContentController
from controllers.notification import NotificationController
from controllers.profile import ProfileController
from controllers.reputation import ReputationController
from controllers.search import SearchController
from models.profile import roleName
from seed import seed
from services.content import ContentServiceImpl
from services.notification import NotificationServiceImpl
from services.profile import ProfileServiceImpl
from services.reputation import ReputationServiceImpl
from services.search import SearchServiceImpl
from storage import Database

DB_PATH = Path(__file__).with_name("knowledge.db")
PORT = 5000


class Application:
    def __init__(self, dbPath=DB_PATH):
        database = Database(str(dbPath))
        self.profileService = ProfileServiceImpl(database)
        notificationService = NotificationServiceImpl(database)
        searchService = SearchServiceImpl(database)
        reputationService = ReputationServiceImpl(database, self.profileService, notificationService)
        contentService = ContentServiceImpl(database, searchService, notificationService, reputationService)

        self.flask = Flask(__name__)
        self.flask.secret_key = secrets.token_hex(16)
        self.flask.jinja_env.globals["roleName"] = roleName
        self.flask.before_request(self.loadUser)
        self.flask.add_url_rule("/quit", "quit", self.quit, methods=["POST"])
        for controller in (ProfileController(self.profileService), SearchController(searchService),
                           ContentController(contentService), ReputationController(reputationService),
                           NotificationController(notificationService)):
            controller.bindRoutes(self.flask)

        if database.isEmpty():
            with self.flask.app_context():
                seed(self.profileService, contentService, reputationService)

    def loadUser(self):
        userId = session.get("userId")
        g.user = self.profileService.getUser(userId) if userId else None
        if g.user and g.user.isBlocked:
            session.clear()
            g.user = None

    def quit(self):
        session.clear()
        threading.Timer(0.5, os._exit, [0]).start()
        return render_template("closed.html")

    def run(self):
        threading.Timer(1, webbrowser.open, [f"http://127.0.0.1:{PORT}/login"]).start()
        self.flask.run(port=PORT)


if __name__ == "__main__":
    Application().run()
