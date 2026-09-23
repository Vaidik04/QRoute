from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.logging import logger

class BaseAppException(Exception):
    """Base exception class for Q-TRANSIT application errors."""
    def __init__(self, code: str, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class ResourceNotFoundException(BaseAppException):
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            code="RESOURCE_NOT_FOUND",
            message=f"{resource} with ID '{resource_id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND
        )

class ValidationException(BaseAppException):
    def __init__(self, message: str):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

class ExternalServiceException(BaseAppException):
    def __init__(self, service: str, details: str):
        super().__init__(
            code="EXTERNAL_SERVICE_ERROR",
            message=f"Error connecting to external service '{service}': {details}",
            status_code=status.HTTP_502_BAD_GATEWAY
        )

def create_error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message
            }
        }
    )

from starlette.exceptions import HTTPException as StarletteHTTPException

async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
    logger.warning(f"HTTP Exception [{exc.status_code}]: {exc.detail} (Path: {request.url.path})")
    return create_error_response(code, str(exc.detail), exc.status_code)

async def app_exception_handler(request: Request, exc: BaseAppException) -> JSONResponse:
    logger.warning(f"Application Exception [{exc.code}]: {exc.message} (Path: {request.url.path})")
    return create_error_response(exc.code, exc.message, exc.status_code)

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    first_error = errors[0]["msg"] if errors else "Invalid request parameters"
    logger.warning(f"Validation Error: {first_error} (Path: {request.url.path})")
    return create_error_response("VALIDATION_ERROR", f"Invalid payload: {first_error}", status.HTTP_422_UNPROCESSABLE_ENTITY)

async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Unhandled Exception on {request.url.path}: {str(exc)}", exc_info=True)
    return create_error_response(
        "INTERNAL_SERVER_ERROR",
        "An internal server error occurred. Please contact support or check server logs.",
        status.HTTP_500_INTERNAL_SERVER_ERROR
    )
