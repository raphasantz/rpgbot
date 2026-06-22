"""Models web - wrappers síncronos compatíveis com engine desktop (TODAS as tabelas)."""
import os
from typing import Optional, Dict, Any

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    create_engine,
    func,
    select,
)
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

# ─── Database engine: PostgreSQL (production) ou SQLite (local) ───
DATABASE_URL = os.environ.get("DATABASE_URL", "")
DB_ECHO = os.environ.get("DB_ECHO", "").lower() in ("1", "true", "yes")

if DATABASE_URL:
    # Produção (PostgreSQL)
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        echo=DB_ECHO,
    )
else:
    # Local (SQLite)
    DB_PATH = os.path.join(os.path.dirname(__file__), "rpg.db")
    engine = create_engine(
        f"sqlite:///{DB_PATH}",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
        echo=DB_ECHO,
    )
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)


# ════════════════════════════════════════════════════════════════════════
# ReprMixin — __repr__ legível para os models principais
# ════════════════════════════════════════════════════════════════════════
class ReprMixin:
    """Fornece __repr__ genérico baseado em __repr_fields__."""

    __repr_fields__ = ("id",)

    def __repr__(self) -> str:
        fields = ", ".join(
            f"{f}={getattr(self, f, None)!r}" for f in self.__repr_fields__
        )
        return f"{self.__class__.__name__}({fields})"


# ════════════════════════════════════════════════════════════════════════
# TODOS OS MODELS (estrutura idêntica a models.py do rpg_bot)
# ════════════════════════════════════════════════════════════════════════

class JogadorWeb(ReprMixin, Base):
    __tablename__ = "jogadores"
    __repr_fields__ = ("telefone", "nome", "classe", "nivel")

    telefone = Column(String(20), primary_key=True)
    party_id = Column(String(50), index=True, nullable=True)
    cena_atual = Column(String(50), default="taverna")
    cena_anterior = Column(String(50), nullable=True)

    nome = Column(String(100))
    senha_hash = Column(String(255))
    google_id = Column(String(100), unique=True, index=True, nullable=True)
    avatar_url = Column(String(255), nullable=True)
    email = Column(String(150), unique=True, index=True, nullable=True)
    sexo = Column(String(20), nullable=True)
    classe = Column(String(50))
    raca = Column(String(50))
    background = Column(String(100))

    nivel = Column(Integer, default=1)
    xp = Column(Integer, default=0)

    hp_atual = Column(Integer)
    hp_maximo = Column(Integer)

    str_val = Column("str", Integer)
    dex_val = Column("dex", Integer)
    con_val = Column("con", Integer)
    int_val = Column("int", Integer)
    wis_val = Column("wis", Integer)
    cha_val = Column("cha", Integer)

    mod_str = Column(Integer)
    mod_dex = Column(Integer)
    mod_con = Column(Integer)
    mod_int = Column(Integer)
    mod_wis = Column(Integer)
    mod_cha = Column(Integer)

    modificador_ataque = Column(Integer)
    modificador_defesa = Column(Integer)
    proficiencia = Column(Integer, default=2)

    arma_equipada = Column(String(100), default="Desarmado")
    armadura_equipada = Column(String(100), default="Trajes Comuns")
    dano_dado = Column(String(20), default="1d4")
    mod_dano = Column(Integer, default=0)

    gold = Column(Integer, default=15)
    inventario = Column(MutableList.as_mutable(JSON), default=list)
    slots_magia = Column(Integer, default=0)
    slots_magia_max = Column(Integer, default=0)
    descanso_curto_disponivel = Column(Boolean, default=True)

    hit_dice_max = Column(Integer, default=1)
    hit_dice_atual = Column(Integer, default=1)

    status_efeitos = Column(MutableList.as_mutable(JSON), default=list)
    resistencias = Column(MutableList.as_mutable(JSON), default=list)
    vulnerabilidades = Column(MutableList.as_mutable(JSON), default=list)
    imunidades = Column(MutableList.as_mutable(JSON), default=list)

    # ── relationships bidirecionais ──
    estatisticas = relationship(
        "EstatisticasJogador", back_populates="jogador", uselist=False
    )
    missoes = relationship("Missao", back_populates="jogador")


class Aventura(Base):
    __tablename__ = "aventuras"
    id = Column(String(50), primary_key=True)
    nome = Column(String(100))
    prologo = Column(Text)


