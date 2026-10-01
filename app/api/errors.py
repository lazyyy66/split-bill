"""Ошибки API: {"code": "err_...", "message": "<текст на языке пользователя>"}.

code стабилен (фронт может на него опираться), message — для показа человеку.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.bot.texts import TEXTS, t
from app.services.balances import SettlementError
from app.services.expenses import ExpenseConflictError, ExpenseError


class ApiError(Exception):
    def __init__(self, status: int, code: str) -> None:
        super().__init__(code)
        self.status = status
        self.code = code


def _response(request: Request, status: int, code: str) -> JSONResponse:
    lang = getattr(request.state, "lang", "ru")
    message = t(lang, code) if code in TEXTS else code
    return JSONResponse(status_code=status, content={"code": code, "message": message})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error(request: Request, error: ApiError) -> JSONResponse:
        return _response(request, error.status, error.code)

    @app.exception_handler(ExpenseConflictError)
    async def conflict(request: Request, error: ExpenseConflictError) -> JSONResponse:
        return _response(request, 409, error.args[0])

    @app.exception_handler(ExpenseError)
    @app.exception_handler(SettlementError)
    async def domain_error(request: Request, error: Exception) -> JSONResponse:
        return _response(request, 400, error.args[0])
