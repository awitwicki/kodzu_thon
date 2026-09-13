"""Jinja environment and the one HTML rendering helper."""

from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from kodzu_thon.web.textfmt import display_name, format_text, human_size, local_time

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"


def build_env(timezone: str) -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(default=True, default_for_string=True),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["fmt_text"] = format_text
    env.filters["localtime"] = lambda value: local_time(value, timezone)
    env.filters["human_size"] = human_size
    env.globals["display_name"] = display_name
    return env


def render(
    request: Request,
    template: str,
    *,
    status: int = 200,
    headers: dict[str, str] | None = None,
    **context: Any,
) -> HTMLResponse:
    env: Environment = request.app.state.jinja
    context.setdefault("session", None)
    context.setdefault("q", None)
    context.setdefault("query", dict(request.query_params))
    context.setdefault("path", request.url.path)
    html = env.get_template(template).render(**context)
    return HTMLResponse(html, status_code=status, headers=headers)
