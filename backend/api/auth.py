from fastapi import APIRouter, Depends, Request, Response

from ..schemas import LoginIn, PasswordChangeIn, RecoveryCodeIn, RegisterIn, ResetPasswordIn
from ..services import auth
from .deps import SESSION_COOKIE, get_conn, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_cookie(request, response, token, days):
    response.set_cookie(
        SESSION_COOKIE, token, max_age=days * 86400, path="/",
        httponly=True, samesite="lax", secure=request.url.scheme == "https",
    )


def _client_ip(request):
    return request.client.host if request.client else None


@router.post("/register", status_code=201)
def register(data: RegisterIn, request: Request, response: Response, conn=Depends(get_conn)):
    settings = request.app.state.settings
    user, token, recovery_code = auth.register(conn, data, settings.session_days, settings.allow_signup)
    _set_cookie(request, response, token, settings.session_days)
    # The recovery code is only ever shown here, once.
    return {**auth.public_user(user, auth.owner_id(conn)), "recovery_code": recovery_code}


@router.post("/login")
def login(data: LoginIn, request: Request, response: Response, conn=Depends(get_conn)):
    settings = request.app.state.settings
    days = settings.remember_days if data.remember else settings.session_days
    user, token = auth.login(conn, data.email, data.password, _client_ip(request), days)
    _set_cookie(request, response, token, days)
    return auth.public_user(user, auth.owner_id(conn))


@router.post("/logout")
def logout(request: Request, response: Response, conn=Depends(get_conn)):
    auth.end_session(conn, request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"logged_out": True}


@router.post("/reset-password")
def reset_password(data: ResetPasswordIn, request: Request, response: Response, conn=Depends(get_conn)):
    """Forgot password: set a new one with the recovery code. Issues a fresh code (the old one is used up)."""
    settings = request.app.state.settings
    user, token, new_code = auth.reset_with_recovery_code(
        conn, data.email, data.recovery_code, data.new_password, _client_ip(request), settings.session_days)
    _set_cookie(request, response, token, settings.session_days)
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
    return {**auth.public_user(user, auth.owner_id(conn)), "recovery_code": new_code}


@router.post("/recovery-code")
def new_recovery_code(data: RecoveryCodeIn, user=Depends(get_current_user), conn=Depends(get_conn)):
    """Replace the recovery code (the old one stops working). Requires the password."""
    return {"recovery_code": auth.regenerate_recovery_code(conn, user["id"], data.password)}


@router.get("/me")
def me(user=Depends(get_current_user), conn=Depends(get_conn)):
    return auth.public_user(user, auth.owner_id(conn))


@router.put("/password")
def change_password(data: PasswordChangeIn, request: Request, user=Depends(get_current_user), conn=Depends(get_conn)):
    auth.change_password(conn, user["id"], data.current_password, data.new_password, request.cookies.get(SESSION_COOKIE))
    return {"changed": True}