class CampanhaWeb(ReprMixin, Base):
    __tablename__ = "campanhas"
    __repr_fields__ = ("party_id", "host_id", "cena_atual")

    party_id = Column(String(50), primary_key=True, index=True)
    host_id = Column(String(20), nullable=False)
    aventura_ativa = Column(String(50), default="cidadela")

    estado_salas = Column(MutableDict.as_mutable(JSON), default=dict)
    ultimo_evento = Column(MutableDict.as_mutable(JSON), default=dict)
    momento = Column(String(50), default="inicio")
    tensao = Column(Integer, default=0)
    turno_atual = Column(Integer, default=1)

    em_combate = Column(Boolean, default=False)
    fila_iniciativa = Column(MutableList.as_mutable(JSON), default=list)
    indice_turno = Column(Integer, default=0)

    cena_atual = Column(String(50), default="taverna")
    cena_anterior = Column(String(50), nullable=True)
    status = Column(String(50), default="exploracao")
    votos_destino = Column(MutableDict.as_mutable(JSON), default=dict)

    bolsa_da_party = Column(MutableDict.as_mutable(JSON), default=lambda: {"ouro": 0, "itens": []})


class Encontro(ReprMixin, Base):
    __tablename__ = "encontros"
    __repr_fields__ = ("id", "cod_sala", "nome_inimigo")

    id = Column(Integer, primary_key=True)
    cod_sala = Column(String(50), ForeignKey("cenas.cod_sala"), index=True)
    nome_inimigo = Column(String(100))
    quantidade = Column(Integer)
    condicao_aparecimento = Column(String(50), default="sempre")
    ativo = Column(Boolean, default=True)
    multiplicador_ameaca = Column(Integer, default=1)

    cena = relationship("Cena", back_populates="encontros")


class Inimigo(ReprMixin, Base):
    __tablename__ = "inimigos"
    __repr_fields__ = ("id", "nome", "hp_max", "ca")

    id = Column(Integer, primary_key=True)
    nome = Column(String(100), unique=True, index=True, nullable=False)
    hp_max = Column(Integer)
    ca = Column(Integer)
    ataque = Column(String(255))
    dano = Column(String(50))
    imagem_url = Column(String(255), nullable=True)
    xp_recompensa = Column(Integer, default=50)
    ouro_recompensa = Column(Integer, default=5)

    is_boss = Column(Boolean, default=False)
    fase_atual = Column(Integer, default=1)
    loot_especial = Column(MutableList.as_mutable(JSON), default=list)

    tipo_dano_padrao = Column(String(50), default="contundente")
    resistencias = Column(MutableList.as_mutable(JSON), default=list)
    vulnerabilidades = Column(MutableList.as_mutable(JSON), default=list)
    imunidades = Column(MutableList.as_mutable(JSON), default=list)


class Cena(ReprMixin, Base):
    __tablename__ = "cenas"
    __repr_fields__ = ("cod_sala", "nome_sala")

    cod_sala = Column(String(50), primary_key=True)
    nome_sala = Column(String(150))
    descricao_visual = Column(Text)
    conexoes = Column(MutableDict.as_mutable(JSON))
    imagem_url = Column(String(255), nullable=True)
    loot_fixo = Column(MutableList.as_mutable(JSON), default=list)
    hazards = Column(MutableList.as_mutable(JSON), default=list)

    # ── relationships bidirecionais ──
    encontros = relationship("Encontro", back_populates="cena")
    npcs = relationship("Npc", back_populates="cena")
    interativos = relationship("Interativo", back_populates="cena")


class Interativo(Base):
    __tablename__ = "interativos"
    id = Column(Integer, primary_key=True)
    cod_sala = Column(String(50), ForeignKey("cenas.cod_sala"), index=True)
    nome = Column(String(100))
    descricao = Column(Text)
    tipo = Column(String(50))
    cd_teste = Column(Integer, default=10)
    atributo_teste = Column(String(10), default="DEX")
    recompensa = Column(MutableList.as_mutable(JSON), default=list)
    dano_falha = Column(Integer, default=0)
    ativo = Column(Boolean, default=True)

    cena = relationship("Cena", back_populates="interativos")


class ObjetoDestrutivel(Base):
    __tablename__ = "objetos_destrutiveis"
    id = Column(Integer, primary_key=True)
    cod_sala = Column(String(50), ForeignKey("cenas.cod_sala"), index=True)
    nome = Column(String(100))
    descricao = Column(Text)
    hp_atual = Column(Integer)
    hp_max = Column(Integer)
    ca = Column(Integer, default=10)
    break_threshold = Column(Integer, default=0)
    resistencias = Column(MutableList.as_mutable(JSON), default=list)
    vulnerabilidades = Column(MutableList.as_mutable(JSON), default=list)
    recompensa_ao_destruir = Column(MutableList.as_mutable(JSON), default=list)
    ativo = Column(Boolean, default=True)


