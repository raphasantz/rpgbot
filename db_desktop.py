"""
Wrapper síncrono para operações de DB assíncronas (SQLAlchemy) do desktop.
Usa os mesmos models.py e database.py do Telegram.
"""
import asyncio
import json
import os
import random
import string
from typing import Optional, Dict, Any
from pathlib import Path

from database import get_async_db, init_db, DATABASE_URL
from models import Jogador, Campanha
from sqlalchemy import select, func, text
from ui_utils import HP_POR_CLASSE, INVENTARIO_POR_CLASSE, ARMAS_DB, LOJA_CARVALHAL, BONUS_RACA, calcular_modificador, rolar_atributo_4d6

TEM_POSTGRES = "postgresql" in DATABASE_URL and "+asyncpg" in DATABASE_URL


def testar_conexao_postgres() -> bool:
    """Testa se consegue conectar no PostgreSQL."""
    if not TEM_POSTGRES:
        return False
    try:
        import asyncio
        from sqlalchemy.ext.asyncio import create_async_engine
        from database import DATABASE_URL
        
        async def _test():
            engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
            try:
                async with engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                return True
            finally:
                await engine.dispose()
        
        return asyncio.run(_test())
    except Exception:
        return False


def conexao_status_texto() -> str:
    """Retorna texto do status de conexão para UI."""
    if not TEM_POSTGRES:
        return "🔴 Offline (sem config PostgreSQL)"
    
    conectado = testar_conexao_postgres()
    if conectado:
        return "🟢 PostgreSQL Conectado"
    else:
        return "🟡 PostgreSQL Configurado mas Desconectado"


async def _async_criar_personagem(dados: Dict[str, Any]) -> str:
    async for db in get_async_db():
        telefone = dados.get("telefone", f"local-{dados['nome'].lower()}")
        result = await db.execute(select(Jogador).where(Jogador.telefone == telefone))
        jogador_existente = result.scalar_one_or_none()

        codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        party_id = f"PTY-{codigo}"

        # O model usa MutableList.as_mutable(JSON) - passa listas direto, SQLAlchemy serializa
        inventario_lista = dados.get("inventario", [])
        status_lista = dados.get("status_efeitos", [])

        if jogador_existente:
            for key, value in dados.items():
                if key == "inventario":
                    value = inventario_lista
                elif key == "status_efeitos":
                    value = status_lista
                setattr(jogador_existente, key, value)
            jogador_existente.party_id = party_id
            jogador = jogador_existente
        else:
            jogador = Jogador(
                telefone=telefone, party_id=party_id,
                **{k: v for k, v in dados.items() if k not in ("telefone", "party_id", "inventario", "status_efeitos", "estado_salas", "_save_path")},
                inventario=inventario_lista, status_efeitos=status_lista
            )
            db.add(jogador)

        result_camp = await db.execute(select(Campanha).where(Campanha.party_id == party_id))
        campanha = result_camp.scalar_one_or_none()
        estado_salas = dados.get("estado_salas", {})

        if campanha:
            campanha.cena_atual = dados.get("cena_atual", "taverna")
            campanha.estado_salas = estado_salas
        else:
            campanha = Campanha(
                party_id=party_id, host_id=telefone,
                cena_atual=dados.get("cena_atual", "taverna"),
                estado_salas=estado_salas,
                momento="inicio", tensao=0, turno_atual=1
            )
            db.add(campanha)

        await db.flush()
        await db.commit()
        return party_id


