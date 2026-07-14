"""HTTP layer: FastAPI routes rendering htmx/Jinja fragments.

Presentation only — parse the request, delegate to the domain layer, render a
template. No business logic lives here: the auth routes translate between HTTP
forms and the domain ``UserManager`` and render daisyUI pages / htmx fragments.
"""

import contextlib
from pathlib import Path
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi_users import exceptions as fu_exceptions
from jinja2 import StrictUndefined
from pydantic import ValidationError

from app.domain.email_domains import DisposableEmailError
from app.domain.greeting import normalize_name
from app.domain.schemas import UserCreate
from app.domain.users import User, UserManager
from app.web.auth import (
    auth_backend,
    cookie_transport,
    current_optional_user,
    get_jwt_strategy,
    get_user_manager,
)

_WEB_DIR = Path(__file__).parent

templates = Jinja2Templates(directory=_WEB_DIR / "templates")
# Fail loudly on a typo'd or missing template variable instead of silently
# rendering a blank; a missing partial still raises TemplateNotFound.
templates.env.undefined = StrictUndefined

router = APIRouter()

# Reused so the "no account enumeration" responses stay identical everywhere.
_CHECK_INBOX = "Account created. Check your inbox to confirm your email address."

UserManagerDep = Annotated[UserManager, Depends(get_user_manager)]
OptionalUserDep = Annotated[User | None, Depends(current_optional_user)]


def _alert(request: Request, *, kind: str, message: str) -> HTMLResponse:
    """Render a daisyUI alert fragment for htmx to swap into ``#form-msg``."""
    return templates.TemplateResponse(
        request,
        "partials/auth_alert.html",
        {"kind": kind, "message": message},
    )


async def _get_user_or_none(user_manager: UserManager, email: str) -> User | None:
    """Look a user up by email, returning ``None`` instead of raising."""
    with contextlib.suppress(fu_exceptions.UserNotExists):
        # cast: fastapi-users types this as its ``UP`` TypeVar, which pyrefly
        # cannot resolve to our concrete ``User`` (see the note in domain/users).
        return cast("User", await user_manager.get_by_email(email))
    return None


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    """Render the full Hello World page."""
    return templates.TemplateResponse(request, "index.html")


@router.post("/greet", response_class=HTMLResponse)
def greet(request: Request, name: Annotated[str, Form()] = "") -> HTMLResponse:
    """Return only the greeting fragment, for htmx to swap into the page."""
    return templates.TemplateResponse(
        request,
        "partials/greeting.html",
        {"name": normalize_name(name)},
    )


# --------------------------------------------------------------------------- #
# Auth pages (GET) — full daisyUI pages that host the htmx forms.
# --------------------------------------------------------------------------- #
@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    """Render the sign-in page."""
    return templates.TemplateResponse(request, "auth/login.html")


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request) -> HTMLResponse:
    """Render the account-creation page."""
    return templates.TemplateResponse(request, "auth/register.html")


@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request) -> HTMLResponse:
    """Render the "request a reset link" page."""
    return templates.TemplateResponse(request, "auth/forgot_password.html")


@router.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(request: Request, token: str = "") -> HTMLResponse:
    """Render the "choose a new password" page for a reset link."""
    return templates.TemplateResponse(
        request, "auth/reset_password.html", {"token": token}
    )


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: OptionalUserDep) -> Response:
    """Protected page: show the current user, or redirect to sign in."""
    if user is None:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request, "dashboard.html", {"email": user.email})


# --------------------------------------------------------------------------- #
# Auth actions (POST) — htmx handlers returning fragments or an HX-Redirect.
# --------------------------------------------------------------------------- #
@router.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    user_manager: UserManagerDep,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
) -> Response:
    """Authenticate the credentials and set the session cookie on success."""
    credentials = OAuth2PasswordRequestForm(username=email, password=password)
    user = cast("User | None", await user_manager.authenticate(credentials))
    if user is None or not user.is_active:
        return _alert(request, kind="error", message="Invalid email or password.")
    if not user.is_verified:
        return templates.TemplateResponse(
            request, "partials/verify_needed.html", {"email": email}
        )
    # pyrefly: ignore[bad-argument-type]  (User vs fastapi-users' unresolved UP)
    response = await auth_backend.login(get_jwt_strategy(), user)
    response.headers["HX-Redirect"] = "/dashboard"
    return response


