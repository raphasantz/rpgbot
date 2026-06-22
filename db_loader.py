"""
db_loader.py — Carrega os JSONs exportados do banco em memória.

PROTÓTIPO CTk: lê de .json em vez de SQL.
Quando o bot Telegram subir, o mesmo código aponta pro SQLAlchemy.

A estrutura dos dados (cod_sala, nome_inimigo, etc.) bate com os models.py
do bot — então a UI fala a mesma língua que o backend oficial.
"""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Optional


# Onde estão os JSONs exportados
DATA_DIR = Path(__file__).parent / "db_export"


def _load(name: str) -> list:
    """Carrega um JSON e retorna a lista. Se arquivo vazio/inválido, retorna []."""
    path = DATA_DIR / name
    if not path.exists():
        print(f"[db_loader] ⚠️  {name} não encontrado em {DATA_DIR}")
        return []
    with open(path, encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            return []
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"[db_loader] ❌ JSON inválido em {name}: {e}")
            return []


# ── DADOS CARREGADOS UMA VEZ NO IMPORT ─────────────────────────────────────────
# (Reload via reload() se tu editar o JSON em runtime.)

CENAS: dict[str, dict] = {}              # cod_sala -> cena
INIMIGOS: dict[str, dict] = {}           # nome -> bestiario
NPCS: dict[str, dict] = {}               # nome -> npc
AVENTURAS: dict[str, dict] = {}          # id -> aventura
CAMPANHAS: list[dict] = []               # lista de campanhas ativas

# Encontros (inimigo spawnado por sala). Não tem JSON exportado, então
# a gente HARDCODA aqui as salas que têm encontro, baseado no setup_oficial.py
# (que o Rafael mencionou que popula o banco). É só placeholder — no MVP,
# cada sala de masmorra tem 30% de chance de ter 1-3 monstros.

ENCONTROS_POR_SALA: dict[str, list[dict]] = {
    # DEPRECATED: usar tabela Encontro do SQLAlchemy via get_encontros_vivos_sync()
    # cod_sala -> lista de encontros (cada um é um dict com nome_inimigo, quantidade)
    "sala_01": [{"nome_inimigo": "Rato Atroz", "quantidade": 2}],
    "sala_03": [{"nome_inimigo": "Kobold Sentinela", "quantidade": 3}],
    # ... completa conforme for populando
}

# Mapa: NPC -> palavras-chave da raça para detectar presença na descrição
# da cena. Definido no nível do módulo para evitar recriação a cada chamada
# de get_npc_da_cena().
KEYWORDS_NPC: dict[str, list[str]] = {
    "Meepo": ["meepo", "kobold", "calcryx", "dragão"],
    "Erky Timbers": ["erky", "gnomo", "clérigo", "prisioneiro"],
    "Sharwyn Hucrele": ["sharwyn", "mag", "árvore", "gulthias", "varinha"],
}


def _slugify(text: str) -> str:
    """Normaliza texto para slug ASCII (sem acentos), lowercase com underscores."""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_text = nfkd.encode("ascii", "ignore").decode("ascii")
    return ascii_text.lower().replace(" ", "_")


def _init():
    """Popula os dicts acima. Chamado uma vez no import."""
    for c in _load("aventura_cidadela.json"):
        cod_sala = c.get("cod_sala")
        if cod_sala:
            CENAS[cod_sala] = c
    for i in _load("bestiario_cidadela.json"):
        nome = i.get("nome")
        if nome:
            INIMIGOS[nome] = i
    for n in _load("aliados_e_npcs.json"):
        if "id" not in n:
            nome = n.get("nome")
            if nome:
                n["id"] = _slugify(nome)
        nome_npc = n.get("nome")
        if nome_npc:
            NPCS[nome_npc] = n
    for a in _load("aventuras.json"):
        aid = a.get("id")
        if aid:
            AVENTURAS[aid] = a
    global CAMPANHAS
    CAMPANHAS = _load("campanhas.json")


_init()


def reload() -> None:
    """Recarrega os JSONs em memória (limpa e repopula os dicts).

    Útil quando os arquivos de ``db_export`` são editados em runtime.
    Era prometida nos comentários do módulo mas não existia.
    """
    CENAS.clear()
    INIMIGOS.clear()
    NPCS.clear()
    AVENTURAS.clear()
    global CAMPANHAS
    CAMPANHAS = []
    _init()


