"""
ui_utils.py — Constantes, utilitários de UI e helpers do inventário.
Importado pelo main.py para manter o arquivo de rotas limpo.
"""
import hashlib
import json
import math
import random
import re
from collections import Counter

try:
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
except ImportError:
    ReplyKeyboardMarkup = KeyboardButton = ReplyKeyboardRemove = InlineKeyboardMarkup = InlineKeyboardButton = None

# Import local movido para o topo (try/except) — evita reimportar a cada
# chamada de processar_saque e mantém o módulo carregável mesmo se as
# dependências (openai/dotenv) não estiverem instaladas.
try:
    from ai_engine_web import extrair_itens_da_narracao
except ImportError:
    extrair_itens_da_narracao = None

# Constantes D&D 5e — fonte canônica em dnd_5e_rules.py (evita duplicação).
# Reexportadas aqui para manter compatibilidade com código que faz
# `from ui_utils import PERICIAS_DND_5E` (ex.: action_resolver.py).
from dnd_5e_rules import (
    CONDICOES_DND_5E,
    TIPOS_DANO,
    ACOES_COMBATE,
    COBERTURA_BONUS,
    TERRENOS,
    PERICIAS_DND_5E,
    PERICIAS_POR_ATRIBUTO,
)

def gerar_callback_safe(prefixo: str, nome_item: str) -> str:
    """
    Gera um callback_data compacto de até 64 caracteres limitados pelo Telegram,
    using um hash MD5 dos últimos caracteres para evitar colisões.
    Ex: buy_pocao_de_cura_maior_a8f1
    """
    nome_limpo = nome_item.lower().replace(" ", "_").replace("⚡", "").replace("🧪", "").strip()
    nome_truncado = nome_limpo[:25]
    hash_checksum = hashlib.md5(nome_item.encode('utf-8')).hexdigest()[:4]
    return f"{prefixo}_{nome_truncado}_{hash_checksum}"


# ── Tabelas de progressão ──────────────────────────────────────────────────────
XP_POR_NIVEL = {
    1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500,
    6: 14000, 7: 23000, 8: 34000, 9: 48000, 10: 64000,
    11: 85000, 12: 100000, 13: 120000, 14: 140000, 15: 165000,
    16: 195000, 17: 225000, 18: 265000, 19: 305000, 20: 355000
}

HP_POR_CLASSE = {
    "Bárbaro": 12, "Guerreiro": 10, "Paladino": 10, "Patrulheiro": 10,
    "Bardo": 8, "Clérigo": 8, "Druida": 8, "Monge": 8, "Ladino": 8, "Bruxo": 8,
    "Feiticeiro": 6, "Mago": 6, "Artífice": 8
}

INVENTARIO_POR_CLASSE = {
    "Patrulheiro":  ["Armadura de Couro", "Arco Longo", "20 Flechas", "2 Espadas Curtas", "Pacote de Explorador"],
    "Guerreiro":    ["Cota de Malha", "Espada Longa", "Escudo", "Besta Leve", "Pacote de Masmorra"],
    "Mago":         ["Grimório", "Foco Arcano", "Adaga", "Pacote de Estudioso"],
    "Ladino":       ["Armadura de Couro", "2 Adagas", "Rapieira", "Arco Curto", "Ferramentas de Ladrão"],
    "Clérigo":      ["Cota de Malha", "Maça", "Escudo", "Símbolo Sagrado", "Pacote de Sacerdote"],
    "Bárbaro":      ["Machado Grande", "2 Machadinhas", "4 Azagaias", "Pacote de Explorador"],
    "Bardo":        ["Armadura de Couro", "Rapieira", "Alaúde", "Pacote de Artista", "Adaga"],
    "Bruxo":        ["Armadura de Couro", "Maça", "Foco Arcano", "Pacote de Estudioso", "2 Adagas"],
    "Druida":       ["Armadura de Couro", "Escudo", "Cimitarra", "Foco Druídico", "Pacote de Explorador"],
    "Feiticeiro":   ["Besta Leve", "20 Virotes", "Foco Arcano", "Pacote de Aventureiro", "2 Adagas"],
    "Monge":        ["Espada Curta", "Pacote de Explorador", "10 Dardos"],
    "Paladino":     ["Cota de Malha", "Espada Longa", "Escudo", "5 Azagaias", "Símbolo Sagrado", "Pacote de Sacerdote"],
    "Artífice":     ["Armadura de Couro", "Besta Leve", "20 Virotes", "Ferramentas de Artesão", "Pacote de Estudioso", "2 Adagas"]
}

