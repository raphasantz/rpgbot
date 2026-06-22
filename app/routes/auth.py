"""Auth routes for MezzaRPG Web."""
from fastapi import APIRouter, Request, Response, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from urllib.parse import urlencode
import os
import secrets
import time
from collections import deque

from app.database import get_db, JogadorWeb, CampanhaWeb
from app.auth import (
    verify_password, get_password_hash, create_access_token,
    get_current_user, require_user, set_auth_cookie, clear_auth_cookie,
    create_reset_token, verify_reset_token
)
from app.ws_manager import ws_manager
from app.templates_config import templates
from app.google_oauth import oauth, GOOGLE_REDIRECT_URI, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
import string

router = APIRouter()

# ── Rate limiting for login (in-memory, per ip:email) ────────────────────────
_LOGIN_ATTEMPTS: dict = {}
_LOGIN_WINDOW = 300  # seconds — sliding window
_LOGIN_MAX = 10  # max attempts per window


def _login_rate_limit(key: str) -> bool:
    """Return True if within the limit, False if exceeded.

    Records the attempt regardless, so repeated failures keep getting rejected.
    """
    now = time.time()
    attempts = _LOGIN_ATTEMPTS.get(key)
    if attempts is None:
        attempts = deque()
        _LOGIN_ATTEMPTS[key] = attempts
    # Drop attempts outside the sliding window
    while attempts and now - attempts[0] > _LOGIN_WINDOW:
        attempts.popleft()
    if len(attempts) >= _LOGIN_MAX:
        # Still record the attempt timestamp so the window keeps sliding
        attempts.append(now)
        return False
    attempts.append(now)
    return True


def _cleanup_login_attempts() -> None:
    """Limpa entradas expiradas do dict de rate limiting de login (anti memory leak)."""
    now = time.time()
    expired = [
        k for k, attempts in _LOGIN_ATTEMPTS.items()
        if not attempts or now - attempts[-1] > _LOGIN_WINDOW * 2
    ]
    for k in expired:
        del _LOGIN_ATTEMPTS[k]


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user: JogadorWeb = Depends(get_current_user)):
    if user:
        return RedirectResponse(url="/game/lobby", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
def login(
    response: Response,
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    remember_me: bool = False,
    db: Session = Depends(get_db),
):
    # Rate limiting — reject brute-force attempts early
    ip = request.client.host if request.client else "unknown"
    if not _login_rate_limit(f"{ip}:{email}"):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Muitas tentativas. Aguarde alguns minutos."},
            status_code=429,
        )

    # Use telefone as email (simplified)
    user = db.query(JogadorWeb).filter(JogadorWeb.telefone == email).first()

    if not user or not verify_password(password, user.senha_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Credenciais inválidas"},
            status_code=401
        )

    # Create token
    token = create_access_token(data={"sub": user.telefone})
    redirect_response = RedirectResponse(url="/game/lobby", status_code=302)
    # Use remember_me to control cookie lifetime: 7 days if checked, 4 hours if not
    max_age = (60 * 60 * 24 * 7) if remember_me else (60 * 60 * 4)
    set_auth_cookie(redirect_response, token, max_age=max_age)
    # CSRF double-submit cookie (readable by JS, sent back as X-CSRF-Token header)
    _IS_PROD = os.getenv("MEZZARPG_ENV", "dev").lower() in ("prod", "production")
    csrf_token = secrets.token_hex(32)
    redirect_response.set_cookie(
        key="csrf_token", value=csrf_token,
        httponly=False, secure=_IS_PROD, samesite="strict",
        max_age=max_age, path="/",
    )

    return redirect_response


@router.get("/forgot", response_class=HTMLResponse)
def forgot_password_page(request: Request, user: JogadorWeb = Depends(get_current_user)):
    if user:
        return RedirectResponse(url="/game/lobby", status_code=302)
    return templates.TemplateResponse("forgot.html", {"request": request})


@router.post("/forgot")
def forgot_password(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db),
):
    # Find user by email
    user = db.query(JogadorWeb).filter(JogadorWeb.email == email).first()

    # Always return success to prevent email enumeration
    # But only send email if user exists
    if user:
        reset_token = create_reset_token(user.email)
        # TODO: integrar envio de email SMTP
        # NUNCA logar tokens em nenhuma circunstância.
        # send_reset_email(user.email, reset_token)

    return templates.TemplateResponse(
        "forgot.html",
        {"request": request, "success": "Se o email existir, você receberá instruções para redefinir a senha."},
    )


