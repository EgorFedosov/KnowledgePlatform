from dataclasses import replace

from flask import flash, g, redirect, render_template, request, session, url_for

from controllers import attempt, loginRequired, selected
from models.profile import Specialist, User
from models.reputation import Rating
from services import ServiceError
from services.profile import ProfileService


class ProfileController:
    def __init__(self, profileService: ProfileService):
        self.profileService = profileService

    def register(self, user: User) -> User:
        return self.profileService.register(user)

    def login(self, name: str, password: str) -> User:
        return self.profileService.login(name, password)

    def updateProfile(self, user: User) -> User:
        return self.profileService.updateProfile(user)

    def updateRating(self, userId: int, rating: Rating) -> User:
        return self.profileService.updateRating(userId, rating)

    def blockUser(self, id: int) -> User:
        return self.profileService.blockUser(id)

    def unblockUser(self, id: int) -> User:
        return self.profileService.unblockUser(id)

    def grantExpert(self, id: int) -> User:
        return self.profileService.grantExpert(id)

    def revokeExpert(self, id: int) -> User:
        return self.profileService.revokeExpert(id)

    def bindRoutes(self, app):
        app.add_url_rule("/", "index", lambda: redirect(url_for("feed")))
        app.add_url_rule("/login", "login", self.loginWindow, methods=["GET", "POST"])
        app.add_url_rule("/register", "register", self.registerWindow, methods=["GET", "POST"])
        app.add_url_rule("/logout", "logout", self.logout)
        app.add_url_rule("/profile", "profile", loginRequired(self.profileWindow), methods=["GET", "POST"])
        app.add_url_rule("/admin", "admin", loginRequired(self.adminWindow))
        app.add_url_rule("/admin", "admin_action", loginRequired(self.adminAction), methods=["POST"])

    def loginWindow(self):
        if request.method == "POST":
            try:
                return self._enter(self.login(request.form["name"], request.form["password"]))
            except ServiceError as error:
                flash(str(error), "error")
        return render_template("auth.html", tab="login")

    def registerWindow(self):
        if request.method == "POST":
            try:
                self._checkRepeat()
                return self._enter(self.register(Specialist(None, request.form["name"], request.form["password"])))
            except ServiceError as error:
                flash(str(error), "error")
        return render_template("auth.html", tab="register")

    def logout(self):
        session.clear()
        return redirect(url_for("login"))

    def profileWindow(self):
        if request.method == "POST":
            def save():
                self._checkRepeat()
                self.updateProfile(replace(g.user, name=request.form["name"], password=request.form["password"]))
            return attempt(save, url_for("profile"), "Данные сохранены")
        return render_template("profile.html")

    def adminWindow(self):
        query = request.args.get("q", "")
        try:
            users = self.profileService.getUsers(query)
        except ServiceError as error:
            flash(str(error), "error")
            return redirect(url_for("feed"))
        return render_template("admin.html", users=users, query=query, chosen=request.args.get("chosen", ""))

    def adminAction(self):
        actions = {"block": self.blockUser, "unblock": self.unblockUser,
                   "grant": self.grantExpert, "revoke": self.revokeExpert}
        url = url_for("admin", q=request.form.get("q", ""), chosen=request.form.get("userId", ""))
        return attempt(lambda: actions[request.form["action"]](selected("userId")), url)

    @staticmethod
    def _enter(user: User):
        session["userId"] = user.id
        return redirect(url_for("feed"))

    @staticmethod
    def _checkRepeat():
        if request.form["password"] != request.form["password2"]:
            raise ServiceError("Пароли не совпадают")