# ── Dicionários de Dados do Jogo ────────────────────────────────────────────────
# PERÍCIAS COMPLETAS D&D 5E (18 perícias oficiais)
BACKGROUND_SKILLS = {
    "Acólito": ["Religião", "Intuição"],
    "Criminoso": ["Furtividade", "Enganação"],
    "Herói do Povo": ["Adestrar Animais", "Sobrevivência"],
    "Nobre": ["História", "Persuasão"],
    "Sábio": ["Arcanismo", "História"],
    "Soldado": ["Atletismo", "Intimidação"],
    "Forasteiro": ["Atletismo", "Sobrevivência"],
    "Artesão de Guilda": ["Persuasão", "Percepção"]
}

# NOTE: PERICIAS_DND_5E e PERICIAS_POR_ATRIBUTO agora vivem em dnd_5e_rules.py
# (fonte canônica) e são importadas/reexportadas no topo deste módulo.

# Ordem: STR, DEX, CON, INT, WIS, CHA
BONUS_RACA = {
    "Humano": [1, 1, 1, 1, 1, 1],
    "Elfo": [0, 2, 0, 0, 0, 0],
    "Anão": [0, 0, 2, 0, 0, 0],
    "Halfling": [0, 2, 0, 0, 0, 0],
    "Draconato": [2, 0, 0, 0, 0, 1],
    "Meio-Orc": [2, 0, 1, 0, 0, 0],
    "Meio-Elfo": [0, 1, 1, 0, 0, 2], # Simplificado: +2 CHA, +1 DEX, +1 CON
    "Tiefling": [0, 0, 0, 1, 0, 2],
    "Gnomo": [0, 0, 0, 2, 0, 0]
}

LOJA_CARVALHAL = {
    "Poção de Cura": {"preco": 50, "tipo": "pocao", "dano": "2d4+2", "descricao": "Recupera 2d4+2 HP"},
    "Poção de Cura Maior": {"preco": 150, "tipo": "pocao", "dano": "4d4+4", "descricao": "Recupera 4d4+4 HP"},
    "Poção de Cura Superior": {"preco": 1000, "tipo": "pocao", "dano": "8d4+8", "descricao": "Recupera 8d4+8 HP"},
    "Poção de Cura Suprema": {"preco": 5000, "tipo": "pocao", "dano": "10d4+20", "descricao": "Recupera 10d4+20 HP"},
    "Antídoto": {"preco": 50, "tipo": "pocao", "descricao": "Remove efeitos de envenenamento e toxinas"},
    "Adaga": {"preco": 2, "tipo": "arma", "dano": "1d4", "descricao": "Dano 1d4 (Leve, Acuidade)"},
    "Lança": {"preco": 1, "tipo": "arma", "dano": "1d6", "descricao": "Dano 1d6 (Arremesso)"},
    "Maça": {"preco": 5, "tipo": "arma", "dano": "1d6", "descricao": "Dano 1d6"},
    "Espada Curta": {"preco": 10, "tipo": "arma", "dano": "1d6", "descricao": "Dano 1d6 (Leve, Acuidade)"},
    "Machado de Batalha": {"preco": 10, "tipo": "arma", "dano": "1d8", "descricao": "Dano 1d8 (Versátil)"},
    "Espada Longa": {"preco": 15, "tipo": "arma", "dano": "1d8", "descricao": "Dano 1d8 (Versátil)"},
    "Alabarda": {"preco": 20, "tipo": "arma", "dano": "1d10", "descricao": "Dano 1d10 (Alcance, Duas mãos)"},
    "Arco Curto": {"preco": 25, "tipo": "arma", "dano": "1d6", "descricao": "Dano 1d6 (Distância)"},
    "Rapieira": {"preco": 25, "tipo": "arma", "dano": "1d8", "descricao": "Dano 1d8 (Acuidade)"},
    "Espada Grande": {"preco": 50, "tipo": "arma", "dano": "2d6", "descricao": "Dano 2d6 (Duas mãos, Pesada)"},
    "Corda de Cânhamo (15m)": {"preco": 1, "tipo": "equipamento", "descricao": "Útil para travessias e abismos"},
    "Cantil": {"preco": 1, "tipo": "equipamento", "descricao": "Recipiente para água potável"},
    "Pacote de Tochas (10)": {"preco": 1, "tipo": "equipamento", "descricao": "Ilumina masmorras (Pacote c/ 10)"},
    "Rações (5 dias)": {"preco": 2, "tipo": "equipamento", "descricao": "Comida de viagem (Pacote p/ 5 dias)"},
    "Mochila": {"preco": 2, "tipo": "equipamento", "descricao": "Transporta mais items"},
    "Corda de Seda (15m)": {"preco": 10, "tipo": "equipamento", "descricao": "Resistente e leve"},
    "Kit de Aventureiro": {"preco": 15, "tipo": "equipamento", "descricao": "Ferramentas vitais de exploração"},
    "Armadura de Couro": {"preco": 10, "tipo": "armadura", "subtipo": "leve", "ca_base": 11, "descricao": "CA 11 + Mod DEX (Armadura Leve)"},
    "Peitoral de Aço": {"preco": 400, "tipo": "armadura", "subtipo": "media", "ca_base": 14, "descricao": "CA 14 + Mod DEX [Máx +2] (Armadura Média)"},
    "Cota de Malha": {"preco": 75, "tipo": "armadura", "subtipo": "pesada", "ca_base": 16, "descricao": "CA 16 (Armadura Pesada)"},
    "Escudo": {"preco": 10, "tipo": "armadura", "subtipo": "escudo", "ca_base": 2, "descricao": "+2 na CA (Equipado na mão secundária)"}
}

