"""
Game routes for MezzaRPG Web - usa ActionResolver completo (engine D&D 5e).
Substitui a versão simplificada pela lógica completa do rpg_bot.
"""
import logging
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import asyncio
import math
import secrets

logger = logging.getLogger("mezzarpg.game")

# ── ENGINE COMPLETA ────────────────────────────────────────────────────────
from action_resolver import ActionResolver, ActionResult
from mapa_engine import extrair_direcao_sync
from modelos_web import (
    JogadorWeb, CampanhaWeb, Cena, Npc,
    get_db, jogador_to_dict,
)
from db_loader import get_cena, get_inimigo, get_npc_da_cena, get_encontros_vivos
from imagens_config import url_para
from ui_utils import XP_POR_NIVEL
from game_helpers import set_status_efeitos, set_inventario
from app.auth import require_user, get_current_user
from app.ws_manager import ws_manager
from app.templates_config import templates
from sqlalchemy.orm import Session
from sqlalchemy import select

# ── IA NARRAÇÃO ─────────────────────────────────────────────────────────────
from ai_engine_web import (
    narrar_combate, narrar_ambiente, interpretar_acao_json,
    decidir_atributo_teste, extrair_itens_da_narracao,
    gerar_imagem_sala, gerar_imagem_critica,
)

router = APIRouter()

# F12: Party Lock - Concorrência: uma ação por vez por party
PARTY_LOCKS: Dict[str, asyncio.Lock] = {}

def get_party_lock(party_id: str) -> asyncio.Lock:
    if party_id not in PARTY_LOCKS:
        PARTY_LOCKS[party_id] = asyncio.Lock()
    return PARTY_LOCKS[party_id]

# ── RATE LIMITER simples (evita spam de chamadas OpenAI) ──────────────────
from collections import defaultdict, deque
import time

_ACTION_TIMESTAMPS: Dict[str, deque] = defaultdict(deque)
_RATE_LIMIT_WINDOW = 60  # segundos
_RATE_LIMIT_MAX = 12     # máx 12 ações/min por jogador (combate + narração)
_last_cleanup: float = 0.0
_CLEANUP_INTERVAL = 300   # limpar a cada 5 minutos

def _check_rate_limit(telefone: str) -> bool:
    """Retorna True se o jogador pode agir, False se excedeu o limite."""
    global _last_cleanup
    now = time.time()

    # Limpeza periódica automática (a cada 5 min)
    if now - _last_cleanup > _CLEANUP_INTERVAL:
        _last_cleanup = now
        _cleanup_rate_limiters()

    timestamps = _ACTION_TIMESTAMPS[telefone]
    # Remove timestamps antigos
    while timestamps and now - timestamps[0] > _RATE_LIMIT_WINDOW:
        timestamps.popleft()
    if len(timestamps) >= _RATE_LIMIT_MAX:
        return False
    timestamps.append(now)
    return True


def _cleanup_rate_limiters() -> None:
    """Limpa entradas expiradas dos dicts de rate limiting e party locks."""
    now = time.time()
    # Limpar timestamps antigos de _ACTION_TIMESTAMPS
    expired_action = [
        k for k, ts in _ACTION_TIMESTAMPS.items()
        if not ts or now - ts[-1] > _RATE_LIMIT_WINDOW * 2
    ]
    for k in expired_action:
        del _ACTION_TIMESTAMPS[k]
    # Limpar party locks nao travados (parties inativas)
    inactive = [pid for pid, lk in PARTY_LOCKS.items() if not lk.locked()]
    for pid in inactive:
        del PARTY_LOCKS[pid]
    # Limpar shop locks não travados (usuários inativos)
    inactive_shops = [k for k, lk in _SHOP_USER_LOCKS.items() if not lk.locked()]
    for k in inactive_shops:
        del _SHOP_USER_LOCKS[k]


# ════════════════════════════════════════════════════════════════════════
# HELPERS DE CACHE E CONVERSÃO
# ════════════════════════════════════════════════════════════════════════

import time as _time_mod

# Cache TTL simples: chave -> (timestamp, valor)
_CENA_CACHE: Dict[str, tuple] = {}
_INIMIGO_CACHE: Dict[str, tuple] = {}
_NPC_CACHE: Dict[str, tuple] = {}
_CACHE_TTL = 60  # segundos


def _cache_get(cache: dict, key: str) -> Optional[Any]:
    """Retorna valor do cache se ainda válido, senão None."""
    entry = cache.get(key)
    if entry and (_time_mod.time() - entry[0]) < _CACHE_TTL:
        return entry[1]
    return None


def _cache_set(cache: dict, key: str, value: Any) -> None:
    """Armazena valor no cache com timestamp atual."""
    cache[key] = (_time_mod.time(), value)


def _cleanup_caches() -> None:
    """Remove entradas expiradas de todos os caches (chamado periodicamente)."""
    now = _time_mod.time()
    for cache in (_CENA_CACHE, _INIMIGO_CACHE, _NPC_CACHE):
        expired = [k for k, (ts, _) in cache.items() if now - ts > _CACHE_TTL * 2]
        for k in expired:
            del cache[k]


def get_cena_cached_sync(cod_sala: str, db: Optional[Session] = None) -> Optional[Dict[str, Any]]:
    # 1. Cache em memória (TTL 60s)
    cached = _cache_get(_CENA_CACHE, cod_sala)
    if cached is not None:
        return cached

    # 2. PostgreSQL (fonte canônica) — usa sessão fornecida ou cria nova
    own_db = db is None
    if own_db:
        from modelos_web import SessionLocal
        db = SessionLocal()
    try:
        from modelos_web import Cena as CenaModel
        db_cena = db.query(CenaModel).filter(CenaModel.cod_sala == cod_sala).first()
        if db_cena:
            resultado = {
                'cod_sala': db_cena.cod_sala,
                'nome_sala': db_cena.nome_sala,
                'descricao_visual': db_cena.descricao_visual,
                'conexoes': db_cena.conexoes or {},
                'loot_fixo': db_cena.loot_fixo or [],
                'hazards': db_cena.hazards or [],
                'imagem_url': db_cena.imagem_url or '',
            }
            _cache_set(_CENA_CACHE, cod_sala, resultado)
            return resultado
    except Exception:
        if own_db:
            db.rollback()
        raise
    finally:
        if own_db:
            db.close()
    # 3. Fallback: JSON (db_loader)
    cena = get_cena(cod_sala)
    if cena:
        _cache_set(_CENA_CACHE, cod_sala, cena)
        return cena
    return None


def get_inimigo_cached_sync(nome: str, db: Optional[Session] = None) -> Optional[Dict[str, Any]]:
    # 1. Cache em memória
    cached = _cache_get(_INIMIGO_CACHE, nome)
    if cached is not None:
        return cached

    # 2. PostgreSQL
    own_db = db is None
    if own_db:
        from modelos_web import SessionLocal
        db = SessionLocal()
    try:
        from modelos_web import Inimigo as InimigoModel
        inimigo = db.query(InimigoModel).filter(InimigoModel.nome == nome).first()
        if inimigo:
            resultado = {
                'nome': inimigo.nome,
                'hp_max': inimigo.hp_max,
                'ca': inimigo.ca,
                'ataque': inimigo.ataque,
                'dano': inimigo.dano,
                'xp_recompensa': inimigo.xp_recompensa,
                'ouro_recompensa': inimigo.ouro_recompensa,
                'is_boss': inimigo.is_boss,
                'loot_especial': inimigo.loot_especial or [],
                'resistencias': inimigo.resistencias or [],
                'vulnerabilidades': inimigo.vulnerabilidades or [],
                'imunidades': inimigo.imunidades or [],
            }
            _cache_set(_INIMIGO_CACHE, nome, resultado)
            return resultado
    except Exception:
        if own_db:
            db.rollback()
        raise
    finally:
        if own_db:
            db.close()
    # 3. Fallback: JSON
    resultado = get_inimigo(nome)
    if resultado:
        _cache_set(_INIMIGO_CACHE, nome, resultado)
    return resultado


