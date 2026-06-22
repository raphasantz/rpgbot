"""FastAPI app entrypoint for MezzaRPG Web."""
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import logging

# Carrega variáveis de ambiente ANTES de importar rotas
load_dotenv()

# Configuração de logging estruturado (#21)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("mezzarpg")

from fastapi import FastAPI, Request
import os
import json
import uuid
from urllib.parse import urlparse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from jose import jwt, JWTError

from app.database import init_db, SessionLocal, JogadorWeb
from app.routes import auth, game
from app.ws_manager import ws_manager
from app.templates_config import templates
from app.auth import SECRET_KEY, ALGORITHM


# ─── CSRF Origin middleware ───────────────────────────────────────────────────
# Reject state-changing requests whose Origin/Referer host is not allowlisted.
_ALLOWED_CSRF_HOSTS = {
    "localhost",
    "127.0.0.1",
    "mezza.rednerds.com.br",
    "www.mezza.rednerds.com.br",
}


class CSRFOriginMiddleware(BaseHTTPMiddleware):
    """Reject POST/PUT/DELETE/PATCH requests from disallowed origins.

    Also validates a double-submit CSRF token (cookie vs X-CSRF-Token header)
    for state-changing requests.
    """

    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            # 1. Origin/Referer check — mandatory for ALL state-changing requests.
            #    Browsers always send Origin on POST; if both Origin and Referer
            #    are missing, the request is suspect and must be rejected.
            origin = request.headers.get("origin") or request.headers.get("referer")
            if not origin:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Origin/Referer obrigatório para requisições state-changing"},
                )
            host = urlparse(origin).hostname or ""
            if host not in _ALLOWED_CSRF_HOSTS:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Origin não permitida"},
                )
            # 2. Double-submit CSRF token check
            # Exempt paths that cannot send CSRF headers:
            #   - login/register/forgot/reset: no auth cookie yet → no csrf cookie yet
            #   - character/create: regular HTML <form method="post"> (not AJAX),
            #     can't set X-CSRF-Token header; protected by mandatory Origin check above.
            path = request.url.path
            _CSRF_EXEMPT = {
                "/auth/login", "/auth/register",
                "/auth/forgot", "/auth/reset",
                "/auth/google", "/auth/google/callback",
                "/auth/party/create", "/auth/party/leave",
                "/auth/party/join", "/auth/logout",
                "/game/character/create",
            }
            if path not in _CSRF_EXEMPT:
                cookie_csrf = request.cookies.get("csrf_token")
                header_csrf = request.headers.get("x-csrf-token")
                if not cookie_csrf or not header_csrf or cookie_csrf != header_csrf:
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "CSRF token inválido"},
                    )
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security-related headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' wss://mezza.rednerds.com.br ws://localhost:8001; "
            "frame-ancestors 'none'"
        )
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    # Periodic cleanup of in-memory rate limiter dicts (anti memory leak)
    import asyncio as _aio
    from app.routes.game import _cleanup_rate_limiters as _cleanup_game, _cleanup_caches as _cleanup_game_caches
    from app.routes.auth import _cleanup_login_attempts as _cleanup_auth

    async def _periodic_cleanup():
        while True:
            await _aio.sleep(1800)  # 30 min
            try:
                _cleanup_game()
                _cleanup_game_caches()
                _cleanup_auth()
            except Exception as e:
                logger.warning("Erro na limpeza periódica: %s", e)

    cleanup_task = _aio.create_task(_periodic_cleanup())
    yield
    # Shutdown
    cleanup_task.cancel()


app = FastAPI(
    title="MezzaRPG Web",
    description="MezzaRPG - Campanhas Online",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── PROXY / CLOUDFLARE HEADERS ──────────────────────────────────────────────
# Trust X-Forwarded-* headers from Cloudflare (proxy)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["127.0.0.1", "::1", "localhost"])

# Trusted hosts - allow our domain + localhost for dev
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "mezza.rednerds.com.br",
        "www.mezza.rednerds.com.br",
        "localhost",
        "127.0.0.1",
    ],
)

