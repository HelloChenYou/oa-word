from fastapi import APIRouter, HTTPException

from app.schemas import CreateUserReq, ResetUserPasswordReq, UpdateUserReq, UserOut
from app.security import create_user_account, list_users, reset_user_password, update_user_account


router = APIRouter(prefix="/api/v1/users", tags=["users"])


def _to_user_out(user) -> UserOut:
    return UserOut(
        username=user.username,
        role=user.role,
        enabled=user.enabled,
        must_change_password=user.must_change_password,
        created_at=user.created_at.isoformat(),
    )


@router.get("", response_model=list[UserOut])
def get_users():
    return [_to_user_out(user) for user in list_users()]


@router.post("", response_model=UserOut)
def post_user(req: CreateUserReq):
    user = create_user_account(
        username=req.username,
        password=req.password,
        role=req.role,
        enabled=req.enabled,
        must_change_password=req.must_change_password,
    )
    if user is None:
        raise HTTPException(status_code=409, detail="username already exists")
    return _to_user_out(user)


@router.patch("/{username}", response_model=UserOut)
def patch_user(username: str, req: UpdateUserReq):
    updates = req.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="no updates provided")
    user = update_user_account(username, **updates)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return _to_user_out(user)


@router.post("/{username}/reset-password", response_model=UserOut)
def post_reset_password(username: str, req: ResetUserPasswordReq):
    user = reset_user_password(
        username=username,
        new_password=req.new_password,
        must_change_password=req.must_change_password,
    )
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return _to_user_out(user)
