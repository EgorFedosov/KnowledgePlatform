from functools import wraps

from flask import flash, g, redirect, request, url_for

from models.content import Tag
from services import ServiceError


def loginRequired(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper


def attempt(action, successUrl: str, message: str = ""):
    try:
        action()
    except ServiceError as error:
        flash(str(error), "error")
        return redirect(successUrl)
    if message:
        flash(message, "ok")
    return redirect(successUrl)


def selected(field: str) -> int:
    value = request.form.get(field, "")
    if not value.isdigit():
        raise ServiceError("Выберите строку в таблице")
    return int(value)


def back() -> str:
    return request.referrer or url_for("feed")


def parseTags(text: str) -> list[Tag]:
    return [Tag(None, name) for name in text.replace(";", ",").split(",")]
