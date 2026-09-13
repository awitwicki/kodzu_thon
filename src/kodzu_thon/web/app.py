"""FastAPI application factory for kodzuthon.web."""

import sys
import traceback
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from kodzu_thon.db import SCHEMA_VERSION
from kodzu_thon.web.config import WebSettings
from kodzu_thon.web.render import STATIC_DIR, build_env, render
from kodzu_thon.web.repository import Repository
from kodzu_thon.web.routes import ROUTERS
from kodzu_thon.web.security import (
    NotAuthenticated,
    SecurityHeadersMiddleware,
    apply_security_headers,
)

STATEMENT_TIMEOUT_MS = 10_000
_ERROR_MESSAGES = {
    403: "Forbidden",
    404: "Not found",
    422: "Bad request",
    429: "Too many attempts, try again later",
}


async def check_schema(repo) -> int:
    version = await repo.schema_version()
    if version is None or version < SCHEMA_VERSION:
        raise RuntimeError(
            f"database schema version {version} is older than required {SCHEMA_VERSION}; "
            "start the recorder (kodzuthon) first so it applies its migrations"
        )
    return version


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: WebSettings = app.state.settings
    owns_repo = app.state.repo is None
    if owns_repo:
        pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=1,
            max_size=4,
            server_settings={"statement_timeout": str(STATEMENT_TIMEOUT_MS)},
        )
        app.state.repo = Repository(pool)
    try:
        await check_schema(app.state.repo)
        yield
    finally:
        if owns_repo and app.state.repo is not None:
            await app.state.repo.close()
            app.state.repo = None


def create_app(settings: WebSettings, repo=None) -> FastAPI:
    app = FastAPI(debug=False, docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.settings = settings
    app.state.repo = repo
    app.state.jinja = build_env(settings.timezone)
    app.state.last_sweep = None
    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.cookie_secure)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    for router in ROUTERS:
        app.include_router(router)
    _register_error_handlers(app)
    return app


def _register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotAuthenticated)
    async def not_authenticated(request: Request, exc: NotAuthenticated):
        return RedirectResponse("/login", status_code=303)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        message = _ERROR_MESSAGES.get(exc.status_code, "Request failed")
        return render(
            request,
            "error.html",
            status=exc.status_code,
            headers=exc.headers,
            status_code=exc.status_code,
            message=message,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return render(request, "error.html", status=422, status_code=422, message="Bad request")

    @app.exception_handler(Exception)
    async def server_error(request: Request, exc: Exception):
        traceback.print_exception(exc, file=sys.stderr)
        response = render(
            request, "error.html", status=500, status_code=500, message="Internal error"
        )
        # This handler runs outside the middleware stack, so add the headers here too.
        apply_security_headers(response, hsts=request.app.state.settings.cookie_secure)
        return response
