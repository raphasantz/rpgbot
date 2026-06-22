"""Authentication utilities for MezzaRPG Web - sync version."""
import os
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db, JogadorWeb

# Config — lê de variável de ambiente; gera chave aleatória se não estiver definida
# Production flag — cookies are only secure (HTTPS-only) in prod
_IS_PROD = os.getenv("MEZZARPG_ENV", "dev").lower() in ("prod", "production")
_env_key = os.environ.get("MEZZARPG_SECRET_KEY", "")
if not _env_key:
    if _IS_PROD:
        raise RuntimeError("MEZZARPG_SECRET_KEY obrigatória em produção")
    _env_key = secrets.token_hex(32)
    print("[auth] AVISO: MEZZARPG_SECRET_KEY não definida no .env — usando chave gerada (tokens não persistem entre reinícios)")
SECRET_KEY = _env_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

# ── Password Hashing ──────────────────────────────────────────────────────
# NOTA DE SEGURANÇA: O SHA256 pre-hash antes do bcrypt é uma camada
# desnecessária que não melhora a segurança. Bcrypt já lida com senhas
# longas (trunca em 72 bytes internamente). O SHA256 intermediário:
#   1. Não adiciona entropia
#   2. Cria um hash rápido (SHA256) que um atacante com o DB poderia
#      pré-computar antes de atacar o bcrypt
#   3. Adiciona complexidade sem benefício
#
# PLANO DE MIGRAÇÃO (não pode ser feito em um passo só):
#   1. Adicionar coluna `hash_version` (default=1 para SHA256+bcrypt)
#   2. Em verify_password: se hash_version==1, verificar com SHA256+bcrypt;
#      se correto, re-hashear com bcrypt puro (version=2) e atualizar o DB
#   3. Em get_password_hash: sempre usar bcrypt puro (version=2)
#   4. Após todas as senhas migradas (verificar via query), remover o
#      código SHA256 e a coluna hash_version
#
# Por enquanto, manter a lógica atual para não quebrar logins existentes.


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pre = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
    return pwd_context.verify(pre, hashed_password)


def get_password_hash(password: str) -> str:
    pre = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return pwd_context.hash(pre)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["type"] = "access"
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_reset_token(telefone: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a password reset token (short-lived, 1 hour)."""
    to_encode = {"sub": telefone, "type": "reset"}
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=1)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_reset_token(token: str) -> Optional[str]:
    """Verify reset token and return telefone if valid."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "reset":
            return None
        telefone: str = payload.get("sub")
        return telefone
    except JWTError:
        return None


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[JogadorWeb]:
    """Get current user from JWT cookie."""
    token = request.cookies.get("access_token")
    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Reject reset tokens (or any non-access type) used as access tokens
        if payload.get("type") not in (None, "access"):
            return None
        telefone: str = payload.get("sub")
        if telefone is None:
            return None
    except JWTError:
        return None

    user = db.query(JogadorWeb).filter(JogadorWeb.telefone == telefone).first()
    return user


def require_user(
    request: Request,
    db: Session = Depends(get_db),
) -> JogadorWeb:
    """Require authenticated user (raises 401 if not authenticated)."""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def set_auth_cookie(response: Response, token: str, max_age: Optional[int] = None):
    """Set JWT in HttpOnly cookie."""
    if max_age is None:
        max_age = ACCESS_TOKEN_EXPIRE_MINUTES * 60
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=_IS_PROD,  # True in production with HTTPS
        samesite="lax",
        max_age=max_age,
        path="/",
    )


def clear_auth_cookie(response: Response):
    """Clear auth cookie."""
    response.delete_cookie(key="access_token", path="/")