ARMAS_DB = {
    "Desarmado": {"dano": "1d1", "atributo": "STR"},
    "Soco": {"dano": "1d1", "atributo": "STR"},
    "Punhos": {"dano": "1d1", "atributo": "STR"},
    "Adaga": {"dano": "1d4", "atributo": "FINESSE"},
    "Azagaia": {"dano": "1d6", "atributo": "STR"},
    "Bastão": {"dano": "1d6", "atributo": "STR"},
    "Clava": {"dano": "1d4", "atributo": "STR"},
    "Clube": {"dano": "1d4", "atributo": "STR"},
    "Grande Clube": {"dano": "1d8", "atributo": "STR"},
    "Foice": {"dano": "1d4", "atributo": "STR"},
    "Lança": {"dano": "1d6", "atributo": "STR"},
    "Maça": {"dano": "1d6", "atributo": "STR"},
    "Machadinha": {"dano": "1d6", "atributo": "STR"},
    "Machado de Mão": {"dano": "1d6", "atributo": "STR"},
    "Martelo Leve": {"dano": "1d4", "atributo": "STR"},
    "Arco Curto": {"dano": "1d6", "atributo": "DEX"},
    "Besta Leve": {"dano": "1d8", "atributo": "DEX"},
    "Dardo": {"dano": "1d4", "atributo": "FINESSE"},
    "Funda": {"dano": "1d4", "atributo": "DEX"},
    "Estilingue": {"dano": "1d4", "atributo": "DEX"},
    "Alabarda": {"dano": "1d10", "atributo": "STR"},
    "Chicote": {"dano": "1d4", "atributo": "FINESSE"},
    "Cimitarra": {"dano": "1d6", "atributo": "FINESSE"},
    "Espada Curta": {"dano": "1d6", "atributo": "FINESSE"},
    "Espada Grande": {"dano": "2d6", "atributo": "STR"},
    "Espada Longa": {"dano": "1d8", "atributo": "STR"},
    "Estrela da Manhã": {"dano": "1d8", "atributo": "STR"},
    "Gládio": {"dano": "1d10", "atributo": "STR"},
    "Machado de Batalha": {"dano": "1d8", "atributo": "STR"},
    "Machado Grande": {"dano": "1d12", "atributo": "STR"},
    "Grande Machado": {"dano": "1d12", "atributo": "STR"},
    "Marreta": {"dano": "2d6", "atributo": "STR"},
    "Maul": {"dano": "2d6", "atributo": "STR"},
    "Martelo de Guerra": {"dano": "1d8", "atributo": "STR"},
    "Warhammer": {"dano": "1d8", "atributo": "STR"},
    "Picareta de Guerra": {"dano": "1d8", "atributo": "STR"},
    "Escolha de Guerra": {"dano": "1d8", "atributo": "STR"},
    "Pique": {"dano": "1d10", "atributo": "STR"},
    "Rapieira": {"dano": "1d8", "atributo": "FINESSE"},
    "Espada": {"dano": "1d8", "atributo": "FINESSE"},
    "Tridente": {"dano": "1d6", "atributo": "STR"},
    "Arco Longo": {"dano": "1d8", "atributo": "DEX"},
    "Besta de Mão": {"dano": "1d6", "atributo": "DEX"},
    "Besta Pesada": {"dano": "1d10", "atributo": "DEX"},
    "Zarabatana": {"dano": "1d1", "atributo": "DEX"}
}

