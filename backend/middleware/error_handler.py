"""全局异常处理"""
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from middleware.logger import logger


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} | {request.method} {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_code": f"HTTP_{exc.status_code}"},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    logger.warning(f"Validation error: {errors} | {request.method} {request.url.path}")
    return JSONResponse(
        status_code=422,
        content={"detail": "请求参数校验失败", "error_code": "VALIDATION_ERROR", "errors": errors},
    )


async def general_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception: {exc} | {request.method} {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误", "error_code": "INTERNAL_ERROR"},
    )


def register_exception_handlers(app):
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
