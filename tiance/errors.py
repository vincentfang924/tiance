from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class TianceError(Exception):
    status_code = 400
    code = "TIANCE_ERROR"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class StockNotFound(TianceError):
    status_code = 404
    code = "STOCK_NOT_FOUND"


class AnnouncementNotFound(TianceError):
    status_code = 404
    code = "ANNOUNCEMENT_NOT_FOUND"


class AlreadyWatching(TianceError):
    status_code = 409
    code = "ALREADY_WATCHING"


class TaskRunning(TianceError):
    status_code = 409
    code = "TASK_RUNNING"


class TianyanUnavailable(TianceError):
    status_code = 503
    code = "TIANYAN_UNAVAILABLE"


class InvalidFreq(TianceError):
    status_code = 400
    code = "INVALID_FREQ"


def data_response(data):
    return {"data": data}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(TianceError)
    async def handle_tiance_error(_: Request, exc: TianceError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "请求参数无效",
                    "details": exc.errors(),
                }
            },
        )
