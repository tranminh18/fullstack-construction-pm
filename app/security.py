from datetime import datetime, timedelta
import os
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session, select

from .db import get_session
from .models import Project, ProjectMember, TokenData, User, UserRole

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# bcrypt giới hạn 72 byte; cắt bớt để tránh ValueError với mật khẩu dài.
_BCRYPT_MAX_BYTES = 72


def _to_bcrypt_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(_to_bcrypt_bytes(plain_password), hashed_password.encode("utf-8"))


def get_password_hash(password):
    return bcrypt.hashpw(_to_bcrypt_bytes(password), bcrypt.gensalt()).decode("utf-8")


def authenticate_user(email: str, password: str, session: Session):
    user = session.exec(select(User).where(User.email == email)).first()
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_refresh_token(token: str) -> str:
    """Giải mã refresh token, trả về email (sub). Raise 401 nếu không hợp lệ."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise credentials_exception
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
        return email
    except JWTError:
        raise credentials_exception


async def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") == "refresh":
            # Refresh token không được dùng để truy cập tài nguyên.
            raise credentials_exception
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = session.exec(select(User).where(User.email == token_data.email)).first()
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_project_role(project_id: int, user_id: int, session: Session) -> Optional[str]:
    project = session.exec(select(Project).where(Project.id == project_id)).first()
    if not project:
        return None
    if project.owner_id == user_id:
        return "owner"
    member = session.exec(
        select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
    ).first()
    if member:
        return member.role
    return None


def require_project_access(project_id: int, current_user: User, session: Session) -> Project:
    project = session.exec(select(Project).where(Project.id == project_id)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if get_project_role(project_id, current_user.id, session) is None:
        raise HTTPException(status_code=403, detail="Access denied")
    return project


def require_project_management(project_id: int, current_user: User, session: Session) -> Project:
    project = require_project_access(project_id, current_user, session)
    role = get_project_role(project_id, current_user.id, session)
    if role not in {"owner", "manager"}:
        raise HTTPException(status_code=403, detail="Manager access required")
    return project


def require_business_role(current_user: User, allowed_roles: set[UserRole]) -> User:
    """Kiểm tra vai trò nghiệp vụ (cấp hệ thống) của người dùng."""
    if current_user.role not in allowed_roles:
        allowed = ", ".join(sorted(role.value for role in allowed_roles))
        raise HTTPException(
            status_code=403,
            detail=f"Role '{current_user.role.value}' not permitted. Requires one of: {allowed}",
        )
    return current_user


# Ma trận phân quyền nghiệp vụ theo từng hành động trên công trường.
# Tập trung tại đây để dễ rà soát và giải trình, thay vì rải rác trong các router.
CAN_ASSIGN_TASK = {UserRole.construction_company, UserRole.contractor, UserRole.site_manager}
CAN_ACCEPT_WORK = {UserRole.construction_company, UserRole.site_manager}
CAN_APPROVE_CHANGE_ORDER = {UserRole.homeowner, UserRole.construction_company}
CAN_SETTLE_PAYMENT = {UserRole.homeowner, UserRole.construction_company}