MAGIAS_POR_CLASSE = {
    "mago": {"nome": "Rajada Arcana", "dano": "1d10", "icone": "☄️", "aoe": False},
    "feiticeiro": {"nome": "Raio de Fogo", "dano": "1d10", "icone": "🔥", "aoe": False},
    "bruxo": {"nome": "Rajada Mística", "dano": "1d10", "icone": "🟣", "aoe": False},
    "clérigo": {"nome": "Chama Sagrada", "dano": "1d8", "icone": "✨", "aoe": False},
    "druida": {"nome": "Chicote de Espinhos", "dano": "1d6", "icone": "🌿", "aoe": False},
    "bardo": {"nome": "Onda Trovejante", "dano": "2d8", "icone": "🎵", "aoe": True},
    "paladino": {"nome": "Destruição Divina", "dano": "2d8", "icone": "⚔️✨", "aoe": False},
    "patrulheiro": {"nome": "Marca do Caçador", "dano": "1d6", "icone": "🏹", "aoe": False},
    "artífice": {"nome": "Raio de Fogo", "dano": "1d10", "icone": "⚙️", "aoe": False},
    "default": {"nome": "Projétil Mágico", "dano": "1d8", "icone": "🔮", "aoe": False}
}

IMAGENS_INIMIGOS = {
    "Rato Atroz":               "https://orbedosdragoes.com/wp-content/uploads/2015/02/rato-atroz.jpg",
    "Ramo Seco":                "https://dragoesdosreinos.wordpress.com/wp-content/uploads/2009/05/ramoseco.jpg",
    "Kobold Sentinela":         "https://draconusdictum.wordpress.com/wp-content/uploads/2006/12/kobold.jpg",
    "Goblin Saqueador":         "https://cdn.cardsrealm.com/images/cartas/7ed-seventh-edition/en/crop-med/goblin-raider-192.jpeg",
    "Goblin Guerreiro":         "https://nadaqueteinteresse.weebly.com/uploads/8/1/7/1/8171548/3847330.jpg",
    "Robgoblin Guerreiro":      "https://i.pinimg.com/736x/ba/fb/b0/bafbb04718f0898188d009fa01bafb9f.jpg",
    "Bugbear Jardineiro":       "https://media-waterdeep.cursecdn.com/avatars/thumbnails/0/291/1000/1000/636252772552775032.jpeg",
    "Esqueleto":                "https://media-waterdeep.cursecdn.com/avatars/thumbnails/16/471/1000/1000/636376289069650058.jpeg",
    "Esqueleto Arqueiro":       "https://media-waterdeep.cursecdn.com/avatars/thumbnails/16/471/1000/1000/636376289069650058.jpeg",
    "Esqueleto Guardião":       "https://media-waterdeep.cursecdn.com/avatars/thumbnails/16/471/1000/1000/636376289069650058.jpeg",
    "Durnn (Chefe Goblin)":     "https://media-waterdeep.cursecdn.com/avatars/thumbnails/0/353/1000/1000/636252777935400263.jpeg",
    "Jot (Quasit)":             "https://i.pinimg.com/originals/ce/ee/b2/ceeeb29ecf205ab0348737ccb8314e7a.jpg",
    "Calcryx (Filhote Dragão)": "https://media-waterdeep.cursecdn.com/avatars/thumbnails/0/132/1000/1000/636252755375971485.jpeg",
    "Sir Bradford (Corrompido)":"https://media-waterdeep.cursecdn.com/avatars/thumbnails/16/582/1000/1000/636376342898730999.jpeg",
    "Sharwyn (Corrompida)":     "https://media-waterdeep.cursecdn.com/avatars/thumbnails/16/582/1000/1000/636376342898730999.jpeg",
    "Belak o Proscrito":        "https://media-waterdeep.cursecdn.com/avatars/thumbnails/16/465/1000/1000/636376288647043878.jpeg",
    "Sacerdote-Troll":          "https://media-waterdeep.cursecdn.com/avatars/thumbnails/16/579/1000/1000/636376342502674390.jpeg",
    "Balsag (Bugbear)":         "https://media-waterdeep.cursecdn.com/avatars/thumbnails/0/291/1000/1000/636252772552775032.jpeg",
}