@router.get("/reset", response_class=HTMLResponse)
def reset_password_page(request: Request, token: str, user: JogadorWeb = Depends(get_current_user)):
    if user:
        return RedirectResponse(url="/game/lobby", status_code=302)
    
    # Verify token
    email = verify_reset_token(token)
    if not email:
        return templates.TemplateResponse(
            "reset.html",
            {"request": request, "error": "Token inválido ou expirado.", "token": None},
        )
    
    return templates.TemplateResponse("reset.html", {"request": request, "token": token, "error": None})


@router.post("/reset")
def reset_password(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_db),
):
    # Verify token
    email = verify_reset_token(token)
    if not email:
        return templates.TemplateResponse(
            "reset.html",
            {"request": request, "error": "Token inválido ou expirado.", "token": token},
            status_code=400,
        )

    # Validate passwords match
    if password != password_confirm:
        return templates.TemplateResponse(
            "reset.html",
            {"request": request, "error": "As senhas não coincidem.", "token": token},
            status_code=400,
        )

    # FIX #13 (Baixo): Política de senha mais forte (igual ao register)
    import re as _re
    if len(password) < 8:
        return templates.TemplateResponse(
            "reset.html",
            {"request": request, "error": "A senha deve ter pelo menos 8 caracteres.", "token": token},
            status_code=400,
        )
    if not _re.search(r'[A-Z]', password):
        return templates.TemplateResponse(
            "reset.html",
            {"request": request, "error": "A senha deve conter pelo menos uma letra maiúscula.", "token": token},
            status_code=400,
        )
    if not _re.search(r'[a-z]', password):
        return templates.TemplateResponse(
            "reset.html",
            {"request": request, "error": "A senha deve conter pelo menos uma letra minúscula.", "token": token},
            status_code=400,
        )
    if not _re.search(r'\d', password):
        return templates.TemplateResponse(
            "reset.html",
            {"request": request, "error": "A senha deve conter pelo menos um número.", "token": token},
            status_code=400,
        )

    # Find user and update password
    user = db.query(JogadorWeb).filter(JogadorWeb.email == email).first()

    if not user:
        # Uniform anti-enumeration response — same shape as an invalid/expired token
        return templates.TemplateResponse(
            "reset.html",
            {"request": request, "error": "Token inválido ou expirado.", "token": None},
            status_code=400,
        )

    # Update password
    user.senha_hash = get_password_hash(password)
    db.commit()

    return templates.TemplateResponse(
        "reset.html",
        {"request": request, "success": "Senha alterada com sucesso! <a href='/auth/login' class='text-gold'>Faça login</a>.", "token": None},
    )


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, user: JogadorWeb = Depends(get_current_user)):
    if user:
        return RedirectResponse(url="/game/lobby", status_code=302)
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register")
def register(
    response: Response,
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(...),
    db: Session = Depends(get_db),
):
    # FIX #1 (Crítico): Sanitizar display_name contra stored XSS
    from game_helpers import sanitize_user_text
    display_name = sanitize_user_text(display_name, max_len=50)
    if not display_name:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Nome inválido"},
            status_code=400
        )

    # Check if exists
    existing = db.query(JogadorWeb).filter(JogadorWeb.telefone == email).first()
    if existing:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Email já cadastrado"},
            status_code=400
        )

    # FIX #13 (Baixo): Política de senha mais forte
    import re as _re
    if len(password) < 8:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "A senha deve ter pelo menos 8 caracteres."},
            status_code=400,
        )
    if not _re.search(r'[A-Z]', password):
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "A senha deve conter pelo menos uma letra maiúscula."},
            status_code=400,
        )
    if not _re.search(r'[a-z]', password):
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "A senha deve conter pelo menos uma letra minúscula."},
            status_code=400,
        )
    if not _re.search(r'\d', password):
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "A senha deve conter pelo menos um número."},
            status_code=400,
        )

    # Create user with proper fields
    hashed_pw = get_password_hash(password)
    user = JogadorWeb(
        telefone=email,
        email=email,  # Also save to email field
        nome=display_name,  # Save display_name as nome
        senha_hash=hashed_pw,  # Save password hash in senha_hash
        classe="Aventureiro",
        raca="Humano",
        background="Forasteiro",
        nivel=1,
        xp=0,
        hp_atual=10,
        hp_maximo=10,
        str_val=10, dex_val=10, con_val=10, int_val=10, wis_val=10, cha_val=10,
        mod_str=0, mod_dex=0, mod_con=0, mod_int=0, mod_wis=0, mod_cha=0,
        modificador_ataque=0,
        modificador_defesa=10,
        proficiencia=2,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create token
    token = create_access_token(data={"sub": user.telefone})
    redirect_response = RedirectResponse(url="/game/character/create", status_code=302)
    set_auth_cookie(redirect_response, token)

    return redirect_response


@router.post("/logout")
def logout():
    redirect_response = RedirectResponse(url="/auth/login", status_code=302)
    clear_auth_cookie(redirect_response)
    return redirect_response


@router.get("/party/create", response_class=HTMLResponse)
def create_party_page(request: Request, user: JogadorWeb = Depends(require_user)):
    return templates.TemplateResponse("party_create.html", {"request": request, "user": user})


@router.post("/party/create")
def create_party(
    request: Request,
    user: JogadorWeb = Depends(require_user),
    db: Session = Depends(get_db),
):
    # Check if user is already in a party
    if user.party_id:
        return templates.TemplateResponse(
            "party_create.html",
            {"request": request, "user": user, "error": f"Você já está na party {user.party_id}. Saia dela primeiro para criar uma nova."},
            status_code=400
        )

    # Generate party code (cryptographically secure, 8 chars)
    _codigo_chars = string.ascii_uppercase + string.digits
    codigo = ''.join(secrets.choice(_codigo_chars) for _ in range(8))
    party_id = f"PTY-{codigo}"

    # Update user
    user.party_id = party_id

    # Create campaign
    campanha = CampanhaWeb(
        party_id=party_id,
        host_id=user.telefone,
        cena_atual="taverna",
        estado_salas={},
        momento="inicio",
        tensao=0,
        turno_atual=1,
    )
    db.add(campanha)
    db.commit()

    return RedirectResponse(url=f"/game/jogar/{party_id}", status_code=302)


@router.get("/party/join", response_class=HTMLResponse)
def join_party_page(request: Request, user: JogadorWeb = Depends(require_user)):
    return templates.TemplateResponse("party_join.html", {"request": request, "user": user})


@router.post("/party/join")
def join_party(
    request: Request,
    party_id: str = Form(...),
    user: JogadorWeb = Depends(require_user),
    db: Session = Depends(get_db),
):
    party_id = party_id.upper().strip()
    if not party_id.startswith("PTY-"):
        party_id = f"PTY-{party_id}"

    # Check campaign exists
    campanha = db.query(CampanhaWeb).filter(CampanhaWeb.party_id == party_id).first()
    if not campanha:
        return templates.TemplateResponse(
            "party_join.html",
            {"request": request, "user": user, "error": "Party não encontrada"},
            status_code=404
        )

    # Check if user already in party
    if user.party_id == party_id:
        return RedirectResponse(url=f"/game/jogar/{party_id}", status_code=302)

    # Check party size
    membros = db.query(JogadorWeb).filter(JogadorWeb.party_id == party_id).all()
    if len(membros) >= 5:
        return templates.TemplateResponse(
            "party_join.html",
            {"request": request, "user": user, "error": "Party cheia (máx 5)"},
            status_code=400
        )

    # Join party
    user.party_id = party_id
    user.cena_atual = campanha.cena_atual

    # F6: XP auto-level - ajustar nível para média do grupo
    if membros:
        nivel_medio = sum((m.nivel or 1) for m in membros) / len(membros)
        nivel_medio_arredondado = round(nivel_medio)
        if nivel_medio_arredondado > (user.nivel or 1):
            from game_helpers import aplicar_level_up
            # Aplicar level-ups até alcançar a média do grupo
            aplicar_level_up(user, forcar_ate=nivel_medio_arredondado)

    db.commit()

    return RedirectResponse(url=f"/game/jogar/{party_id}", status_code=302)


@router.post("/party/leave")
def leave_party(
    request: Request,
    user: JogadorWeb = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Leave current party."""
    if not user.party_id:
        return RedirectResponse(url="/auth/party/create", status_code=302)
    
    party_id = user.party_id
    # If user is host, transfer or delete the campaign
    campanha = db.query(CampanhaWeb).filter(CampanhaWeb.party_id == party_id).first()
    if campanha and campanha.host_id == user.telefone:
        # Find remaining members (excluding the leaving user)
        outros = db.query(JogadorWeb).filter(
            JogadorWeb.party_id == party_id,
            JogadorWeb.telefone != user.telefone,
        ).all()
        if outros:
            # Transfer host to the first remaining member
            campanha.host_id = outros[0].telefone
        else:
            # Last member leaving — delete the campaign
            db.delete(campanha)
    
    # Remove user from party
    user.party_id = None
    user.cena_atual = "taverna"
    db.commit()
    
    return RedirectResponse(url="/auth/party/create", status_code=302)


from ui_utils import XP_POR_NIVEL

@router.get("/me", response_class=HTMLResponse)
def me_page(request: Request, user: JogadorWeb = Depends(require_user)):
    return templates.TemplateResponse("me.html", {"request": request, "user": user, "xp_por_nivel": XP_POR_NIVEL})


# ============================================================
# Google OAuth2 Routes (kept async for authlib compatibility)
# ============================================================

@router.get("/google")
async def google_login(request: Request):
    """
    Initiate Google OAuth2 flow.
    Redirects user to Google consent screen.
    """
    redirect_uri = GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """
    Handle Google OAuth2 callback.
    Creates or links user, sets JWT cookie, redirects to character creation or lobby.
    """
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        # FIX #10 (Médio): Não vazar detalhes de exceção na URL
        import logging as _log
        _log.getLogger("mezzarpg.auth").warning("[OAUTH] Falha no callback Google: %s", e)
        return RedirectResponse(
            url="/auth/login?error=google_falha",
            status_code=302
        )

    # Get user info from Google
    user_info = token.get('userinfo')
    if not user_info:
        # Fallback: fetch from userinfo endpoint
        resp = await oauth.google.get('https://www.googleapis.com/oauth2/v3/userinfo', token=token)
        user_info = resp.json()

    google_id = user_info.get('sub')
    email = user_info.get('email')
    name = user_info.get('name', '')
    picture = user_info.get('picture', '')
    email_verified = user_info.get('email_verified', False)

    if not google_id or not email:
        return RedirectResponse(
            url="/auth/login?error=google_incomplete_profile",
            status_code=302
        )

    if not email_verified:
        return RedirectResponse(
            url="/auth/login?error=google_email_not_verified",
            status_code=302
        )

    # Check if user exists with this google_id
    user = db.query(JogadorWeb).filter(JogadorWeb.google_id == google_id).first()

    if user:
        # Existing Google user — update avatar if changed
        if picture and user.avatar_url != picture:
            user.avatar_url = picture
            db.commit()
    else:
        # Check if email exists with local account
        user = db.query(JogadorWeb).filter(JogadorWeb.telefone == email).first()

        if user:
            # Existing local account — only link if google_id already set;
            # otherwise require password confirmation (no auto-linking).
            if not user.google_id:
                return RedirectResponse(
                    url=f"/auth/login?error=conta_existente_confirme_senha&email={email}",
                    status_code=302,
                )
            user.google_id = google_id
            if picture:
                user.avatar_url = picture
            db.commit()
        else:
            # Create new user via Google
            # FIX #1 (Crítico): Sanitizar name do Google contra stored XSS
            from game_helpers import sanitize_user_text
            name = sanitize_user_text(name or email.split('@')[0], max_len=50)
            user = JogadorWeb(
                telefone=email,
                senha_hash=get_password_hash(secrets.token_urlsafe(32)),  # Random password, never used
                nome=name,
                google_id=google_id,
                avatar_url=picture,
                cena_atual="taverna",
                classe="Aventureiro",
                raca="Humano",
                background="Forasteiro",
                nivel=1,
                xp=0,
                hp_atual=10,
                hp_maximo=10,
                str_val=10, dex_val=10, con_val=10, int_val=10, wis_val=10, cha_val=10,
                mod_str=0, mod_dex=0, mod_con=0, mod_int=0, mod_wis=0, mod_cha=0,
                modificador_ataque=0,
                modificador_defesa=10,
                proficiencia=2,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

    # Create JWT token (reuse existing create_access_token)
    access_token = create_access_token(data={"sub": user.telefone})

    # Check if user has character (simplified - just check if they have a class set beyond default)
    # For now, always go to lobby since we auto-create party on character creation

    redirect_url = "/game/lobby"

    response = RedirectResponse(url=redirect_url, status_code=302)
    _IS_PROD = os.getenv("MEZZARPG_ENV", "dev").lower() in ("prod", "production")
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=_IS_PROD,  # True in production with HTTPS
        samesite="lax",
        max_age=60 * 60 * 24 * 7,  # 7 days
        path="/",
    )
    # CSRF double-submit cookie
    csrf_token = secrets.token_hex(32)
    response.set_cookie(
        key="csrf_token", value=csrf_token,
        httponly=False, secure=_IS_PROD, samesite="strict",
        max_age=60 * 60 * 24 * 7, path="/",
    )
    return response