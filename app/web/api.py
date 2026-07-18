"""HTTP layer: the JSON REST API.

Presentation only — this module translates HTTP requests into calls on the domain
``UserManager`` and returns JSON. It mounts fastapi-users' standard auth and user
routers under ``/api`` and adds a thin, anti-enumeration registration endpoint plus
the demo greeting. No business logic lives here; the rules live in ``app.domain``.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi_users import exceptions as fu_exceptions
from pydantic import BaseModel

from app.domain.email_domains import DisposableEmailError
from app.domain.greeting import normalize_name
from app.domain.schemas import UserCreate, UserRead, UserUpdate
from app.domain.users import UserManager
from app.web.auth import auth_backend, fastapi_users, get_user_manager

UserManagerDep = Annotated[UserManager, Depends(get_user_manager)]

# Reused so the "no account enumeration" response stays identical whether or not the
# address is already registered.
_CHECK_INBOX = "Account created. Check your inbox to confirm your email address."


class MessageResponse(BaseModel):
    """A simple ``{"message": ...}`` envelope for endpoints without a resource body."""

    message: str


router = APIRouter(prefix="/api")


@router.post(
    "/auth/register",
    tags=["auth"],
    status_code=status.HTTP_202_ACCEPTED,
)
async def register(
    user_create: UserCreate,
    user_manager: UserManagerDep,
    request: Request,
) -> MessageResponse:
    """Create an account and email a confirmation link.

    Deliberately does **not** reveal whether the address was already registered:
    both a fresh creation and an ``UserAlreadyExists`` collision return the same
    neutral ``202`` so the endpoint can't be used to enumerate accounts. The
    verification email is sent from ``UserManager.on_after_register``.
    """
    try:
        await user_manager.create(user_create, safe=True, request=request)
    except fu_exceptions.UserAlreadyExists:
        # Same response as success — never confirm the address exists.
        return MessageResponse(message=_CHECK_INBOX)
    except DisposableEmailError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except fu_exceptions.InvalidPasswordException as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=str(exc.reason)
        ) from exc
    return MessageResponse(message=_CHECK_INBOX)


@router.get("/greeting", tags=["greeting"])
def greeting(name: str = "") -> MessageResponse:
    """Return a greeting for ``name``, falling back to a default when blank."""
    return MessageResponse(message=f"Hello, {normalize_name(name)}!")


# fastapi-users' standard routers cover the rest of the auth surface with
# conventional REST endpoints and JSON bodies:
#   /auth/login, /auth/logout                       (cookie session)
#   /auth/request-verify-token, /auth/verify        (email confirmation)
#   /auth/forgot-password, /auth/reset-password     (password reset)
#   /users/me, /users/{id}                          (profile)
# The custom /auth/register above replaces the stock register router so the
# anti-enumeration response and domain-driven verification email are preserved.
router.include_router(
    # requires_verification=True blocks login until the email is confirmed.
    # pyrefly: ignore[bad-argument-type]  (auth_backend's UP vs the unresolved UP)
    fastapi_users.get_auth_router(auth_backend, requires_verification=True),
    prefix="/auth",
    tags=["auth"],
)
router.include_router(
    fastapi_users.get_verify_router(UserRead), prefix="/auth", tags=["auth"]
)
router.include_router(
    fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"]
)
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)