# ── Helpers de atributos ───────────────────────────────────────────────────────
def calcular_modificador(valor: int) -> int:
    return math.floor((valor - 10) / 2)

def rolar_atributo_4d6() -> int:
    dados = [random.randint(1, 6) for _ in range(4)]
    dados.remove(min(dados))
    return sum(dados)

# ── Constantes de cálculo de CA (D&D 5e) ───────────────────────────────────────
CA_BASE_SEM_ARMADURA = 10       # CA base sem armadura (10 + mod DEX)
BONUS_DEX_MAX_ARMADURA_MEDIA = 2  # Bônus máx. de DEX em armadura média
BONUS_ESCUDO_CA = 2             # Bônus de CA concedido por escudo

def calcular_ca_final(jogador, armadura_nome: str) -> int:
    """
    Lógica centralizada de cálculo de CA baseada em D&D 5e.
    Evita repetição de código em menus.py e main.py.
    """
    ca_final = CA_BASE_SEM_ARMADURA
    
    # 1. Busca a armadura na loja/DB
    armadura_dados = None
    for nome, dados in LOJA_CARVALHAL.items():
        if armadura_nome.lower() in nome.lower() and dados.get("tipo") == "armadura":
            armadura_dados = dados
            break
    
    if not armadura_dados:
        return CA_BASE_SEM_ARMADURA + jogador.mod_dex # CA base sem armadura

    subtipo = armadura_dados.get("subtipo")
    ca_base = armadura_dados.get("ca_base", CA_BASE_SEM_ARMADURA)

    if subtipo == "leve":
        ca_final = ca_base + jogador.mod_dex
    elif subtipo == "media":
        ca_final = ca_base + min(BONUS_DEX_MAX_ARMADURA_MEDIA, jogador.mod_dex)
    elif subtipo == "pesada":
        ca_final = ca_base
    else:
        ca_final = ca_base

    # 2. Bônus de Escudo — CRIT-03 FIX: apenas se equipado (não só no inventário)
    if "Escudo" in armadura_nome:
        ca_final += BONUS_ESCUDO_CA
        
    return ca_final

def calcular_modificadores_ataque(jogador, arma_nome: str):
    """
    Lógica centralizada de modificadores de ataque e dano.
    Retorna: (mod_ataque_dano, nome_oficial_arma, dano_dado)
    """
    # Caso especial: Monge Desarmado
    if jogador.classe.lower() == "monge" and arma_nome.lower() in ["desarmado", "soco", "punhos"]:
        if jogador.nivel >= 17:
            dado = "1d10"
        elif jogador.nivel >= 11:
            dado = "1d8"
        elif jogador.nivel >= 5:
            dado = "1d6"
        else:
            dado = "1d4"
        return jogador.mod_dex, "Artes Marciais (Desarmado)", dado

    # Busca arma no DB (prioriza match exato → substring)
    arma_dados = None
    nome_oficial = arma_nome
    # 1) Match exato case-insensitive
    arma_dados_exato = next(
        ((n, d) for n, d in ARMAS_DB.items() if arma_nome.lower() == n.lower()), None
    )
    if arma_dados_exato:
        nome_oficial, arma_dados = arma_dados_exato
    else:
        # 2) Substring — mas só se o nome da arma é MAIS CURTO que o do DB
        #    (evita "Espada" matchar "Espada Curta" em vez de "Espada Longa")
        for nome, dados in ARMAS_DB.items():
            if arma_nome.lower() in nome.lower() and len(arma_nome) <= len(nome):
                arma_dados = dados
                nome_oficial = nome
                break

    if not arma_dados:
        return jogador.mod_str, "Desarmado", "1d1"

    atr = arma_dados["atributo"]
    if atr == "STR":
        mod = jogador.mod_str
    elif atr == "DEX":
        mod = jogador.mod_dex
    elif atr == "FINESSE":
        mod = max(jogador.mod_str, jogador.mod_dex)
    else:
        mod = jogador.mod_str
        
    return mod, nome_oficial, arma_dados["dano"]