@router.post("/register", response_class=HTMLResponse)
async def register(
    request: Request,
    user_manager: UserManagerDep,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    confirm_password: Annotated[str, Form()],
) -> HTMLResponse:
    """Create an account and send an email-confirmation link."""
    if password != confirm_password:
        return _alert(request, kind="error", message="Passwords do not match.")
    try:
        user_create = UserCreate(email=email, password=password)
    except ValidationError:
        return _alert(
            request, kind="error", message="Please enter a valid email address."
        )
    try:
        user = await user_manager.create(user_create, safe=True, request=request)
    except DisposableEmailError as exc:
        return _alert(request, kind="error", message=str(exc))
    except fu_exceptions.UserAlreadyExists:
        # Do not reveal whether the email is already registered.
        return _alert(request, kind="success", message=_CHECK_INBOX)
    except fu_exceptions.InvalidPasswordException as exc:
        return _alert(request, kind="error", message=str(exc.reason))
    # `create` is overridden to return the concrete ``User``; pyrefly can't
    # reconcile that with request_verify's cross-module ``UP`` TypeVar (see the
    # note in app/domain/users.py). The call is sound and covered by the tests.
    # pyrefly: ignore[bad-argument-type]
    await user_manager.request_verify(user, request)
    return _alert(request, kind="success", message=_CHECK_INBOX)


@router.get("/verify", response_class=HTMLResponse)
async def verify(
    request: Request, user_manager: UserManagerDep, token: str = ""
) -> HTMLResponse:
    """Consume an email-confirmation link and report the outcome."""
    try:
        await user_manager.verify(token)
    except fu_exceptions.InvalidVerifyToken:
        return templates.TemplateResponse(
            request, "auth/verify_result.html", {"ok": False}
        )
    except fu_exceptions.UserAlreadyVerified:
        return templates.TemplateResponse(
            request, "auth/verify_result.html", {"ok": True}
        )
    return templates.TemplateResponse(request, "auth/verify_result.html", {"ok": True})


@router.post("/resend-verification", response_class=HTMLResponse)
async def resend_verification(
    request: Request,
    user_manager: UserManagerDep,
    email: Annotated[str, Form()],
) -> HTMLResponse:
    """Re-send the confirmation link (neutral response, no enumeration)."""
    user = await _get_user_or_none(user_manager, email)
    if user is not None and not user.is_verified:
        with contextlib.suppress(fu_exceptions.FastAPIUsersException):
            # pyrefly: ignore[bad-argument-type]  (User vs unresolved UP)
            await user_manager.request_verify(user, request)
    return _alert(
        request,
        kind="info",
        message="If that account exists and is unconfirmed, we've sent a new link.",
    )


@router.post("/forgot-password", response_class=HTMLResponse)
async def forgot_password(
    request: Request,
    user_manager: UserManagerDep,
    email: Annotated[str, Form()],
) -> HTMLResponse:
    """Trigger a password-reset email (neutral response, no enumeration)."""
    user = await _get_user_or_none(user_manager, email)
    if user is not None:
        with contextlib.suppress(fu_exceptions.FastAPIUsersException):
            # pyrefly: ignore[bad-argument-type]  (User vs unresolved UP)
            await user_manager.forgot_password(user, request)
    return _alert(
        request,
        kind="info",
        message="If an account exists for that email, we've sent a reset link.",
    )


@router.post("/reset-password", response_class=HTMLResponse)
async def reset_password(
    request: Request,
    user_manager: UserManagerDep,
    token: Annotated[str, Form()],
    password: Annotated[str, Form()],
    confirm_password: Annotated[str, Form()],
) -> Response:
    """Apply a new password from a reset link."""
    if password != confirm_password:
        return _alert(request, kind="error", message="Passwords do not match.")
    try:
        await user_manager.reset_password(token, password)
    except (
        fu_exceptions.InvalidResetPasswordToken,
        fu_exceptions.UserInactive,
        fu_exceptions.UserNotExists,
    ):
        return _alert(
            request, kind="error", message="This reset link is invalid or has expired."
        )
    except fu_exceptions.InvalidPasswordException as exc:
        return _alert(request, kind="error", message=str(exc.reason))
    response = _alert(
        request, kind="success", message="Password updated. Redirecting to sign in…"
    )
    response.headers["HX-Redirect"] = "/login"
    return response


@router.post("/logout")
async def logout() -> Response:
    """Clear the session cookie and send the client back to sign in."""
    response = await cookie_transport.get_logout_response()
    response.headers["HX-Redirect"] = "/login"
    return response