async def _async_carregar_jogador(telefone: str) -> Optional[Dict[str, Any]]:
    async for db in get_async_db():
        result = await db.execute(select(Jogador).where(Jogador.telefone == telefone))
        jogador = result.scalar_one_or_none()
        if not jogador:
            return None

        jogador_dict = {
            "telefone": jogador.telefone, "party_id": jogador.party_id,
            "nome": jogador.nome, "raca": jogador.raca, "classe": jogador.classe,
            "background": jogador.background, "sexo": jogador.sexo,
            "nivel": jogador.nivel, "xp": jogador.xp,
            "hp_atual": jogador.hp_atual, "hp_maximo": jogador.hp_maximo,
            "str_val": jogador.str_val, "mod_str": jogador.mod_str,
            "dex_val": jogador.dex_val, "mod_dex": jogador.mod_dex,
            "con_val": jogador.con_val, "mod_con": jogador.mod_con,
            "int_val": jogador.int_val, "mod_int": jogador.mod_int,
            "wis_val": jogador.wis_val, "mod_wis": jogador.mod_wis,
            "cha_val": jogador.cha_val, "mod_cha": jogador.mod_cha,
            "modificador_ataque": jogador.modificador_ataque,
            "modificador_defesa": jogador.modificador_defesa,
            "proficiencia": jogador.proficiencia, "gold": jogador.gold,
            "inventario": list(jogador.inventario) if jogador.inventario else [],
            "arma_equipada": jogador.arma_equipada,
            "armadura_equipada": jogador.armadura_equipada,
            "dano_dado": jogador.dano_dado, "mod_dano": jogador.mod_dano,
            "slots_magia": jogador.slots_magia, "slots_magia_max": jogador.slots_magia_max,
            "hit_dice_atual": jogador.hit_dice_atual, "hit_dice_max": jogador.hit_dice_max,
            "status_efeitos": list(jogador.status_efeitos) if jogador.status_efeitos else [],
            "cena_atual": jogador.cena_atual, "cena_anterior": jogador.cena_anterior,
        }

        if jogador.party_id:
            result_camp = await db.execute(select(Campanha).where(Campanha.party_id == jogador.party_id))
            campanha = result_camp.scalar_one_or_none()
            if campanha:
                jogador_dict["campanha"] = {
                    "party_id": campanha.party_id, "host_id": campanha.host_id,
                    "cena_atual": campanha.cena_atual, "estado_salas": campanha.estado_salas,
                    "momento": campanha.momento, "tensao": campanha.tensao,
                    "turno_atual": campanha.turno_atual, "em_combate": campanha.em_combate,
                }
        return jogador_dict


async def _async_salvar_jogador(dados: Dict[str, Any]) -> bool:
    async for db in get_async_db():
        telefone = dados.get("telefone", f"local-{dados['nome'].lower()}")
        result = await db.execute(select(Jogador).where(Jogador.telefone == telefone))
        jogador = result.scalar_one_or_none()
        if not jogador:
            return False

        # Model usa MutableList.as_mutable(JSON) - passa listas direto
        inventario_lista = dados.get("inventario", [])
        status_lista = dados.get("status_efeitos", [])

        for key, value in dados.items():
            if key in ("inventario", "status_efeitos", "telefone"):
                continue
            setattr(jogador, key, value)
        jogador.inventario = inventario_lista
        jogador.status_efeitos = status_lista
        
        await db.flush()
        await db.commit()
        return True


async def _async_salvar_campanha(party_id: str, cena_atual: str, estado_salas: Dict[str, Any]) -> bool:
    async for db in get_async_db():
        result = await db.execute(select(Campanha).where(Campanha.party_id == party_id))
        campanha = result.scalar_one_or_none()
        if not campanha:
            return False
        campanha.cena_atual = cena_atual
        campanha.estado_salas = estado_salas
        
        await db.flush()
        await db.commit()
        return True


async def _async_entrar_party(party_id: str, telefone: str) -> Optional[Dict[str, Any]]:
    async for db in get_async_db():
        result_camp = await db.execute(select(Campanha).where(Campanha.party_id == party_id))
        campanha = result_camp.scalar_one_or_none()
        if not campanha:
            return None

        count_result = await db.execute(select(func.count()).select_from(Jogador).where(Jogador.party_id == party_id))
        membros = count_result.scalar()
        if membros >= 5:
            return {"erro": "limite"}

        result_jog = await db.execute(select(Jogador).where(Jogador.telefone == telefone))
        jogador = result_jog.scalar_one_or_none()
        if not jogador:
            return None

        membros_result = await db.execute(select(Jogador.xp).where(Jogador.party_id == party_id, Jogador.telefone != telefone))
        xps = [row[0] for row in membros_result.all()]
        if xps:
            xp_medio = sum(xps) // len(xps)
            if xp_medio > jogador.xp:
                pass

        jogador.party_id = party_id
        jogador.cena_atual = campanha.cena_atual

        return {
            "campanha": {"party_id": campanha.party_id, "cena_atual": campanha.cena_atual, "estado_salas": campanha.estado_salas},
            "jogador": {"cena_atual": campanha.cena_atual, "party_id": party_id}
        }


async def _async_criar_party(telefone: str) -> str:
    async for db in get_async_db():
        result = await db.execute(select(Jogador).where(Jogador.telefone == telefone))
        jogador = result.scalar_one_or_none()
        if not jogador or jogador.party_id:
            return None

        codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        party_id = f"PTY-{codigo}"
        jogador.party_id = party_id

        campanha = Campanha(party_id=party_id, host_id=telefone, cena_atual="taverna", estado_salas={}, momento="inicio", tensao=0, turno_atual=1)
        db.add(campanha)
        return party_id