# ── Inventário e Saque Inteligente ──────────────────────────────────────────────
def obter_inventario_limpo(inv_bruto) -> list:
    if not inv_bruto:
        return []

    # 1. Já é lista — limpa e retorna
    if isinstance(inv_bruto, list):
        return [str(item).strip() for item in inv_bruto if str(item).strip()]

    # 2. String — tenta JSON primeiro (formato canônico do SQLAlchemy/SQLite)
    if isinstance(inv_bruto, str):
        s = inv_bruto.strip()
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except (json.JSONDecodeError, ValueError):
            pass  # não é JSON válido — cai no fallback de split abaixo

    # 3. Fallback: string que não é JSON — limpa delimitadores e faz split
    inv_str = str(inv_bruto)
    if '\\u' in inv_str or '\\n' in inv_str:
        try:
            inv_str = inv_str.encode('utf-8').decode('unicode_escape')
        except Exception:
            pass

    for char in ['[', ']', '"', "'", '•']:
        inv_str = inv_str.replace(char, '')

    inv_str = inv_str.replace('\\n', ',')
    itens_limpos = []
    for item in inv_str.split(','):
        limpo = item.strip()
        if limpo:
            itens_limpos.append(limpo)

    return itens_limpos

def formatar_inventario_para_display(lista_itens: list) -> str:
    if not lista_itens:
        return "Inventário vazio."

    contagem = Counter(lista_itens)

    linhas = []
    for item, qtd in contagem.items():
        if qtd > 1:
            linhas.append(f"{qtd}x {item}")
        else:
            linhas.append(item)

    return "\n".join(linhas)

def contar_inventario(lista_itens: list) -> dict:
    """Retorna dict {nome_item: quantidade} para uso em APIs JSON."""
    if not lista_itens:
        return {}
    return dict(Counter(str(item).strip() for item in lista_itens if str(item).strip()))

def adicionar_ao_inventario(jogador, novos_itens: list) -> list:
    """
    Adiciona itens ao inventário INDIVIDUAL do jogador.
    Sincronizado com MutableList do models.py.
    """
    itens_adicionados_msg = []
    
    for item in novos_itens:
        item_limpo = str(item).replace("•", "").replace("-", "").strip()
        
        match_ouro = re.search(r'(\d+)\s*(PO|po|gp|peças?\s*(?:de\s*ouro)?|ouro)', item_limpo, re.IGNORECASE)
        if match_ouro:
            quantidade = int(match_ouro.group(1))
            jogador.gold += quantidade
            itens_adicionados_msg.append(f"{quantidade} PO (adicionado à bolsa)") # FIX: Corrigido de formatting_gold_po para quantidade
            continue 
            
        if item_limpo:
            # Graças ao MutableList no models.py, o append é detectado automaticamente
            jogador.inventario.append(item_limpo)
            itens_adicionados_msg.append(item_limpo)
            
    return itens_adicionados_msg

async def processar_saque(message, jogador, narracao: str, db):
    itens = await extrair_itens_da_narracao(narracao)
    if itens:
        itens_reais = adicionar_ao_inventario(jogador, itens)
        # O commit é feito no handler, mas mantemos por segurança se chamado isoladamente
        # await db.commit() 
        lista = ", ".join(itens_reais)
        await message.answer(f"<b>Loot Encontrado!</b> Adicionado: {lista}", parse_mode="HTML")