def get_npc_da_cena_cached_sync(cod_sala: str, db: Optional[Session] = None) -> List[Dict[str, Any]]:
    """Retorna TODOS os NPCs da sala — busca no banco SQLAlchemy primeiro,
    faz fallback para o db_loader (JSON) se necessário."""
    # 1. Cache em memória
    cached = _cache_get(_NPC_CACHE, cod_sala)
    if cached is not None:
        return cached

    # 2. Banco SQLAlchemy (tabela Npc) — fonte canônica
    own_db = db is None
    if own_db:
        from modelos_web import SessionLocal
        db = SessionLocal()
    try:
        from modelos_web import Npc as NpcModel
        npcs_db = db.query(NpcModel).filter(NpcModel.cod_sala == cod_sala).all()
        resultado = [
            {
                "id": n.id,
                "nome": n.nome,
                "descricao": n.descricao or "",
                "dialogo_base": n.dialogo_base or "",
                "dialogo_item_especial": n.dialogo_item_especial or "",
                "item_gatilho": n.item_gatilho or "",
                "cod_sala": n.cod_sala,
            }
            for n in npcs_db
        ]
    except Exception as e:
        if own_db:
            db.rollback()
        logger.warning("[NPC] Erro ao buscar no banco: %s", e)
        resultado = None
    finally:
        if own_db:
            db.close()

    if resultado:
        _cache_set(_NPC_CACHE, cod_sala, resultado)
        return resultado

    # 3. Fallback: db_loader (JSON em memória)
    npc = get_npc_da_cena(cod_sala)
    fallback = [npc] if npc else []
    _cache_set(_NPC_CACHE, cod_sala, fallback)
    return fallback


def get_encontros_vivos_sync(cod_sala: str, estado_salas: Dict[str, Any], db: Optional[Session] = None) -> List[Dict[str, Any]]:
    """Busca encontros ativos da sala no banco SQLAlchemy e cruza com o bestiário
    para retornar o formato completo que a UI espera:
    {nome, hp_atual, hp_max, ca, quantidade}."""
    # Não usa cache TTL: estado_salas muda dinamicamente durante combate
    own_db = db is None
    if own_db:
        from modelos_web import SessionLocal
        db = SessionLocal()
    try:
        from modelos_web import Encontro as EncontroModel, Inimigo as InimigoModel
        encontros = db.query(EncontroModel).filter(
            EncontroModel.cod_sala == cod_sala,
            EncontroModel.ativo.is_(True),
        ).all()

        resultado = []
        for enc in encontros:
            if estado_salas.get(f"derrotado_{enc.id}"):
                continue
            inimigo = db.query(InimigoModel).filter(InimigoModel.nome == enc.nome_inimigo).first()
            if not inimigo:
                logger.warning("[ENCONTRO] Inimigo '%s' não encontrado no bestiário", enc.nome_inimigo)
                continue
            hp_max = inimigo.hp_max or 10
            chave_hp = f"hp_{enc.id}"
            hp_grupo = estado_salas.get(chave_hp, hp_max * enc.quantidade)
            resultado.append({
                "id": enc.id,
                "nome": enc.nome_inimigo,
                "hp_atual": hp_grupo,
                "hp_max": hp_max,
                "ca": inimigo.ca or 10,
                "quantidade": enc.quantidade,
                "multiplicador_ameaca": getattr(enc, "multiplicador_ameaca", 1) or 1,
                "is_boss": getattr(inimigo, "is_boss", False),
            })
        return resultado
    except Exception as e:
        if own_db:
            db.rollback()
        logger.warning("[ENCONTROS] Erro ao buscar no banco: %s", e)
        return []
    finally:
        if own_db:
            db.close()


# ════════════════════════════════════════════════════════════════════════
# ROTAS PRINCIPAIS (Lobby, Character Create, Jogo)
# ════════════════════════════════════════════════════════════════════════

@router.get("/lobby", response_class=HTMLResponse)
def lobby(request: Request, user: JogadorWeb = Depends(require_user), db: Session = Depends(get_db)):
    campanha = None
    if user.party_id:
        campanha = db.query(CampanhaWeb).filter(CampanhaWeb.party_id == user.party_id).first()

    return templates.TemplateResponse("lobby.html", {
        "request": request,
        "user": user,
        "campanha": campanha,
        "xp_por_nivel": XP_POR_NIVEL
    })


@router.get("/character/create", response_class=HTMLResponse)
def character_create_page(request: Request, user: JogadorWeb = Depends(get_current_user)):
    return templates.TemplateResponse("character_create.html", {"request": request, "user": user, "current_step": 1})


