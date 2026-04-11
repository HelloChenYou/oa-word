from fastapi import APIRouter, Depends

from app.config import settings
from fastapi import Depends, HTTPException

from app.schemas import AuthUserOut, ChangePasswordReq, ChangePasswordResp, LoginReq, LoginResp
from app.security import authenticate_user, change_user_password, create_access_token, require_authenticated


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=LoginResp)
def login(req: LoginReq):
    user = authenticate_user(req.username, req.password)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid credentials")

    return LoginResp(
        access_token=create_access_token(user["username"], user["role"], user["must_change_password"]),
        expires_in=settings.auth_token_expire_sec,
        user=AuthUserOut(
            username=user["username"],
            role=user["role"],
            must_change_password=user["must_change_password"],
        ),
    )


@router.get("/me", response_model=AuthUserOut)
def me(current_user: dict = Depends(require_authenticated)):
    return AuthUserOut(
        username=current_user["username"],
        role=current_user["role"],
        must_change_password=current_user["must_change_password"],
    )


@router.post("/change-password", response_model=ChangePasswordResp)
def change_password(req: ChangePasswordReq, current_user: dict = Depends(require_authenticated)):
    updated = change_user_password(
        username=current_user["username"],
        current_password=req.current_password,
        new_password=req.new_password,
    )
    if updated is None:
        raise HTTPException(status_code=400, detail="current password is incorrect")
    return ChangePasswordResp(
        access_token=create_access_token(updated["username"], updated["role"], updated["must_change_password"]),
        expires_in=settings.auth_token_expire_sec,
        user=AuthUserOut(
            username=updated["username"],
            role=updated["role"],
            must_change_password=updated["must_change_password"],
        ),
    )