# ── API DE CONSULTA ─────────────────────────────────────────────────────────────

def get_cena(cod_sala: str) -> Optional[dict]:
    """Retorna a cena (dict com cod_sala, nome_sala, descricao_visual, conexoes, etc.) ou None."""
    return CENAS.get(cod_sala)


def get_inimigo(nome: str) -> Optional[dict]:
    """Retorna o bestiário (dict com ca, hp_max, ataque, dano, etc.) ou None."""
    return INIMIGOS.get(nome)


def get_npc(nome: str) -> Optional[dict]:
    return NPCS.get(nome)


def get_npc_da_cena(cod_sala: str) -> Optional[dict]:
    """
    Procura qual NPC está presente na cena atual.
    1. Verifica se algum NPC tem localizacao == cod_sala
    2. Faz busca por nome OU por keywords da raça nas descrições
    3. Fallback: NPCs genéricos por tipo de sala (ex: taverneiro em carvalhal)
    Retorna o dict do NPC ou None.
    """
    # 1. Verifica localizacao exata do NPC
    for nome, npc in NPCS.items():
        if npc.get("localizacao") == cod_sala:
            return npc
    
    cena = CENAS.get(cod_sala)
    if not cena:
        return None
    # monta texto da cena pra buscar
    texto_cena = " ".join(str(p) for p in [
        cena.get("descricao_visual", ""),
        cena.get("descricao_narrativa", ""),
        cena.get("nome_sala", ""),
        cena.get("segredos_mestre", ""),
    ]).lower()
    # primeiro tenta match exato por nome
    for nome, npc in NPCS.items():
        if nome.lower() in texto_cena:
            return npc
    # depois tenta por keywords (KEYWORDS_NPC definido no nível do módulo)
    for nome, npc in NPCS.items():
        keywords = KEYWORDS_NPC.get(nome, [])
        for kw in keywords:
            if kw in texto_cena:
                return npc
    
    # 3. Fallback: NPCs genéricos por sala
    if cod_sala in ["carvalhal", "taverna"]:
        # Taverneiro genérico da Vila de Carvalhal
        return {
            "id": "taverneiro",
            "nome": "Taverneiro do Velho Javali",
            "descricao": "O dono da taverna, um homem robusto de avental de couro, seca um copo com um pano surrado.",
            "dialogo_inicial": "Bem-vindo à Taverna do Velho Javali. O que vai ser? Temos cerveja, hidromel e um ensopado que esquenta até osso.",
            "opcoes_dialogo": ["Pedir bebida", "Perguntar sobre rumores", "Alugar quarto", "Sair"],
            "missao": None,
            "itens_venda": [],
            "servicos": ["hospedagem", "comida", "bebida", "rumores"],
            "localizacao": "carvalhal",
            "amigavel": True,
        }
    
    return None


def get_aventura(aventura_id: str) -> Optional[dict]:
    return AVENTURAS.get(aventura_id)


def get_encontros_vivos(cod_sala: str, estado_salas: dict) -> list[dict]:
    """
    Retorna os encontros da sala que ainda não foram derrotados.
    O `estado_salas` é o dict que o jogador tem salvo (do modelo Campanha).
    No MVP, estado_salas vive em memória dentro do pygame_ui.py.
    """
    encontros = ENCONTROS_POR_SALA.get(cod_sala, [])
    return [e for e in encontros if not estado_salas.get(f"derrotado_{e['nome_inimigo']}")]


# ── DEBUG ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Cenas carregadas: {len(CENAS)}")
    print(f"Inimigos: {len(INIMIGOS)}")
    print(f"NPCs: {len(NPCS)}")
    print(f"Aventuras: {len(AVENTURAS)}")
    print()
    print("Primeira sala:", list(CENAS.keys())[:3])
    print()
    print("Exemplo - Vila de Carvalhal:")
    c = get_cena("carvalhal")
    if c:
        print(f"  nome: {c['nome_sala']}")
        print(f"  conexões: {c['conexoes']}")
        print(f"  descrição: {c['descricao_visual'][:80]}...")
