"""Application errors that map to structured JSON responses."""


class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field


class NotFound(AppError):
    status_code = 404
    code = "not_found"


class Conflict(AppError):
    status_code = 409
    code = "conflict"


class InvalidInput(AppError):
    status_code = 422
    code = "validation_error"