class EstatisticasJogador(Base):
    __tablename__ = "estatisticas_jogadores"
    jogador_telefone = Column(String(20), ForeignKey("jogadores.telefone"), primary_key=True)
    inimigos_derrotados = Column(Integer, default=0)
    danos_causados_total = Column(Integer, default=0)
    danos_recebidos_total = Column(Integer, default=0)
    vezes_derrotado = Column(Integer, default=0)
    total_ataques_acertados = Column(Integer, default=0)
    total_ataques_errados = Column(Integer, default=0)
    criticos_acertados = Column(Integer, default=0)
    fumbles_rolados = Column(Integer, default=0)
    salas_visitadas = Column(MutableList.as_mutable(JSON), default=list)
    salas_desbloqueadas_count = Column(Integer, default=0)
    xp_ganho_total = Column(Integer, default=0)
    ouro_ganho_total = Column(Integer, default=0)
    ouro_perdido_total = Column(Integer, default=0)
    testes_realizados = Column(Integer, default=0)
    testes_sucesso = Column(Integer, default=0)
    testes_falha = Column(Integer, default=0)
    descansos_curtos = Column(Integer, default=0)
    intervencoes_divinas = Column(Integer, default=0)
    primeira_sessao = Column(String(30), nullable=True)
    ultima_sessao = Column(String(30), nullable=True)
    tempo_jogo_minutos = Column(Integer, default=0)

    # ── relationship bidirecional ──
    jogador = relationship("JogadorWeb", back_populates="estatisticas")


class HistoricoPartida(Base):
    __tablename__ = "historico_partidas"
    id = Column(Integer, primary_key=True)
    jogador_telefone = Column(String(20), ForeignKey("jogadores.telefone"), index=True, nullable=False)
    data_inicio = Column(String(30))
    data_fim = Column(String(30), nullable=True)
    resultado = Column(String(50))
    inimigos_derrotados = Column(Integer, default=0)
    ouro_coletado = Column(Integer, default=0)
    xp_ganho = Column(Integer, default=0)
    sala_final = Column(String(50))
    causa_morte = Column(String(255), nullable=True)


class Missao(Base):
    __tablename__ = "missoes"
    id = Column(Integer, primary_key=True)
    jogador_telefone = Column(String(20), ForeignKey("jogadores.telefone"), index=True)
    party_id = Column(String(50), ForeignKey("campanhas.party_id"), index=True)
    npc_nome = Column(String(100))
    titulo = Column(String(150))
    descricao = Column(Text)
    tipo = Column(String(50), default="coleta")
    objetivo_item = Column(String(100))
    objetivo_quantidade = Column(Integer, default=1)
    objetivo_atual = Column(String(100), nullable=True)
    progresso = Column(Integer, default=0)
    objetivo_total = Column(Integer, default=1)
    recompensa_xp = Column(Integer, default=0)
    recompensa_ouro = Column(Integer, default=0)
    recompensa_item = Column(String(100), nullable=True)
    concluida = Column(Boolean, default=False)
    data_conclusao = Column(String(30), nullable=True)

    # ── relationship bidirecional ──
    jogador = relationship("JogadorWeb", back_populates="missoes")


class Npc(ReprMixin, Base):
    __tablename__ = "npcs"
    __repr_fields__ = ("id", "cod_sala", "nome")

    id = Column(Integer, primary_key=True)
    cod_sala = Column(String(50), ForeignKey("cenas.cod_sala"), index=True)
    nome = Column(String(100))
    descricao = Column(Text)
    dialogo_base = Column(Text)
    dialogo_item_especial = Column(Text, nullable=True)
    item_gatilho = Column(String(100), nullable=True)

    cena = relationship("Cena", back_populates="npcs")


class EncontroAleatorio(Base):
    __tablename__ = "encontros_aleatorios"
    id = Column(Integer, primary_key=True)
    cod_sala = Column(String(50), ForeignKey("cenas.cod_sala"), index=True)
    nome_inimigo = Column(String(100))
    quantidade = Column(Integer)
    chance = Column(Integer, default=100)


# ════════════════════════════════════════════════════════════════════════
# HELPERS DE CONVERSÃO (SQLAlchemy → dict compatível engine)
# ════════════════════════════════════════════════════════════════════════

