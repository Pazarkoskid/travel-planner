from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


class ServiceError(APIException):

    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "service_error"

    def __init__(self, message, code=None, status_code=None):
        super().__init__(detail=message, code=code or self.default_code)
        self.error_code = code or self.default_code
        if status_code:
            self.status_code = status_code


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None
    code = getattr(exc, "error_code", None) or getattr(exc, "default_code", None) or {
        404: "not_found", 403: "forbidden", 401: "not_authenticated"}.get(response.status_code, "error")
    data = response.data
    if isinstance(data, dict) and "detail" in data and len(data) == 1:
        message, details = str(data["detail"]), None
    elif isinstance(data, list):
        message, details = " ".join(str(d) for d in data), None
    else:
        message, details = "Невалидни податоци.", data
    response.data = {"error": {"code": code, "message": message, "details": details}}
    return response
