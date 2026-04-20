
from fastapi import status
from pydantic import BaseModel

class ErrorResponse(BaseModel):
    code: int
    reason: str
    message: str

error_responses = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    400: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}


class HTTPException(Exception):
    def __init__(self, status_code: int, reason: str, message: str):
        self.status_code = status_code
        self.reason = reason
        self.message = message

class OpenAIAPIException(HTTPException):
    pass

def http_exception_factory(
    status_code: int,
    reason: str,
    default_message: str
):
    class_name = reason + "Exception"
    
    def init(self, message=default_message, is_openai_exception=False):
        if is_openai_exception:
            self.__class__.__bases__ = (OpenAIAPIException,)
        super(self.__class__, self).__init__(status_code, reason, message)

    return type(
        class_name,
        (HTTPException,),
        {"__init__": init},
    )


InvalidException = http_exception_factory(
    status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid", "Invalid input"
)