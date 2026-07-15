from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .exceptions import WriteWingedException


async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "internal_server_error", "message": "Something went wrong."},
    )


async def writewinged_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, WriteWingedException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.__class__.__name__, "message": exc.message},
        )
    return await general_exception_handler(request, exc)


async def request_validation_handler(request: Request, exc: Exception):
    if isinstance(exc, RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"error": "request_validation_error", "message": exc.errors()},
        )
    return await general_exception_handler(request, exc)