# ── Loot Dinâmico e Armadilhas ─────────────────────────────────────────────────
# Constantes de chance (percentual, 1-100) para loot de inimigo comum.
LOOT_COMUM_CHANCE_VAZIO = 50    # roll <= 50 -> sem loot
LOOT_COMUM_CHANCE_OURO = 80     # roll <= 80 -> apenas ouro
LOOT_COMUM_CHANCE_ARMA = 95     # roll <= 95 -> arma comum

# Constantes de chance (percentual, 1-100) para loot de baú.
LOOT_BAU_CHANCE_OURO = 40       # roll <= 40 -> apenas ouro
LOOT_BAU_CHANCE_POCAO = 75      # roll <= 75 -> ouro + poção
LOOT_BAU_CHANCE_EQUIP = 95      # roll <= 95 -> ouro + equipamento

def gerar_loot_inimigo_comum() -> list:
    roll = random.randint(1, 100)
    if roll <= LOOT_COMUM_CHANCE_VAZIO:
        return []
    elif roll <= LOOT_COMUM_CHANCE_OURO:
        ouro = random.randint(1, 6)
        return [f"{ouro} PO"]
    elif roll <= LOOT_COMUM_CHANCE_ARMA:
        armas = ["Adaga", "Espada Curta", "Arco Curto", "Machadinha", "Funda"]
        return [random.choice(armas)]
    else:
        return ["Poção de Cura"]

def gerar_loot_bau(nivel=1) -> list:
    roll = random.randint(1, 100)
    ouro = random.randint(10, 50) * nivel
    
    if roll <= LOOT_BAU_CHANCE_OURO:
        return [f"{ouro} PO"]
    elif roll <= LOOT_BAU_CHANCE_POCAO:
        return [f"{ouro} PO", "Poção de Cura"]
    elif roll <= LOOT_BAU_CHANCE_EQUIP:
        equipment = ["Espada Longa", "Machado de Batalha", "Rapieira", "Armadura de Couro", "Corda de Seda (15m)"]
        return [f"{ouro} PO", random.choice(equipment)]
    else:
        return [f"{ouro} PO", "Poção de Cura Maior", "Kit de Aventureiro"]

# ── Teclados e menus ───────────────────────────────────────────────────────────
def _saidas_validas(sala) -> list:
    """Retorna as chaves das conexões válidas (title-cased) de uma sala.

    Compartilhado entre ``texto_saidas`` e ``teclado_saidas`` para evitar
    duplicação da lógica de filtragem de conexões.
    """
    if not sala or not sala.conexoes:
        return []
    return [k.title() for k, v in sala.conexoes.items() if isinstance(v, str) and v.strip()]

def texto_saidas(sala) -> str:
    saidas_validas = _saidas_validas(sala)
    if not saidas_validas:
        return "\n━━━━━━━━━━━━━━━━\n<b>Nenhuma saída óbvia.</b>\n❓ O que você faz?"
    lista = ", ".join(saidas_validas)
    return f"\n━━━━━━━━━━━━━━━━\n🗺️ <b>Saídas:</b> {lista}\n❓ O que você faz?"

def teclado_saidas(sala):
    saidas_validas = _saidas_validas(sala)
    if not saidas_validas:
        return ReplyKeyboardRemove()
    botoes = [KeyboardButton(text=s) for s in saidas_validas]
    linhas = [botoes[i:i+2] for i in range(0, len(botoes), 2)]
    return ReplyKeyboardMarkup(keyboard=linhas, resize_keyboard=True)

def resumo_status(jogador) -> str:
    status_str = ""
    if hasattr(jogador, 'status_efeitos') and jogador.status_efeitos:
        efeitos = ", ".join(jogador.status_efeitos)
        status_str = f" | ⚠️ <b>Status:</b> {efeitos}"

    return (
        f"\n━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>{jogador.nome}</b> | ❤️ {jogador.hp_atual}/{jogador.hp_maximo} | 🛡️ <b>CA: {jogador.modificador_defesa}</b>{status_str}"
    )

# Opções dos menus de criação de personagem (listas de listas = linhas de botões).
MENU_CLASSES = [
    ["Bárbaro", "Bardo", "Bruxo", "Artífice"],
    ["Clérigo", "Druida", "Feiticeiro"],
    ["Guerreiro", "Ladino", "Mago"],
    ["Monge", "Paladino", "Patrulheiro"],
]

