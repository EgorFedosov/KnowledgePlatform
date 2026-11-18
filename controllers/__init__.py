from functools import wraps

from flask import flash, g, redirect, request, url_for

from services import ServiceError


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper


def attempt(action, success_url: str, fail_url: str | None = None, message: str = ""):
    try:
        action()
    except ServiceError as error:
        flash(str(error), "error")
        return redirect(fail_url or success_url)
    if message:
        flash(message, "ok")
    return redirect(success_url)


def selected(field: str) -> int:
    value = request.form.get(field, "")
    if not value.isdigit():
        raise ServiceError("Выберите строку в таблице")
    return int(value)


def back() -> str:
    return request.referrer or url_for("feed")
