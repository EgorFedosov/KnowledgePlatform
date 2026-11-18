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
    def __init__(self, db_path=DB_PATH):
        db = Database(str(db_path))
        self.profile_service = ProfileServiceImpl(db)
        notification_service = NotificationServiceImpl(db)
        search_service = SearchServiceImpl(db)
        reputation_service = ReputationServiceImpl(db, self.profile_service, notification_service)
        content_service = ContentServiceImpl(db, search_service, notification_service, reputation_service)
        if db.is_empty():
            seed(self.profile_service, content_service, reputation_service)

        self.flask = Flask(__name__)
        self.flask.secret_key = secrets.token_hex(16)
        self.flask.before_request(self.load_user)
        self.flask.add_url_rule("/quit", "quit", self.quit, methods=["POST"])
        for controller in (ProfileController(self.profile_service), SearchController(search_service),
                           ContentController(content_service), ReputationController(reputation_service),
                           NotificationController(notification_service)):
            controller.bind(self.flask)

    def load_user(self):
        user_id = session.get("user_id")
        g.user = self.profile_service.get_user(user_id) if user_id else None
        if g.user and g.user.is_blocked:
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