def criar_personagem_no_banco(dados: Dict[str, Any]) -> Optional[str]:
    if not TEM_POSTGRES:
        return None
    try:
        return asyncio.run(_async_criar_personagem(dados))
    except Exception as e:
        print(f"[DB] Erro criando personagem: {e}")
        return None


def carregar_do_banco(telefone: str) -> Optional[Dict[str, Any]]:
    if not TEM_POSTGRES:
        return None
    try:
        return asyncio.run(_async_carregar_jogador(telefone))
    except Exception as e:
        print(f"[DB] Erro carregando: {e}")
        return None


def salvar_jogador_no_banco(dados: Dict[str, Any]) -> bool:
    if not TEM_POSTGRES:
        return False
    try:
        return asyncio.run(_async_salvar_jogador(dados))
    except Exception as e:
        print(f"[DB] Erro salvando jogador: {e}")
        return False


def salvar_campanha_no_banco(party_id: str, cena_atual: str, estado_salas: Dict[str, Any]) -> bool:
    if not TEM_POSTGRES:
        return False
    try:
        return asyncio.run(_async_salvar_campanha(party_id, cena_atual, estado_salas))
    except Exception as e:
        print(f"[DB] Erro salvando campanha: {e}")
        return False


def entrar_party_no_banco(party_id: str, telefone: str) -> Optional[Dict[str, Any]]:
    if not TEM_POSTGRES:
        return None
    try:
        return asyncio.run(_async_entrar_party(party_id.upper(), telefone))
    except Exception as e:
        print(f"[DB] Erro entrando na party: {e}")
        return None


def criar_party_no_banco(telefone: str) -> Optional[str]:
    if not TEM_POSTGRES:
        return None
    try:
        return asyncio.run(_async_criar_party(telefone))
    except Exception as e:
        print(f"[DB] Erro criando party: {e}")
        return None


SAVES_DIR = Path(__file__).parent / "saves"
SAVES_DIR.mkdir(exist_ok=True)


def salvar_local(dados: Dict[str, Any], nome_arquivo: str = None) -> Path:
    if nome_arquivo is None:
        nome_arquivo = f"jogador_{dados.get('nome', 'anonimo').lower()}.json"
    path = SAVES_DIR / nome_arquivo
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    return path


def carregar_local(telefone: str = None, nome: str = None) -> Optional[Dict[str, Any]]:
    if nome:
        path = SAVES_DIR / f"jogador_{nome.lower()}.json"
    elif telefone:
        path = SAVES_DIR / f"jogador_{telefone.replace('local-', '')}.json"
    else:
        path = SAVES_DIR / "jogador_atual.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def carregar_jogador_completo(telefone: str = None, nome: str = None) -> Optional[Dict[str, Any]]:
    if TEM_POSTGRES and telefone:
        dados = carregar_do_banco(telefone)
        if dados:
            return dados
    if nome:
        local = carregar_local(nome=nome)
    elif telefone:
        local = carregar_local(telefone=telefone)
    else:
        local = carregar_local()
    if local:
        return {"jogador": local, "campanha": local.get("campanha")}
    return None


def sincronizar_tudo(dados_jogador: Dict[str, Any], cena_atual: str, estado_salas: Dict[str, Any]) -> bool:
    telefone = dados_jogador.get("telefone", f"local-{dados_jogador.get('nome', 'anonimo').lower()}")
    dados_jogador["cena_atual"] = cena_atual
    dados_jogador["estado_salas"] = estado_salas
    salvar_local(dados_jogador)
    if TEM_POSTGRES:
        # Tenta carregar do banco pra saber se existe
        existente = carregar_do_banco(telefone)
        if existente:
            ok_jogador = salvar_jogador_no_banco(dados_jogador)
        else:
            ok_jogador = criar_personagem_no_banco(dados_jogador) is not None
        
        ok_campanha = True
        party_id = dados_jogador.get("party_id")
        if party_id and party_id != "PTY-LOCAL":
            ok_campanha = salvar_campanha_no_banco(party_id, cena_atual, estado_salas)
        elif party_id == "PTY-LOCAL" and ok_jogador:
            # Se criou no banco, pega o party_id gerado
            recarregado = carregar_do_banco(telefone)
            if recarregado and recarregado.get("party_id"):
                dados_jogador["party_id"] = recarregado["party_id"]
                salvar_local(dados_jogador)
        return ok_jogador and ok_campanha
    return True