MENU_RACAS = [
    ["Humano", "Elfo", "Anão"],
    ["Halfling", "Draconato", "Meio-Orc"],
    ["Meio-Elfo", "Tiefling", "Gnomo"],
]

MENU_BACKGROUNDS = [
    ["Acólito", "Criminoso"],
    ["Herói do Povo", "Nobre"],
    ["Sábio", "Soldado"],
    ["Forasteiro", "Artesão de Guilda"],
]


def _menu_teclado(opcoes: list):
    """Gera um ``ReplyKeyboardMarkup`` a partir de uma lista de listas de opções.

    Compartilhado entre ``menu_classes``, ``menu_racas`` e
    ``menu_backgrounds`` para evitar duplicação da construção do teclado.
    """
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=c) for c in linha] for linha in opcoes],
        resize_keyboard=True, one_time_keyboard=True
    )

def menu_classes():
    return _menu_teclado(MENU_CLASSES)

def menu_racas():
    return _menu_teclado(MENU_RACAS)

def menu_backgrounds():
    return _menu_teclado(MENU_BACKGROUNDS)

# ── NOVO: Utilitários da Bolsa da Party e Quadro de Missões ────────────────────
def formatar_bolsa_party(bolsa: dict) -> str:
    """Formata visualmente os itens e ouro contidos na bolsa do grupo."""
    if not bolsa or (not bolsa.get("itens") and bolsa.get("ouro", 0) == 0):
        return "A bolsa do grupo está vazia."
        
    linhas = []
    ouro = bolsa.get("ouro", 0)
    if ouro > 0:
        linhas.append(f"💰 <b>Ouro da Party:</b> {ouro} PO")
        
    itens = bolsa.get("itens", [])
    if itens:
        linhas.append("🎒 <b>Itens Coletados:</b>")
        contagem = {}
        for item in itens:
            contagem[item] = contagem.get(item, 0) + 1
        for item, qtd in contagem.items():
            if qtd > 1:
                linhas.append(f"  └ {qtd}x {item}")
            else:
                linhas.append(f"  └ {item}")
                
    return "\n".join(linhas)

def adicionar_a_bolsa_party(bolsa: dict, novos_itens: list) -> list:
    """
    Adiciona loot diretamente ao dicionário da bolsa da party.
    Retorna a lista de itens formatados que foram adicionados.
    """
    if "ouro" not in bolsa:
        bolsa["ouro"] = 0
    if "itens" not in bolsa:
        bolsa["itens"] = []
    
    itens_adicionados_msg = []
    
    for item in novos_itens:
        item_limpo = str(item).replace("•", "").replace("-", "").strip()
        
        match_ouro = re.search(r'(\d+)\s*(PO|po|gp|peças?\s*(?:de\s*ouro)?|ouro)', item_limpo, re.IGNORECASE)
        if match_ouro:
            quantidade = int(match_ouro.group(1))
            bolsa["ouro"] += quantidade
            itens_adicionados_msg.append(f"{quantidade} PO (Bolsa do Grupo)")
            continue
            
        if item_limpo:
            bolsa["itens"].append(item_limpo)
            itens_adicionados_msg.append(f"{item_limpo} (Bolsa do Grupo)")
            
    return itens_adicionados_msg

def menu_hub_aventuras(aventuras: list) -> InlineKeyboardMarkup:
    """Gera um teclado inline dinâmico com as missões/aventuras disponíveis no banco."""
    botoes = []
    for adv in aventuras:
        botoes.append([InlineKeyboardButton(text=f"📜 {adv.nome}", callback_data=f"hub_iniciar_{adv.id}")])
    botoes.append([InlineKeyboardButton(text="❌ Fechar", callback_data="hub_fechar")])
    
    return InlineKeyboardMarkup(inline_keyboard=botoes)

# =============================================================================
# CONSTANTES D&D 5E — FONTE CANÔNICA: dnd_5e_rules.py
# =============================================================================
# As constantes abaixo (CONDICOES_DND_5E, TIPOS_DANO, ACOES_COMBATE,
# COBERTURA_BONUS, TERRENOS, PERICIAS_DND_5E, PERICIAS_POR_ATRIBUTO)
# foram movidas para dnd_5e_rules.py para evitar duplicação e resolver o
# import circular. São importadas/reexportadas no topo deste módulo.
