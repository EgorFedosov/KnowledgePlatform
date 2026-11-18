class ServiceError(Exception):
    pass


def require(condition: bool, message: str):
    if not condition:
        raise ServiceError(message)
