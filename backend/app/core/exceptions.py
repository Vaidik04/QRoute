from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger("qtransit")

class QTransitException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class InfeasibleProblemException(QTransitException):
    def __init__(self, message: str = "No feasible route exists under current constraints.", details: dict = None):
        super().__init__(
            code="INFEASIBLE_PROBLEM",
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )

class TrafficUnavailableException(QTransitException):
    def __init__(self, message: str = "Traffic data currently unavailable.", details: dict = None):
        super().__init__(
            code="TRAFFIC_UNAVAILABLE",
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )

class OptimizationFailedException(QTransitException):
    def __init__(self, message: str = "Optimization algorithm execution failed.", details: dict = None):
        super().__init__(
            code="OPTIMIZATION_FAILED",
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )

class SimulationFailedException(QTransitException):
    def __init__(self, message: str = "Simulation execution encountered an error.", details: dict = None):
        super().__init__(
            code="SIMULATION_FAILED",
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )

class NotFoundException(QTransitException):
    def __init__(self, resource: str = "Resource", resource_id: str = ""):
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource} with identifier '{resource_id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND
        )

async def qtransit_exception_handler(request: Request, exc: QTransitException):
    logger.warning(f"QTransitException [{exc.code}] on {request.url.path}: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )

async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected internal service error occurred.",
                "details": {}
            }
        }
    )