def jogador_to_dict(j: JogadorWeb) -> Dict[str, Any]:
    """Converte JogadorWeb para dict compatível com combat_logic/game_helpers."""
    return {
        "telefone": j.telefone, "party_id": j.party_id, "nome": j.nome,
        "raca": j.raca, "classe": j.classe, "background": j.background,
        "sexo": j.sexo, "nivel": j.nivel, "xp": j.xp,
        "hp_atual": j.hp_atual, "hp_maximo": j.hp_maximo,
        "str_val": j.str_val, "mod_str": j.mod_str,
        "dex_val": j.dex_val, "mod_dex": j.mod_dex,
        "con_val": j.con_val, "mod_con": j.mod_con,
        "int_val": j.int_val, "mod_int": j.mod_int,
        "wis_val": j.wis_val, "mod_wis": j.mod_wis,
        "cha_val": j.cha_val, "mod_cha": j.mod_cha,
        "modificador_ataque": j.modificador_ataque,
        "modificador_defesa": j.modificador_defesa,
        "proficiencia": j.proficiencia,
        "gold": j.gold,
        "inventario": list(j.inventario) if j.inventario else [],
        "arma_equipada": j.arma_equipada,
        "armadura_equipada": j.armadura_equipada,
        "dano_dado": j.dano_dado,
        "mod_dano": j.mod_dano,
        "slots_magia": j.slots_magia,
        "slots_magia_max": j.slots_magia_max,
        "hit_dice_atual": j.hit_dice_atual,
        "hit_dice_max": j.hit_dice_max,
        "status_efeitos": list(j.status_efeitos) if j.status_efeitos else [],
        "resistencias": list(j.resistencias) if j.resistencias else [],
        "vulnerabilidades": list(j.vulnerabilidades) if j.vulnerabilidades else [],
        "imunidades": list(j.imunidades) if j.imunidades else [],
        "cena_atual": j.cena_atual,
        "cena_anterior": j.cena_anterior,
    }


def campanha_to_dict(c: CampanhaWeb) -> Dict[str, Any]:
    return {
        "party_id": c.party_id, "host_id": c.host_id,
        "cena_atual": c.cena_atual, "estado_salas": dict(c.estado_salas) if c.estado_salas else {},
        "momento": c.momento, "tensao": c.tensao,
        "turno_atual": c.turno_atual, "em_combate": c.em_combate,
    }


# Colunas conhecidas dos models (evita setar atributos fantasma via setattr).
# Calculado uma única vez no import (frozenset imutável).
_KNOWN_COLS_JOGADOR = frozenset(
    {c.name for c in JogadorWeb.__table__.columns} | {"telefone"}
)
_KNOWN_COLS_CAMPANHA = frozenset(
    {c.name for c in CampanhaWeb.__table__.columns}
)
# Colunas protegidas: nunca sobrescrever via setattr (PKs).
_PROTECTED_COLS_JOGADOR = frozenset({"telefone"})
_PROTECTED_COLS_CAMPANHA = frozenset({"party_id", "host_id"})


def dict_to_jogador(d: Dict[str, Any], existing: Optional[JogadorWeb] = None) -> JogadorWeb:
    """Cria/atualiza JogadorWeb a partir de dict do engine.

    Ignora chaves que não correspondem a colunas conhecidas do model e
    protege a chave primária (telefone) de ser sobrescrita via setattr.
    """
    _list_keys = {"inventario", "status_efeitos", "resistencias", "vulnerabilidades", "imunidades"}
    j = existing or JogadorWeb(telefone=d["telefone"])
    for key, value in d.items():
        if key not in _KNOWN_COLS_JOGADOR:
            continue
        if key in _PROTECTED_COLS_JOGADOR:
            continue
        if key in _list_keys:
            setattr(j, key, value or [])
        else:
            setattr(j, key, value)
    return j


def dict_to_campanha(d: Dict[str, Any], existing: Optional[CampanhaWeb] = None) -> CampanhaWeb:
    """Cria/atualiza CampanhaWeb a partir de dict do engine.

    Ignora chaves que não correspondem a colunas conhecidas do model e
    protege as chaves primárias (party_id, host_id) de serem sobrescritas.
    """
    _dict_keys = {"estado_salas", "ultimo_evento", "votos_destino", "bolsa_da_party"}
    _list_keys = {"fila_iniciativa"}
    c = existing or CampanhaWeb(party_id=d["party_id"], host_id=d["host_id"])
    for key, value in d.items():
        if key not in _KNOWN_COLS_CAMPANHA:
            continue
        if key in _PROTECTED_COLS_CAMPANHA:
            continue
        if key in _dict_keys:
            setattr(c, key, value or {})
        elif key in _list_keys:
            setattr(c, key, value or [])
        else:
            setattr(c, key, value)
    return c


# Export all models for convenience
__all__ = [
    "Base", "engine", "SessionLocal", "init_db", "get_db", "ReprMixin",
    "JogadorWeb", "CampanhaWeb", "Aventura",
    "Encontro", "Inimigo", "Cena", "Interativo", "ObjetoDestrutivel",
    "EstatisticasJogador", "HistoricoPartida", "Missao", "Npc", "EncontroAleatorio",
    "jogador_to_dict", "campanha_to_dict", "dict_to_jogador", "dict_to_campanha",
]