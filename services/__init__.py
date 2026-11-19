from flask import g, has_app_context


class ServiceError(Exception):
    pass


def require(condition: bool, message: str):
    if not condition:
        raise ServiceError(message)


def currentUser():
    return g.get("user") if has_app_context() else None


def requireRole(role: type, message: str):
    require(isinstance(currentUser(), role), message)