# CORS for frontend (if needed for external access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://mezza.rednerds.com.br",
        "https://www.mezza.rednerds.com.br",
        "http://localhost:8001",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)

# Session middleware (required for OAuth)
# FIX #12 (Baixo): https_only condicional ao ambiente (quebra OAuth em dev HTTP)
_IS_PROD_SESSION = os.getenv("MEZZARPG_ENV", "dev").lower() in ("prod", "production")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, https_only=_IS_PROD_SESSION)

# CSRF: reject state-changing requests from non-allowlisted origins
# (added last so it runs outermost / first on each request)
app.add_middleware(CSRFOriginMiddleware)

# Security headers on all responses
app.add_middleware(SecurityHeadersMiddleware)

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(game.router, prefix="/game", tags=["game"])


# Root redirect to lobby or login
@app.get("/")
async def root():
    return RedirectResponse(url="/auth/login")


# Health check
@app.get("/health")
async def health():
    return {"status": "ok", "service": "mezzarpg-web"}


# F11: Global Error Handler - "Anomalia Magica Detectada!"
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    correlation_id = str(uuid.uuid4())
    # Log detalhado fica APENAS no servidor — cliente recebe mensagem genérica.
    logger.error("[ %s ] %s: %s", correlation_id, type(exc).__name__, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Anomalia Magica Detectada!",
            "message": "Ocorreu um erro inesperado. Tenta novamente.",
            "correlation_id": correlation_id,
        },
    )

# ── Endpoints de debug removidos por segurança ──────────────────────

# WebSocket endpoint with party chat and notifications
@app.websocket("/ws/{party_id}")
async def websocket_endpoint(websocket, party_id: str):
    # Authenticate the WebSocket via the JWT access_token cookie
    token = websocket.cookies.get("access_token") if websocket.cookies else None
    if not token:
        await websocket.close(code=4401)
        return
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Reject reset tokens (or any non-access type) used as access tokens
        if payload.get("type") not in (None, "access"):
            await websocket.close(code=4401)
            return
        telefone = payload.get("sub")
        if not telefone:
            await websocket.close(code=4401)
            return
    except JWTError:
        await websocket.close(code=4401)
        return

    # Validate that the authenticated user actually belongs to this party
    db = SessionLocal()
    try:
        jogador = db.query(JogadorWeb).filter(JogadorWeb.telefone == telefone).first()
        if not jogador or jogador.party_id != party_id:
            await websocket.close(code=4401)
            return
        # Guardar nome do jogador autenticado para usar no chat (anti spoofing)
        jogador_nome = jogador.nome or "Aventureiro"
    except Exception:
        db.rollback()
        await websocket.close(code=4500)
        return
    finally:
        db.close()

    if not await ws_manager.connect(party_id, websocket):
        # connect() already closed the socket (e.g. party at capacity)
        return

    # Send welcome notification to party
    try:
        await ws_manager.broadcast_json(party_id, {
            "type": "party_notification",
            "event": "player_joined",
            "message": "Um membro entrou na party!",
        })
    except Exception:
        pass

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                msg = {"type": "message", "content": data}

            msg_type = msg.get("type", "message")

            if msg_type == "chat":
                # Party chat — usa nome do JWT (não do cliente) para anti spoofing
                await ws_manager.broadcast_json(party_id, {
                    "type": "chat",
                    "jogador": jogador_nome,
                    "mensagem": str(msg.get("mensagem", data))[:500],
                })
            elif msg_type == "action":
                # Game action - broadcast to party
                await ws_manager.broadcast_json(party_id, {
                    "type": "action",
                    "jogador": jogador_nome,
                    "acao": str(msg.get("acao", ""))[:500],
                })
            else:
                # Echo back for other message types
                await ws_manager.broadcast(party_id, data)
    except Exception:
        pass
    finally:
        ws_manager.disconnect(party_id, websocket)
        try:
            await ws_manager.broadcast_json(party_id, {
                "type": "party_notification",
                "event": "player_left",
                "message": "Um membro saiu da party.",
            })
        except Exception:
            pass