@router.post("/character/create")
def character_create(
    request: Request,
    # FIX #8 (Médio): Limitar comprimento do nome no Form (anti payload gigante)
    nome: str = Form(..., max_length=50),
    sexo: str = Form(...),
    raca: str = Form(...),
    classe: str = Form(...),
    background: str = Form(...),
    str_val: int = Form(..., ge=3, le=20),
    dex_val: int = Form(..., ge=3, le=20),
    con_val: int = Form(..., ge=3, le=20),
    int_val: int = Form(..., ge=3, le=20),
    wis_val: int = Form(..., ge=3, le=20),
    cha_val: int = Form(..., ge=3, le=20),
    user: JogadorWeb = Depends(require_user),
    db: Session = Depends(get_db),
):
    from ui_utils import (
        BONUS_RACA, HP_POR_CLASSE, INVENTARIO_POR_CLASSE,
        LOJA_CARVALHAL, ARMAS_DB, calcular_modificadores_ataque, calcular_ca_final,
    )

    # Whitelists — reject invalid values (derived from game data)
    # FIX #1 (Crítico): Sanitizar nome do personagem contra stored XSS
    from game_helpers import sanitize_user_text
    nome = sanitize_user_text(nome, max_len=50)
    if not nome:
        raise HTTPException(status_code=400, detail="Nome de personagem inválido")

    _racas_validas = set(BONUS_RACA.keys())
    _classes_validas = set(HP_POR_CLASSE.keys())
    if raca not in _racas_validas:
        raise HTTPException(status_code=400, detail=f"Raça inválida: {raca}")
    if classe not in _classes_validas:
        raise HTTPException(status_code=400, detail=f"Classe inválida: {classe}")
    from ui_utils import BACKGROUND_SKILLS
    _backgrounds_validos = set(BACKGROUND_SKILLS.keys())
    if background not in _backgrounds_validos:
        raise HTTPException(status_code=400, detail=f"Background inválido: {background}")

    mods = {k: (v - 10) // 2 for k, v in {
        "STR": str_val, "DEX": dex_val, "CON": con_val,
        "INT": int_val, "WIS": wis_val, "CHA": cha_val
    }.items()}

    bonus_raca = BONUS_RACA.get(raca, [0, 0, 0, 0, 0, 0])
    attrs_final = [str_val + bonus_raca[0], dex_val + bonus_raca[1], con_val + bonus_raca[2],
                   int_val + bonus_raca[3], wis_val + bonus_raca[4], cha_val + bonus_raca[5]]
    mods_final = [(v - 10) // 2 for v in attrs_final]

    hp_base = HP_POR_CLASSE.get(classe, 8)
    hp_max = hp_base + mods_final[2]  # CON

    inv = INVENTARIO_POR_CLASSE.get(classe, ["Adaga", "Tochas", "Rações"])
    arma_inicial = next((i for i in inv if any(a.lower() in i.lower() for a in 
                        ["espada", "adaga", "machado", "maça", "lança", "bastão", "clava", "foice", "martelo", "azagaia", "arco", "besta", "dardo"])), "Desarmado")
    armadura_inicial = next((i for i in inv if any(x in i for x in ["Armadura", "Cota", "Peitoral", "Couro", "Escudo"])), "Trajes Comuns")

    ca_base = 10 + mods_final[1]  # DEX
    if classe in ["Guerreiro", "Paladino", "Clérigo"]:
        ca_base = 16 if "Cota" in armadura_inicial or "Peitoral" in armadura_inicial else 14
    elif classe in ["Patrulheiro", "Ladino", "Bárbaro"]:
        ca_base = 11 + mods_final[1]

    mod_ataque = (mods_final[1] + 2 if classe in ["Ladino", "Bardo", "Monge", "Patrulheiro"] else mods_final[0] + 2)
    mod_dano = (mods_final[1] if classe in ["Ladino", "Bardo", "Monge", "Patrulheiro"] else mods_final[0])

    slots = 2 if classe in ["Bardo", "Bruxo", "Clérigo", "Druida", "Feiticeiro", "Mago", "Paladino", "Patrulheiro", "Artífice"] else 0

    # Atualiza user
    user.nome = nome
    user.sexo = sexo
    user.raca = raca
    user.classe = classe
    user.background = background
    user.str_val, user.dex_val, user.con_val = attrs_final[0], attrs_final[1], attrs_final[2]
    user.int_val, user.wis_val, user.cha_val = attrs_final[3], attrs_final[4], attrs_final[5]
    user.mod_str, user.mod_dex, user.mod_con = mods_final[0], mods_final[1], mods_final[2]
    user.mod_int, user.mod_wis, user.mod_cha = mods_final[3], mods_final[4], mods_final[5]
    user.nivel = 1
    user.xp = 0
    user.hp_maximo = hp_max
    user.hp_atual = hp_max
    user.modificador_ataque = mod_ataque
    user.modificador_defesa = ca_base
    user.proficiencia = 2
    user.gold = 15
    set_inventario(user, inv)
    user.arma_equipada = arma_inicial
    user.armadura_equipada = armadura_inicial
    user.dano_dado = "1d12" if classe == "Bárbaro" else "1d10" if classe in ["Guerreiro", "Paladino"] else "1d8" if classe in ["Patrulheiro", "Ladino", "Clérigo", "Bardo", "Monge", "Druida", "Bruxo", "Feiticeiro", "Artífice"] else "1d6"
    user.mod_dano = mod_dano
    user.slots_magia = slots
    user.slots_magia_max = slots
    user.hit_dice_max = 1
    user.hit_dice_atual = 1
    set_status_efeitos(user, [])
    user.cena_atual = "taverna"
    user.cena_anterior = None

    db.commit()

    # Cria party automática
    import string
    _codigo_chars = string.ascii_uppercase + string.digits
    codigo = ''.join(secrets.choice(_codigo_chars) for _ in range(8))
    party_id = f"PTY-{codigo}"
    user.party_id = party_id

    campanha = CampanhaWeb(
        party_id=party_id, host_id=user.telefone,
        cena_atual="taverna", estado_salas={},
        momento="inicio", tensao=0, turno_atual=1
    )
    db.add(campanha)
    db.commit()

    return RedirectResponse(url=f"/game/jogar/{party_id}", status_code=302)


@router.get("/jogar/{party_id}", response_class=HTMLResponse)
def jogar(
    request: Request,
    party_id: str,
    user: JogadorWeb = Depends(require_user),
    db: Session = Depends(get_db),
):
    party_id = party_id.upper()

    if user.party_id != party_id:
        raise HTTPException(status_code=403, detail="Você não está nesta party")

    campanha = db.query(CampanhaWeb).filter(CampanhaWeb.party_id == party_id).first()
    if not campanha:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    membros = db.query(JogadorWeb).filter(JogadorWeb.party_id == party_id).all()

    cena_data = get_cena_cached_sync(campanha.cena_atual, db=db)
    npcs = get_npc_da_cena_cached_sync(campanha.cena_atual, db=db)
    inimigos_vivos = get_encontros_vivos_sync(campanha.cena_atual, campanha.estado_salas, db=db)

    # Build destination names lookup — batch query para evitar N+1
    destino_nomes = {}
    if cena_data:
        conexoes = cena_data.get("conexoes", {})
        dest_codigos = list(conexoes.values())
        # Primeiro tenta buscar do cache (TTL) para cada destino
        dest_nomes_map = {}
        dest_faltam = []
        for dest_code in dest_codigos:
            cached = _cache_get(_CENA_CACHE, dest_code)
            if cached is not None:
                dest_nomes_map[dest_code] = cached.get("nome_sala", dest_code)
            else:
                dest_faltam.append(dest_code)
        # Busca em batch os que não estão no cache
        if dest_faltam:
            from modelos_web import Cena as CenaModel
            cenas_db = db.query(CenaModel).filter(
                CenaModel.cod_sala.in_(dest_faltam)
            ).all()
            for c in cenas_db:
                nome = c.nome_sala or c.cod_sala
                dest_nomes_map[c.cod_sala] = nome
                # Popula o cache também
                _cache_set(_CENA_CACHE, c.cod_sala, {
                    'cod_sala': c.cod_sala, 'nome_sala': c.nome_sala,
                    'descricao_visual': c.descricao_visual,
                    'conexoes': c.conexoes or {}, 'loot_fixo': c.loot_fixo or [],
                    'hazards': c.hazards or [], 'imagem_url': c.imagem_url or '',
                })
        # Monta o dict final na ordem das conexões
        for direcao, dest_code in conexoes.items():
            destino_nomes[direcao] = {
                "codigo": dest_code,
                "nome": dest_nomes_map.get(dest_code, dest_code),
            }

    game_state = {
        "party_id": party_id,
        "user": {
            "telefone": user.telefone,
            "nome": user.nome,
            "hp_atual": user.hp_atual,
            "hp_maximo": user.hp_maximo,
            "ca": user.modificador_defesa,
            "modificador_ataque": user.modificador_ataque,
            "gold": user.gold,
            "inventario": user.inventario,
            "classe": user.classe,
            "nivel": user.nivel or 1,
            "slots_magia": user.slots_magia,
            "slots_magia_max": user.slots_magia_max,
        },
        "campanha": {
            "cena_atual": campanha.cena_atual,
            "cena_nome": cena_data.get("nome_sala", campanha.cena_atual) if cena_data else campanha.cena_atual,
            "cena_descricao": cena_data.get("descricao_visual", "") if cena_data else "",
            "cena_imagem": url_para("cena", campanha.cena_atual),
            "conexoes": conexoes if cena_data else {},
            "destino_nomes": destino_nomes,
            "momento": campanha.momento,
            "tensao": campanha.tensao,
            "turno_atual": campanha.turno_atual,
            "em_combate": campanha.em_combate,
            "estado_salas": campanha.estado_salas,
        },
        "membros": [
            {
                "telefone": m.telefone,
                "nome": m.nome,
                "hp_atual": m.hp_atual,
                "hp_maximo": m.hp_maximo,
                "ca": m.modificador_defesa,
                "classe": m.classe,
                "raca": m.raca,
                "nivel": m.nivel or 1,
                "xp": m.xp or 0,
                "gold": m.gold or 0,
                "arma_equipada": m.arma_equipada,
                "armadura_equipada": m.armadura_equipada,
                "status_efeitos": list(m.status_efeitos) if m.status_efeitos else [],
                "slots_magia": m.slots_magia or 0,
                "slots_magia_max": m.slots_magia_max or 0,
                "is_host": m.telefone == campanha.host_id,
                "cena_atual": m.cena_atual,
            }
            for m in membros
        ],
        "npcs": [
            {
                "id": n.get("id") or n.get("nome"),
                "nome": n.get("nome", ""),
                "descricao": n.get("descricao", ""),
                "imagem": url_para("npc", n.get("nome", "")),
            }
            for n in npcs if n
        ],
        "inimigos": [
            {
                "nome": e["nome"],
                "hp_atual": e["hp_atual"],
                "hp_max": e["hp_max"],
                "ca": e["ca"],
                "quantidade": e["quantidade"],
                "imagem": url_para("inimigo", e["nome"]),
            }
            for e in inimigos_vivos
        ],
    }

    # F15: Link de compartilhamento da party
    share_url = f"{request.base_url}auth/party/join?party_id={party_id}"
    game_state["share_url"] = share_url
    game_state["share_text"] = f"Entra na minha party no MezzaRPG! Código: {party_id}\n{share_url}"

    return templates.TemplateResponse("jogo.html", {"request": request, **game_state})


# ════════════════════════════════════════════════════════════════════════
# F9: CLASS TIPS — Dicas por classe na criação de personagem
# ════════════════════════════════════════════════════════════════════════

CLASS_TIPS = {
    "Bárbaro": "🪓 Tanque bruto com Fúria. HP alto, dano pesado. Ataca sem armadura boa. Ideal para frente de batalha.",
    "Bardo": "🎵 Suporte versátil. Magia + social. Buffa aliados, debilita inimigos. Perícias vastas.",
    "Bruxo": "🔮 Magia pactuada. Poder constante com cantrips fortes. Invocador de patronos arcanos.",
    "Clérigo": "✝️ Curador e tanque sagrado. Cura, protege e sustenta o grupo. essencial em qualquer party.",
    "Druida": "🌿 Natureza e transformação. Curandeiro, invocador de animais. Versátil em exploração.",
    "Feiticeiro": "🔥 Magia innata e caótica. Metamagia para flexibilidade. Dano elemental explosivo.",
    "Guerreiro": "⚔️ Soldado clássico. Alta CA, boa versatilidade. Adapta-se a qualquer arma e estilo.",
    "Ladino": "🗡️ Ataque furtivo e golpes críticos. Abre tranca, desativa armadilhas. DPS silencioso.",
    "Mago": "📚 Mestre do arcane. Maior poder ofensivo. Precisa planejar magias. Frágil mas devastador.",
    "Monge": "👊 Artes marciais + ki. Rápido, esquiva, ataque desarmado. Exploração excepcional.",
    "Paladino": "🛡️ Cavaleiro sagrado. Tanque + cura + dano divino. Resistências poderosas.",
    "Patrulheiro": "🏹 Caçador e rastreador. Arco + magia de natureza. Excelente em exploração e furtividade.",
}


@router.get("/api/class-tips")
async def api_class_tips(classe: str = ""):
    """Retorna dicas para a classe escolhida."""
    tip = CLASS_TIPS.get(classe, "Escolhe uma classe para ver dicas.")
    return JSONResponse({"classe": classe, "tip": tip})


@router.get("/api/class-tips/all")
async def api_class_tips_all():
    """Retorna todas as dicas de classes."""
    return JSONResponse({"tips": CLASS_TIPS})


# ════════════════════════════════════════════════════════════════════════
# LOJA DO CARVALHAL
# ════════════════════════════════════════════════════════════════════════

@router.get("/shop", response_class=HTMLResponse)
def shop_page(
    request: Request,
    user: JogadorWeb = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Página da Loja do Carvalhal."""
    from ui_utils import LOJA_CARVALHAL
    
    # Organizar itens por tipo
    itens_por_tipo = {}
    for nome, dados in LOJA_CARVALHAL.items():
        tipo = dados.get("tipo", "outros")
        if tipo not in itens_por_tipo:
            itens_por_tipo[tipo] = []
        itens_por_tipo[tipo].append({"nome": nome, **dados})
    
    # Ordem de exibição
    ordem_tipos = ["pocao", "arma", "armadura", "equipamento", "outros"]
    tipos_ordenados = [(t, itens_por_tipo.get(t, [])) for t in ordem_tipos if t in itens_por_tipo]
    # Adicionar tipos não listados
    for t, itens in itens_por_tipo.items():
        if t not in ordem_tipos:
            tipos_ordenados.append((t, itens))
    
    return templates.TemplateResponse("shop.html", {
        "request": request,
        "user": user,
        "tipos_ordenados": tipos_ordenados,
        "gold": user.gold,
    })


# CRIT-01 FIX: Per-user lock evita race condition em compras simultâneas
_SHOP_USER_LOCKS: Dict[str, asyncio.Lock] = {}
def _get_shop_lock(telefone: str) -> asyncio.Lock:
    if telefone not in _SHOP_USER_LOCKS:
        _SHOP_USER_LOCKS[telefone] = asyncio.Lock()
    return _SHOP_USER_LOCKS[telefone]

@router.post("/shop/buy")
async def shop_buy(
    request: Request,
    item_nome: str = Form(...),
    quantidade: int = Form(1, gt=0, le=99),
    user: JogadorWeb = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Comprar item na loja (com lock por jogador contra race conditions)."""
    from ui_utils import LOJA_CARVALHAL, adicionar_ao_inventario

    if item_nome not in LOJA_CARVALHAL:
        raise HTTPException(status_code=404, detail="Item não encontrado na loja")

    item_data = LOJA_CARVALHAL[item_nome]
    preco_total = item_data["preco"] * quantidade

    # Lock por jogador: serialized compras do mesmo user
    shop_lock = _get_shop_lock(user.telefone)
    async with shop_lock:
        # Re-fetch gold fresco do DB (pode ter mudado desde o Depends)
        db.refresh(user, ["gold", "inventario"])

        if user.gold < preco_total:
            raise HTTPException(status_code=400, detail=f"Ouro insuficiente. Necessário: {preco_total} PO, você tem: {user.gold} PO")

        # Deduzir ouro
        user.gold -= preco_total

        # Adicionar ao inventário
        adicionar_ao_inventario(user, [item_nome] * quantidade)

        db.commit()

    return JSONResponse({
        "success": True,
        "message": f"Comprou {quantidade}x {item_nome} por {preco_total} PO",
        "gold": user.gold,
        "inventario": user.inventario,
    })

# ════════════════════════════════════════════════════════════════════════
# API DE AÇÕES — Usa ActionResolver completo (engine D&D 5e)
# ════════════════════════════════════════════════════════════════════════

@router.post("/api/acao")
async def api_acao(
    request: Request,
    party_id: str = Form(...),
    tipo: str = Form(...),
    alvo_id: str = Form(""),
    dados: str = Form("{}", max_length=2000),
    user: JogadorWeb = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Endpoint principal para processar ações do jogador via ActionResolver + IA Narração."""

    party_id = party_id.upper()

    if user.party_id != party_id:
        raise HTTPException(status_code=403, detail="Você não está nesta party")

    # Rate limit: evita spam de chamadas OpenAI (12 ações/min por jogador)
    if not _check_rate_limit(user.telefone):
        return JSONResponse(status_code=429, content={
            "success": False,
            "message": "⚡ Ação muito rápida! Aguarda alguns segundos antes de agir novamente.",
        })

# CRIT-02 FIX: try/finally garante lock.release() em TODOS os caminhos
    # F12: Party Lock - uma ação por vez por party (máx 10s de espera)
    lock = get_party_lock(party_id)
    try:
        await asyncio.wait_for(lock.acquire(), timeout=10.0)
    except asyncio.TimeoutError:
        return JSONResponse(status_code=429, content={
            "success": False,
            "message": "A party está ocupada. Tenta novamente em instantes.",
        })

    try:
        campanha = db.query(CampanhaWeb).filter(CampanhaWeb.party_id == party_id).first()
        if not campanha:
            raise HTTPException(status_code=404, detail="Campanha não encontrada")

        # F13: Turn Order - Verificar se é o turno do jogador (combate MP)
        # Otimizado: count query em vez de .all() + len()
        from sqlalchemy import func as _sa_func
        total_membros = db.query(_sa_func.count(JogadorWeb.telefone)).filter(
            JogadorWeb.party_id == party_id,
        ).scalar() or 0
        if campanha.em_combate and total_membros > 1:
            turno_atual = campanha.turno_atual or 1
            membros_vivos = db.query(JogadorWeb).filter(
                JogadorWeb.party_id == party_id,
                JogadorWeb.hp_atual > 0,
            ).order_by(JogadorWeb.telefone).all()
            if membros_vivos:
                idx_turno = (turno_atual - 1) % len(membros_vivos)
                jogador_turno = membros_vivos[idx_turno]
                if jogador_turno.telefone != user.telefone:
                    return JSONResponse(status_code=400, content={
                        "success": False,
                        "message": f"Espera a tua vez! É o turno de {jogador_turno.nome}.",
                    })
                # Avançar turno após ação
                campanha.turno_atual = (turno_atual % len(membros_vivos)) + 1
            else:
                # Todos mortos — party wipe será tratado adiante
                campanha.turno_atual = 1

        # Capturar cena_atual original antes da ação
        cena_atual_original = campanha.cena_atual

        # Parse dados extras com validação (anti JSON bomb)
        try:
            dados_extra = json.loads(dados) if dados else {}
        except json.JSONDecodeError:
            dados_extra = {}
        # Validar tipo e limitar tamanho de campos string
        if not isinstance(dados_extra, dict):
            dados_extra = {}
        _texto = dados_extra.get("texto", "")
        if isinstance(_texto, str) and len(_texto) > 500:
            dados_extra["texto"] = _texto[:500]

        # Buscar cena atual (passa db para reaproveitar sessão do request)
        cena_data = get_cena_cached_sync(campanha.cena_atual, db=db)
        cena_obj = None
        if cena_data:
            cena_obj = db.query(Cena).filter(Cena.cod_sala == campanha.cena_atual).first()

        # Construir json_ia para o ActionResolver
        intencao_map = {
            "movimento": "NAVEGAR",
            "ataque": "COMBATE",
            "magia": "MAGIA",
            "item": "INTERACAO",
            "defesa": "MANOBRA",
        }
        intencao = intencao_map.get(tipo.lower(), tipo.upper())

        direcao = dados_extra.get("direcao") or dados_extra.get("destino")

        # Se não há direção e a intenção é NAVEGAR, pré-computar com IA em thread
        if not direcao and intencao == "NAVEGAR" and cena_obj and cena_obj.conexoes:
            texto_livre = dados_extra.get("texto", tipo)
            direcao = await asyncio.to_thread(
                extrair_direcao_sync, texto_livre, cena_obj.conexoes
            )
            if "invalido" in (direcao or "").lower():
                direcao = None

        json_ia = {
            "intencao": intencao,
            "alvo": alvo_id,
        }
        if direcao:
            json_ia["direcao"] = direcao
        json_ia.update(dados_extra)

        # Usar ActionResolver (em thread para nao bloquear o event loop)
        resolver = ActionResolver(db)
        resultado = await asyncio.to_thread(
            resolver.resolver_acao,
            jogador=user,
            campanha=campanha,
            cena_atual=cena_obj,
            json_ia=json_ia,
            texto_jogador=dados_extra.get("texto", tipo),
        )

        # Commit mudancas com rollback em caso de falha
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error("[DB] Rollback na acao: %s", e, exc_info=True)
            return JSONResponse(status_code=500, content={
                "success": False,
                "message": "Erro ao salvar estado. Tenta novamente.",
            })

        # ── PARTY WIPE: se todos os membros morreram em combate ─────────────────
        if campanha.em_combate:
            membros_vivos = db.query(JogadorWeb).filter(
                JogadorWeb.party_id == party_id,
                JogadorWeb.hp_atual > 0,
            ).count()
            if membros_vivos == 0:
                campanha.em_combate = False
                campanha.status = "exploracao"
                campanha.cena_atual = "taverna"
                for m in db.query(JogadorWeb).filter(JogadorWeb.party_id == party_id).all():
                    m.hp_atual = max(1, m.hp_maximo // 2)
                    m.cena_atual = "taverna"
                    m.slots_magia = m.slots_magia_max
                    m.hit_dice_atual = getattr(m, "hit_dice_max", 1)
                    set_status_efeitos(m, [])
                try:
                    db.commit()
                except Exception as e:
                    db.rollback()
                    logger.error("[DB] Rollback no party wipe: %s", e, exc_info=True)
                await ws_manager.broadcast_json(party_id, {
                    "type": "party_wipe",
                    "message": "☠️ A party foi derrotada! A Patrulha de Carvalhal resgatou todos e levou de volta à taverna.",
                })
                return JSONResponse({
                    "success": False,
                    "log_combate": [resultado.narrativa_mecanica] if resultado.narrativa_mecanica else [],
                    "narracao": "☠️ A party foi derrotada! Transportados de volta à taverna.",
                    "party_wipe": True,
                    "redirect": f"/game/jogar/{party_id}",
                })

        # ── NARRAÇÃO (otimizada — segue lógica do rpg_bot) ──────────────────────
        texto_jogador = dados_extra.get("texto", tipo)
        descricao_visual = cena_data.get("descricao_visual", "") if cena_data else ""
        descricao_sala = cena_data.get("descricao", "") if cena_data else ""
        narracao_ia = ""

        try:
            if intencao == "COMBATE" or intencao == "MAGIA":
                resultado_dados = {
                    "sucesso": resultado.sucesso,
                    "narrativa_mecanica": resultado.narrativa_mecanica,
                    "dados_extras": resultado.dados_extras,
                }
                narracao_ia = await narrar_combate(
                    jogador_nome=user.nome,
                    acao_jogador=texto_jogador,
                    resultado_dados=resultado_dados,
                    descricao_sala=descricao_sala,
                )
            elif intencao == "NAVEGAR":
                cena_nova = resultado.dados_extras.get("nova_cena")
                if cena_nova and cena_nova != cena_atual_original:
                    nova_cena_data = get_cena_cached_sync(cena_nova, db=db)
                    nova_desc_visual = nova_cena_data.get("descricao_visual", "") if nova_cena_data else ""
                    if nova_desc_visual:
                        narracao_ia = nova_desc_visual
                    else:
                        nova_desc = nova_cena_data.get("descricao", "") if nova_cena_data else ""
                        narracao_ia = await narrar_ambiente(
                            jogador_nome=user.nome,
                            acao_jogador=texto_jogador,
                            descricao_sala=nova_desc,
                        )
                elif descricao_visual:
                    narracao_ia = descricao_visual
                else:
                    narracao_ia = await narrar_ambiente(
                        jogador_nome=user.nome,
                        acao_jogador=texto_jogador,
                        descricao_sala=descricao_sala,
                    )
            else:
                if descricao_visual:
                    narracao_ia = descricao_visual
                else:
                    narracao_ia = await narrar_ambiente(
                        jogador_nome=user.nome,
                        acao_jogador=texto_jogador,
                        descricao_sala=descricao_sala,
                    )
        except (TimeoutError, ConnectionError, OSError) as e:
            logger.warning("[IA NARRACAO] Erro de rede/timeout: %s", e)
            narracao_ia = ""
        except Exception as e:
            logger.error("[IA NARRACAO] Erro inesperado: %s: %s", type(e).__name__, e, exc_info=True)
            narracao_ia = ""

        # Resposta
        response_data = {
            "success": resultado.sucesso,
            "log_combate": [resultado.narrativa_mecanica] if resultado.narrativa_mecanica else [],
            "narracao": narracao_ia,
            "estado_atualizado": {
                "hp_atual": user.hp_atual,
                "inimigos": get_encontros_vivos_sync(campanha.cena_atual, campanha.estado_salas, db=db),
            }
        }

        # Se houve mudança de cena, incluir redirect
        cena_nova = resultado.dados_extras.get("nova_cena")
        if cena_nova and cena_nova != cena_atual_original:
            response_data["redirect"] = f"/game/jogar/{party_id}"

        return JSONResponse(response_data)
    finally:
        # CRIT-02 FIX: lock SEMPRE é liberado, mesmo em exceções
        lock.release()


@router.post("/api/gerar-imagem-critica")
async def api_gerar_imagem_critica(
    request: Request,
    party_id: str = Form(...),
    contexto_critico: str = Form(...),  # JSON string com contexto
    user: JogadorWeb = Depends(require_user),
):
    """Gera imagem dramática para acerto/falha crítica via FAL.ai."""
    party_id = party_id.upper()

    if user.party_id != party_id:
        raise HTTPException(status_code=403, detail="Você não está nesta party")

    # FIX #3 (Alto): Rate limit — cada chamada FAL.ai tem custo financeiro real
    if not _check_rate_limit(f"img_{user.telefone}"):
        return JSONResponse(status_code=429, content={
            "success": False,
            "message": "Demasiadas imagens geradas! Aguarda alguns segundos.",
        })

    try:
        contexto_raw = json.loads(contexto_critico)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Contexto inválido")

    # Whitelist de campos aceitos + limitação de tamanho (anti prompt injection)
    _CAMPOS_PERMITIDOS = {"tipo", "inimigo_nome", "acao", "cena_nome"}
    _MAX_LEN = 200
    contexto = {}
    for k, v in contexto_raw.items():
        if k in _CAMPOS_PERMITIDOS and isinstance(v, str):
            contexto[k] = v[:_MAX_LEN]

    # Gera a imagem
    imagem_url = await gerar_imagem_critica(contexto)

    if imagem_url:
        return JSONResponse({
            "success": True,
            "imagem_url": imagem_url,
            "tipo": contexto.get("tipo", "critico_acerto"),
        })
    else:
        return JSONResponse({
            "success": False,
            "message": "Erro ao gerar imagem crítica",
        })


@router.post("/api/taverna/chat")
@router.post("/api/npc/chat")
async def api_taverna_chat(
    request: Request,
    mensagem: str = Form(..., max_length=2000),
    party_id: str = Form(...),
    npc_nome: str = Form("O Taverneiro"),
    user: JogadorWeb = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Chat com NPCs — usa IA para gerar resposta imersiva como o NPC específico.
    Funciona em qualquer sala, não apenas na taverna. Busca dados do NPC no banco."""
    party_id = party_id.upper()

    if user.party_id != party_id:
        raise HTTPException(status_code=403, detail="Você não está nesta party")

    # Rate limit: evita spam de chamadas OpenAI no chat
    if not _check_rate_limit(f"chat_{user.telefone}"):
        return JSONResponse(status_code=429, content={
            "success": False,
            "message": "⚡ Mensagem muito rápida! Aguarda alguns segundos.",
        })

    campanha = db.query(CampanhaWeb).filter(CampanhaWeb.party_id == party_id).first()
    if not campanha:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    # Buscar dados do NPC no banco (descrição, diálogo base)
    npc_db = db.query(Npc).filter(Npc.nome == npc_nome).first()
    npc_descricao = npc_db.descricao if npc_db else ""
    npc_dialogo_base = npc_db.dialogo_base if npc_db else ""

    # Buscar contexto completo do jogador
    from modelos_web import Missao
    from stats_manager_sync import get_estatisticas_resumo

    # Missões ativas
    missoes_ativas = db.query(Missao).filter(
        Missao.jogador_telefone == user.telefone,
        Missao.party_id == party_id,
        Missao.concluida == False
    ).all()

    # Estatísticas recentes
    stats = get_estatisticas_resumo(db, user.telefone)

    # Membros da party
    membros = db.query(JogadorWeb).filter(JogadorWeb.party_id == party_id).all()

    # Cena atual
    cena_data = get_cena_cached_sync(campanha.cena_atual, db=db)
    descricao_sala = cena_data.get("descricao_visual", "") if cena_data else ""
    nome_sala = cena_data.get("nome_sala", "Local desconhecido") if cena_data else "Local desconhecido"

    # Construir perfil do aventureiro para o NPC
    perfil_aventureiro = f"""
=== PERFIL DO AVENTUREIRO ===
Nome: {user.nome} ({user.classe} Nv.{user.nivel or 1})
Raça: {user.raca}
HP: {user.hp_atual}/{user.hp_maximo} | CA: {user.modificador_defesa} | Ataque: +{user.modificador_ataque}
Ouro: {user.gold} PO
Slots Magia: {user.slots_magia}/{user.slots_magia_max}

=== MISSÕES ATIVAS ===
{chr(10).join([f"- {m.titulo}: {m.descricao} (Progresso: {m.progresso}/{m.objetivo_quantidade})" for m in missoes_ativas]) if missoes_ativas else "Nenhuma missão ativa no momento."}

=== ESTATÍSTICAS RECENTES ===
- XP Total: {stats.get('xp_total', 0) if isinstance(stats, dict) else 0}
- Inimigos Derrotados: {stats.get('inimigos_derrotados', 0) if isinstance(stats, dict) else 0}
- Dano Causado: {stats.get('dano_causado', 0) if isinstance(stats, dict) else 0}
- Ouro Ganho: {stats.get('ouro_ganho', 0) if isinstance(stats, dict) else 0}

=== PARTY ATUAL ===
{chr(10).join([f"- {m.nome} ({m.classe} Nv.{m.nivel or 1})" for m in membros])}

=== SALA ATUAL ===
{nome_sala}: {descricao_sala[:300]}
"""

    # Gerar resposta do NPC via IA
    try:
        from ai_engine_web import narrar_taverna
        resposta = await narrar_taverna(
            user.nome, mensagem, perfil_aventureiro,
            npc_nome=npc_nome,
            npc_descricao=npc_descricao,
            npc_dialogo_base=npc_dialogo_base,
        )
    except Exception as e:
        logger.error("[IA NPC] Erro: %s", e, exc_info=True)
        fallback = npc_dialogo_base or "O personagem te observa em silêncio."
        resposta = f"{npc_nome}: '{fallback}'"

    return JSONResponse({"resposta": resposta})


# ════════════════════════════════════════════════════════════════════════
# ENDPOINTS ADICIONAIS — IA, STATS, INVENTÁRIO, EQUIPAR, MISSÕES
# ════════════════════════════════════════════════════════════════════════

@router.post("/api/acao/interpretar")
async def api_acao_interpretar(
    request: Request,
    texto: str = Form(..., max_length=2000),
    party_id: str = Form(...),
    user: JogadorWeb = Depends(require_user),
    db: Session = Depends(get_db),
):
    """
    Endpoint para texto livre → JSON estruturado via IA.
    O jogador digita ação natural (ex: \"ataco o goblin com minha espada\")
    e a IA extrai intenção mecânica para o ActionResolver.
    """
    party_id = party_id.upper()

    if user.party_id != party_id:
        raise HTTPException(status_code=403, detail="Você não está nesta party")

    # Rate limit: evita spam de chamadas OpenAI (interpretação de texto)
    if not _check_rate_limit(f"interpret_{user.telefone}"):
        return JSONResponse(status_code=429, content={
            "success": False,
            "message": "⚡ Muitas interpretações! Aguarda alguns segundos.",
        })

    campanha = db.query(CampanhaWeb).filter(CampanhaWeb.party_id == party_id).first()
    if not campanha:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    # Buscar contexto da sala
    cena_data = get_cena_cached_sync(campanha.cena_atual, db=db)
    contexto_sala = ""
    if cena_data:
        inimigos = get_encontros_vivos_sync(campanha.cena_atual, campanha.estado_salas, db=db)
        inimigo_nomes = [e["nome"] for e in inimigos] if inimigos else []
        npcs = get_npc_da_cena_cached_sync(campanha.cena_atual, db=db)
        npc_nomes = [n.get("nome") for n in npcs] if npcs else []
        contexto_sala = (
            f"Sala: {cena_data.get('nome', campanha.cena_atual)}. "
            f"Inimigos: {', '.join(inimigo_nomes) if inimigo_nomes else 'nenhum'}. "
            f"NPCs: {', '.join(npc_nomes) if npc_nomes else 'nenhum'}. "
            f"Saídas: {list(cena_data.get('conexoes', {}).keys())}. "
            f"Descrição: {cena_data.get('descricao', '')[:200]}"
        )

    # IA extrai intenção estruturada
    try:
        json_ia = await interpretar_acao_json(texto, contexto_sala)
    except Exception as e:
        logger.error("[IA INTERPRETAR] Erro: %s", e, exc_info=True)
        json_ia = {
            "intencao": "OUTRO", "alvo": None, "estilo": None,
            "magia_usada": None, "manobra": None, "item": None, "direcao": None
        }

    return JSONResponse({
        "texto_original": texto,
        "json_extraido": json_ia,
        "contexto_usado": contexto_sala[:300],
    })


@router.get("/api/stats")
async def api_stats(
    request: Request,
    user: JogadorWeb = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Retorna estatísticas e histórico do jogador."""
    from stats_manager_sync import get_estatisticas_resumo
    
    stats = get_estatisticas_resumo(db, user.telefone)
    return JSONResponse(stats)


@router.get("/api/inventario")
async def api_inventario(
    request: Request,
    user: JogadorWeb = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Retorna inventário formatado do jogador."""
    from ui_utils import obter_inventario_limpo, formatar_inventario_para_display, contar_inventario
    
    inv_limpo = obter_inventario_limpo(user.inventario)
    inv_formatado = formatar_inventario_para_display(inv_limpo)
    inv_contado = contar_inventario(inv_limpo)
    
    return JSONResponse({
        "inventario_raw": user.inventario,
        "inventario_limpo": inv_contado,
        "inventario_display": inv_formatado,
        "arma_equipada": user.arma_equipada,
        "armadura_equipada": user.armadura_equipada,
        "gold": user.gold,
    })


@router.post("/api/equipar")
async def api_equipar(
    request: Request,
    item_nome: str = Form(...),
    user: JogadorWeb = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Equipa arma ou armadura do inventário."""
    from ui_utils import obter_inventario_limpo, ARMAS_DB, LOJA_CARVALHAL, calcular_ca_final, calcular_modificadores_ataque
    
    inv_limpo = obter_inventario_limpo(user.inventario)
    
    # FIX #9 (Médio): Busca exata primeiro, substring como fallback
    item_no_inv = next(
        (i for i in inv_limpo if i.lower() == item_nome.lower()), None
    )
    if not item_no_inv:
        item_no_inv = next(
            (i for i in inv_limpo
             if item_nome.lower() in i.lower()
             and len(item_nome) <= len(i)),
            None,
        )
    
    if not item_no_inv:
        raise HTTPException(status_code=404, detail=f"Item '{item_nome}' não encontrado no inventário")
    
    # Verificar se é arma
    is_arma = any(item_nome.lower() in nome.lower() for nome in ARMAS_DB.keys())
    # Verificar se é armadura
    is_armadura = any(
        item_nome.lower() in nome.lower() and dados.get("tipo") == "armadura" 
        for nome, dados in LOJA_CARVALHAL.items()
    )
    
    if not is_arma and not is_armadura:
        raise HTTPException(status_code=400, detail=f"'{item_no_inv}' não é uma arma ou armadura equipável")
    
    mensagem = ""
    if is_arma:
        user.arma_equipada = item_no_inv
        # Recalcular modificadores de ataque
        mod_ataque, nome_oficial, dano_dado = calcular_modificadores_ataque(user, item_no_inv)
        user.modificador_ataque = mod_ataque + user.proficiencia
        user.mod_dano = mod_ataque
        user.dano_dado = dano_dado
        mensagem = f"⚔️ {nome_oficial} equipada como arma!"
    else:
        user.armadura_equipada = item_no_inv
        # Recalcular CA
        user.modificador_defesa = calcular_ca_final(user, item_no_inv)
        mensagem = f"🛡️ {item_no_inv} equipada como armadura!"
    
    db.commit()
    
    return JSONResponse({
        "success": True,
        "message": mensagem,
        "arma_equipada": user.arma_equipada,
        "armadura_equipada": user.armadura_equipada,
        "modificador_ataque": user.modificador_ataque,
        "mod_dano": user.mod_dano,
        "modificador_defesa": user.modificador_defesa,
    })


@router.get("/api/status")
async def api_status(
    request: Request,
    user: JogadorWeb = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Retorna status completo do personagem."""
    from ui_utils import XP_POR_NIVEL, obter_inventario_limpo
    
    xp_proximo = XP_POR_NIVEL.get(user.nivel + 1, 0)
    xp_atual_nivel = xp_proximo - XP_POR_NIVEL.get(user.nivel, 0) if user.nivel > 1 else xp_proximo
    xp_progresso = user.xp - XP_POR_NIVEL.get(user.nivel, 0) if user.nivel > 1 else user.xp
    
    inv_limpo = obter_inventario_limpo(user.inventario)
    
    # F10: Perícias de background e proficiências da classe
    from ui_utils import BACKGROUND_SKILLS
    pericias_bg = BACKGROUND_SKILLS.get(user.background, [])
    
    # Perícias por classe (D&D 5e) — nomes canônicos de PERICIAS_DND_5E
    CLASSE_PERICIAS = {
        "Bárbaro": ["Intimidação", "Sobrevivência"],
        "Bardo": ["Acrobacia", "Performance", "Enganação", "História", "Intuição", "Percepção", "Persuasão", "Prestidigitação"],
        "Bruxo": ["Arcanismo", "Enganação", "Intimidação", "Investigação", "Natureza", "Religião"],
        "Clérigo": ["História", "Intuição", "Medicina", "Persuasão", "Religião"],
        "Druida": ["Arcanismo", "Atletismo", "Intuição", "Medicina", "Natureza", "Percepção", "Religião", "Sobrevivência"],
        "Feiticeiro": ["Arcanismo", "Enganação", "Intimidação", "Persuasão", "Religião"],
        "Guerreiro": ["Acrobacia", "Adestrar Animais", "Atletismo", "História", "Intimidação", "Percepção", "Sobrevivência"],
        "Ladino": ["Acrobacia", "Atletismo", "Enganação", "Intimidação", "Investigação", "Percepção", "Prestidigitação", "Sobrevivência"],
        "Mago": ["Arcanismo", "História", "Intuição", "Investigação", "Medicina", "Religião"],
        "Monge": ["Acrobacia", "Atletismo", "História", "Intuição", "Religião", "Furtividade"],
        "Paladino": ["Atletismo", "Intimidação", "Medicina", "Persuasão", "Religião"],
        "Patrulheiro": ["Adestrar Animais", "Atletismo", "Investigação", "Natureza", "Percepção", "Furtividade", "Sobrevivência"],
    }
    pericias_classe = CLASSE_PERICIAS.get(user.classe, [])
    todas_pericias = list(set(pericias_bg + pericias_classe))
    
    return JSONResponse({
        "nome": user.nome,
        "nivel": user.nivel,
        "xp": user.xp,
        "xp_proximo_nivel": xp_proximo,
        "xp_progresso_nivel": xp_progresso,
        "raca": user.raca,
        "classe": user.classe,
        "background": user.background,
        "hp_atual": user.hp_atual,
        "hp_maximo": user.hp_maximo,
        "atributos": {
            "STR": user.str_val, "DEX": user.dex_val, "CON": user.con_val,
            "INT": user.int_val, "WIS": user.wis_val, "CHA": user.cha_val,
        },
        "modificadores": {
            "STR": user.mod_str, "DEX": user.mod_dex, "CON": user.mod_con,
            "INT": user.mod_int, "WIS": user.mod_wis, "CHA": user.mod_cha,
        },
        "modificador_ataque": user.modificador_ataque,
        "mod_dano": user.mod_dano,
        "modificador_defesa": user.modificador_defesa,
        "proficiencia": user.proficiencia,
        "arma_equipada": user.arma_equipada,
        "armadura_equipada": user.armadura_equipada,
        "dano_dado": user.dano_dado,
        "gold": user.gold,
        "inventario": inv_limpo,
        "slots_magia": user.slots_magia,
        "slots_magia_max": user.slots_magia_max,
        "hit_dice_atual": user.hit_dice_atual,
        "hit_dice_max": user.hit_dice_max,
        "status_efeitos": user.status_efeitos,
        "cena_atual": user.cena_atual,
        "party_id": user.party_id,
        "pericias_background": pericias_bg,
        "pericias_classe": pericias_classe,
        "todas_pericias": todas_pericias,
    })


@router.get("/api/missoes")
async def api_missoes(
    request: Request,
    user: JogadorWeb = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Retorna missões ativas do jogador na campanha atual."""
    from modelos_web import Missao
    
    if not user.party_id:
        return JSONResponse({"missoes": [], "message": "Você não está em uma party"})
    
    missoes = db.query(Missao).filter(
        Missao.jogador_telefone == user.telefone,
        Missao.party_id == user.party_id,
        Missao.concluida == False
    ).all()
    
    return JSONResponse({
        "missoes": [
            {
                "id": m.id,
                "titulo": m.titulo,
                "descricao": m.descricao,
                "tipo": m.tipo,
                "objetivo_atual": m.objetivo_atual,
                "progresso": m.progresso,
                "objetivo_total": m.objetivo_quantidade,
                "recompensa_xp": m.recompensa_xp,
                "recompensa_ouro": m.recompensa_ouro,
                "recompensa_item": m.recompensa_item,
            }
            for m in missoes
        ]
    })


@router.post("/api/dice")
async def api_dice(
    request: Request,
    expressao: str = Form(...),
    user: JogadorWeb = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Rola dados (ex: 2d6+3, d20, 1d8-1) e broadcast para a party."""
    import re
    party_id = user.party_id
    if not party_id:
        raise HTTPException(status_code=400, detail="Você não está em uma party")

    # Rate limit: evita spam de rolagens + WebSocket broadcast
    if not _check_rate_limit(f"dice_{user.telefone}"):
        return JSONResponse(status_code=429, content={
            "success": False,
            "message": "⚡ Muitas rolagens! Aguarda alguns segundos.",
        })

    # Parse expressão: NdM+/-K
    match = re.match(r'(\d*)d(\d+)([+-]\d+)?', expressao.strip().lower().replace(' ', ''))
    if not match:
        raise HTTPException(status_code=400, detail="Expressão inválida. Use: 2d6+3, d20, 1d8-1")

    num_dados = int(match.group(1)) if match.group(1) else 1
    lados = int(match.group(2))
    modificador = int(match.group(3)) if match.group(3) else 0

    if num_dados > 20 or lados > 100:
        raise HTTPException(status_code=400, detail="Máximo 20 dados de 100 lados")

    import random
    tiragens = [random.randint(1, lados) for _ in range(num_dados)]
    total = sum(tiragens) + modificador

    # Formatar resultado
    dados_str = '+'.join(str(t) for t in tiragens)
    if modificador > 0:
        dados_str += f'+{modificador}'
    elif modificador < 0:
        dados_str += str(modificador)

    resultado = f"🎲 {expressao.upper()}: [{','.join(str(t) for t in tiragens)}] = {total}"

    # Broadcast para a party via WebSocket
    try:
        from app.ws_manager import ws_manager
        await ws_manager.broadcast_json(party_id, {
            "type": "dice_roll",
            "jogador": user.nome,
            "expressao": expressao,
            "resultado": resultado,
            "total": total,
        })
    except Exception as e:
        logger.warning("[DICE] WS broadcast error: %s", e)

    return JSONResponse({
        "success": True,
        "resultado": resultado,
        "total": total,
        "tiragens": tiragens,
        "expressao": expressao,
    })


@router.post("/api/vender")
async def api_vender(
    request: Request,
    item_nome: str = Form(...),
    user: JogadorWeb = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Vende item do inventário pela metade do preço (com lock por jogador)."""
    from ui_utils import LOJA_CARVALHAL, obter_inventario_limpo

    # Lock por jogador: serialized vendas do mesmo user (anti race condition)
    shop_lock = _get_shop_lock(user.telefone)
    async with shop_lock:
        # Re-fetch fresco do DB (pode ter mudado desde o Depends)
        db.refresh(user, ["gold", "inventario"])

        if user.cena_atual not in ("carvalhal", "taverna"):
            raise HTTPException(status_code=400, detail="Só podes vender itens na Vila de Carvalhal ou na Taverna")

        inv_limpo = obter_inventario_limpo(user.inventario)
        # FIX #9 (Médio): Busca exata primeiro, substring como fallback
        item_para_vender = next(
            (i for i in inv_limpo if i.lower() == item_nome.lower()), None
        )
        if not item_para_vender:
            item_para_vender = next(
                (i for i in inv_limpo
                 if item_nome.lower() in i.lower()
                 and len(item_nome) <= len(i)),
                None,
            )
        if not item_para_vender:
            raise HTTPException(status_code=404, detail=f"Item '{item_nome}' não encontrado no inventário")

        # Busca exata primeiro, depois por contém (evita "Espada Curta" casar com "Espada Longa")
        preco_base = None
        item_lower = item_para_vender.lower()
        for k, v in LOJA_CARVALHAL.items():
            if k.lower() == item_lower:
                preco_base = v["preco"]
                break
        if preco_base is None:
            preco_base = next((v["preco"] for k, v in LOJA_CARVALHAL.items()
                if k.lower() in item_lower or item_lower in k.lower()), 2)
        valor_venda = max(1, math.floor(preco_base / 2))

        user.inventario.remove(item_para_vender)
        user.gold += valor_venda
        db.commit()

        return JSONResponse({
            "success": True,
            "message": f"Vendeste {item_para_vender} por {valor_venda} PO",
            "gold": user.gold,
            "inventario": user.inventario,
        })


@router.post("/api/reset")
async def api_reset(
    request: Request,
    confirmacao: str = Form(...),
    user: JogadorWeb = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Deleta o personagem e limpa dados da party.

    Requer confirmação explícita (confirmacao="CONFIRMAR") para evitar
    destruição acidental ou via CSRF.
    """
    if confirmacao != "CONFIRMAR":
        raise HTTPException(
            status_code=400,
            detail="Digite 'CONFIRMAR' para apagar o personagem.",
        )
    from modelos_web import Missao, EstatisticasJogador

    telefone = user.telefone

    # Limpar missões (bulk delete)
    db.query(Missao).filter(Missao.jogador_telefone == telefone).delete(
        synchronize_session='fetch',
    )

    # Limpar estatísticas (bulk delete)
    db.query(EstatisticasJogador).filter(EstatisticasJogador.jogador_telefone == telefone).delete(
        synchronize_session='fetch',
    )

    # Deletar jogador
    db.delete(user)

    # Se era o único na party, deletar campanha
    party_id = user.party_id
    if party_id:
        from modelos_web import CampanhaWeb
        outros = db.query(JogadorWeb).filter(JogadorWeb.party_id == party_id).count()
        if outros <= 1:  # só ele mesmo ainda
            campanha = db.query(CampanhaWeb).filter(CampanhaWeb.party_id == party_id).first()
            if campanha:
                db.delete(campanha)

    db.commit()

    return JSONResponse({
        "success": True,
        "message": "Personagem deletado. Podes criar um novo na tela inicial.",
    })


@router.get("/api/dashboard")
async def api_dashboard(
    request: Request,
    user: JogadorWeb = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Dashboard completo com ranking, XP bar e KDA."""
    from ui_utils import XP_POR_NIVEL
    from stats_manager_sync import get_estatisticas_resumo
    from sqlalchemy import func

    # Estatísticas (pode não existir para usuários novos)
    try:
        stats = get_estatisticas_resumo(db, user.telefone)
        if isinstance(stats, dict) and "erro" in stats:
            stats = {}
    except Exception:
        stats = {}

    # Ranking global (PK is 'telefone', not 'id')
    total_jogadores = db.query(func.count(JogadorWeb.telefone)).scalar() or 1
    jogadores_acima = db.query(func.count(JogadorWeb.telefone)).filter(JogadorWeb.xp > user.xp).scalar() or 0
    rank_posicao = jogadores_acima + 1

    # XP Progress bar
    xp_nivel_atual = XP_POR_NIVEL.get(user.nivel, 0)
    xp_proximo = XP_POR_NIVEL.get(user.nivel + 1, 355000)
    xp_necessario = xp_proximo - xp_nivel_atual
    xp_progresso = user.xp - xp_nivel_atual
    progresso_pct = min(100, int((xp_progresso / xp_necessario) * 100)) if xp_necessario > 0 else 100
    barras = int(progresso_pct / 10)
    barra = "█" * barras + "░" * (10 - barras)

    # KDA
    total_ataques = stats.get("total_ataques_acertados", 0) + stats.get("total_ataques_errados", 0)
    taxa_acerto = (stats.get("total_ataques_acertados", 0) / total_ataques * 100) if total_ataques > 0 else 0

    return JSONResponse({
        "nome": user.nome,
        "nivel": user.nivel or 1,
        "xp": user.xp,
        "xp_proximo": xp_proximo,
        "xp_progresso_nivel": xp_progresso,
        "xp_necessario_nivel": xp_necessario,
        "barra_progresso": barra,
        "progresso_pct": progresso_pct,
        "rank": {
            "posicao": rank_posicao,
            "total_jogadores": total_jogadores,
        },
        "stats": {
            "inimigos_derrotados": stats.get("inimigos_derrotados", 0),
            "ataques_acertados": stats.get("total_ataques_acertados", 0),
            "ataques_errados": stats.get("total_ataques_errados", 0),
            "taxa_acerto": round(taxa_acerto, 1),
            "criticos": stats.get("criticos_acertados", 0),
            "dano_total": stats.get("danos_causados_total", 0),
            "ouro_total": stats.get("ouro_coletado", 0),
        },
        "gold": user.gold,
    })


@router.post("/api/missao/concluir")
async def api_missao_concluir(
    request: Request,
    missao_id: int = Form(...),
    user: JogadorWeb = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Marca missão como concluída e aplica recompensas."""
    from modelos_web import Missao

    # FIX #4 (Alto): Lock por usuário + SELECT FOR UPDATE anti race condition
    shop_lock = _get_shop_lock(user.telefone)
    async with shop_lock:
        missao = db.query(Missao).filter(
            Missao.id == missao_id,
            Missao.jogador_telefone == user.telefone,
        ).with_for_update().first()

        if not missao:
            raise HTTPException(status_code=404, detail="Missão não encontrada")

        if missao.concluida:
            raise HTTPException(status_code=400, detail="Missão já concluída")

        missao.concluida = True
        missao.data_conclusao = datetime.now()

        # Aplicar recompensas
        user.xp += missao.recompensa_xp
        user.gold += missao.recompensa_ouro
        if missao.recompensa_item:
            from ui_utils import adicionar_ao_inventario
            adicionar_ao_inventario(user, [missao.recompensa_item])

        # Verificar level up
        from game_helpers import aplicar_level_up
        niveis_subidos = aplicar_level_up(user)
        level_up_msg = f"🎉 Subiste {niveis_subidos} nível(s)!" if niveis_subidos > 0 else None

        db.commit()

        return JSONResponse({
            "success": True,
            "message": f"✅ Missão '{missao.titulo}' concluída!",
            "recompensas": {
                "xp": missao.recompensa_xp,
                "ouro": missao.recompensa_ouro,
                "item": missao.recompensa_item,
            },
            "level_up": level_up_msg,
            "novo_nivel": user.nivel,
            "novo_xp": user.xp,
            "novo_gold": user.gold,
        })