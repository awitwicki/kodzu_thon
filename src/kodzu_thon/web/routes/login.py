"""Login, TOTP second step and logout."""

from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from kodzu_thon.web import auth
from kodzu_thon.web.render import render
from kodzu_thon.web.routes.common import RepoDep
from kodzu_thon.web.security import (
    CsrfDep,
    NotAuthenticated,
    OptionalSessionDep,
    clear_session_cookie,
    client_ip,
    set_session_cookie,
    user_agent,
)

router = APIRouter()


def _too_many_attempts() -> HTTPException:
    return HTTPException(
        status_code=429,
        detail="Too many attempts",
        headers={"Retry-After": str(auth.RETRY_AFTER_SECONDS)},
    )


@router.get("/login")
async def login_form(request: Request, repo: RepoDep, session: OptionalSessionDep):
    settings = request.app.state.settings
    if session is not None and session["state"] == auth.STATE_AUTHED:
        return RedirectResponse("/", status_code=303)
    if session is not None and session["state"] == auth.STATE_PENDING_TOTP:
        if settings.totp_secret:
            return RedirectResponse("/login/totp", status_code=303)
        await repo.delete_session(session["token_hash"])  # TOTP was disabled mid-login
        session = None
    if session is None:
        token, session = await auth.create_session(
            repo,
            state=auth.STATE_ANON,
            username=None,
            ip=client_ip(request),
            user_agent=user_agent(request),
        )
        response = render(request, "login.html", session=session, error=None)
        set_session_cookie(response, token, secure=settings.cookie_secure)
        return response
    return render(request, "login.html", session=session, error=None)


@router.post("/login")
async def login_submit(
    request: Request,
    repo: RepoDep,
    session: CsrfDep,
    username: Annotated[str, Form(max_length=200)],
    password: Annotated[str, Form(max_length=1024)],
):
    settings = request.app.state.settings
    ip = client_ip(request)
    now = auth.utcnow()
    if await auth.is_rate_limited(repo, ip, settings.admin_user, now):
        auth.log_auth_event("login rate-limited", username=username, ip=ip)
        raise _too_many_attempts()
    ok = auth.verify_password(settings, username, password)
    await repo.record_login_attempt(ip, username, ok)
    if not ok:
        auth.log_auth_event("login failed", username=username, ip=ip)
        return render(
            request, "login.html", status=401, session=session, error="Invalid credentials"
        )
    state = auth.STATE_PENDING_TOTP if settings.totp_secret else auth.STATE_AUTHED
    token, _ = await auth.rotate_session(
        repo,
        session["token_hash"],
        state=state,
        username=settings.admin_user,
        ip=ip,
        user_agent=user_agent(request),
        now=now,
    )
    await repo.delete_expired_sessions(now)
    auth.log_auth_event(
        "login ok" if state == auth.STATE_AUTHED else "password ok, totp pending",
        username=username,
        ip=ip,
    )
    target = "/login/totp" if state == auth.STATE_PENDING_TOTP else "/"
    response = RedirectResponse(target, status_code=303)
    set_session_cookie(response, token, secure=settings.cookie_secure)
    return response


@router.get("/login/totp")
async def totp_form(request: Request, repo: RepoDep, session: OptionalSessionDep):
    settings = request.app.state.settings
    if not settings.totp_secret:
        return RedirectResponse("/login", status_code=303)
    if session is None or session["state"] != auth.STATE_PENDING_TOTP:
        raise NotAuthenticated()
    return render(request, "totp.html", session=session, error=None)


@router.post("/login/totp")
async def totp_submit(
    request: Request,
    repo: RepoDep,
    session: CsrfDep,
    code: Annotated[str, Form(max_length=16)],
):
    settings = request.app.state.settings
    if not settings.totp_secret or session["state"] != auth.STATE_PENDING_TOTP:
        raise NotAuthenticated()
    ip = client_ip(request)
    now = auth.utcnow()
    if await auth.is_rate_limited(repo, ip, settings.admin_user, now):
        auth.log_auth_event("totp rate-limited", username=settings.admin_user, ip=ip)
        raise _too_many_attempts()
    counter = auth.verify_totp(settings.totp_secret, code, await repo.get_totp_counter(), now)
    await repo.record_login_attempt(ip, settings.admin_user, counter is not None)
    if counter is None:
        auth.log_auth_event("totp failed", username=settings.admin_user, ip=ip)
        return render(request, "totp.html", status=401, session=session, error="Invalid code")
    await repo.set_totp_counter(counter)
    await repo.set_session_state(session["token_hash"], auth.STATE_AUTHED)
    auth.log_auth_event("totp ok", username=settings.admin_user, ip=ip)
    return RedirectResponse("/", status_code=303)


@router.post("/logout")
async def logout(request: Request, repo: RepoDep, session: CsrfDep):
    await repo.delete_session(session["token_hash"])
    auth.log_auth_event("logout", username=session["username"], ip=client_ip(request))
    response = RedirectResponse("/login", status_code=303)
    clear_session_cookie(response, secure=request.app.state.settings.cookie_secure)
    return response
