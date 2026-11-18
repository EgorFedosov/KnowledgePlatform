from flask import flash, g, redirect, render_template, request, session, url_for

from controllers import attempt, login_required, selected
from models.profile import Specialist, User
from models.reputation import Rating
from services import ServiceError
from services.profile import ProfileService


class ProfileController:
    def __init__(self, profile_service: ProfileService):
        self.profile_service = profile_service

    def register(self, user: User) -> User:
        return self.profile_service.register(user)

    def login(self, name: str, password: str) -> User:
        return self.profile_service.login(name, password)

    def update_profile(self, user: User, password: str = "") -> User:
        return self.profile_service.update_profile(user, password)

    def update_rating(self, user_id: int, rating: Rating) -> User:
        return self.profile_service.update_rating(user_id, rating)

    def block_user(self, id: int) -> User:
        return self.profile_service.block_user(id, g.user)

    def unblock_user(self, id: int) -> User:
        return self.profile_service.unblock_user(id, g.user)

    def grant_expert(self, id: int) -> User:
        return self.profile_service.grant_expert(id, g.user)

    def revoke_expert(self, id: int) -> User:
        return self.profile_service.revoke_expert(id, g.user)

    def bind(self, app):
        app.add_url_rule("/", "index", lambda: redirect(url_for("feed")))
        app.add_url_rule("/login", "login", self.login_window, methods=["GET", "POST"])
        app.add_url_rule("/register", "register", self.register_window, methods=["GET", "POST"])
        app.add_url_rule("/logout", "logout", self.logout)
        app.add_url_rule("/profile", "profile", login_required(self.profile_window), methods=["GET", "POST"])
        app.add_url_rule("/admin", "admin", login_required(self.admin_window))
        app.add_url_rule("/admin", "admin_action", login_required(self.admin_action), methods=["POST"])

    def login_window(self):
        if request.method == "POST":
            try:
                return self._enter(self.login(request.form["name"], request.form["password"]))
            except ServiceError as error:
                flash(str(error), "error")
        return render_template("auth.html", tab="login")

    def register_window(self):
        if request.method == "POST":
            try:
                self._check_repeat()
                user = Specialist(None, request.form["name"].strip(), request.form["password"])
                return self._enter(self.register(user))
            except ServiceError as error:
                flash(str(error), "error")
        return render_template("auth.html", tab="register")

    def logout(self):
        session.clear()
        return redirect(url_for("login"))

    def profile_window(self):
        if request.method == "POST":
            def save():
                self._check_repeat()
                g.user.name = request.form["name"]
                self.update_profile(g.user, request.form["password"])
            return attempt(save, url_for("profile"), message="Данные сохранены")
        return render_template("profile.html")

    def admin_window(self):
        query = request.args.get("q", "")
        try:
            users = self.profile_service.find_users(query, g.user)
        except ServiceError as error:
            flash(str(error), "error")
            return redirect(url_for("feed"))
        return render_template("admin.html", users=users, query=query, chosen=request.args.get("chosen", ""))

    def admin_action(self):
        actions = {"block": self.block_user, "unblock": self.unblock_user,
                   "grant": self.grant_expert, "revoke": self.revoke_expert}
        chosen = request.form.get("user_id", "")
        url = url_for("admin", q=request.form.get("q", ""), chosen=chosen)
        return attempt(lambda: actions[request.form["action"]](selected("user_id")), url)

    @staticmethod
    def _enter(user: User):
        session["user_id"] = user.id
        return redirect(url_for("feed"))

    @staticmethod
    def _check_repeat():
        if request.form["password"] != request.form["password2"]:
            raise ServiceError("Пароли не совпадают")
