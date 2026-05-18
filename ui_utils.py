"""
ui_utils.py — Constantes, utilitários de UI e helpers do inventário.
Importado pelo main.py para manter o arquivo de rotas limpo.
"""
import math
import random
import re
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton

import hashlib

def gerar_callback_safe(prefixo: str, nome_item: str) -> str:
    """
    Gera um callback_data compacto de até 64 caracteres limitados pelo Telegram,
    usando um hash MD5 dos últimos caracteres para evitar colisões.
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
    "Forasteiro": ["Atletismo", "Sobrevivência"]
}

# Todas as 18 perícias oficiais do D&D 5e mapeadas por atributo
PERICIAS_DND_5E = {
    # FORÇA
    "Atletismo": "STR",
    # DESTREZA
    "Acrobacia": "DEX",
    "Furtividade": "DEX",
    "Prestidigitação": "DEX",
    # INTELIGÊNCIA
    "Arcanismo": "INT",
    "História": "INT",
    "Investigação": "INT",
    "Natureza": "INT",
    "Religião": "INT",
    # SABEDORIA
    "Adestrar Animais": "WIS",
    "Intuição": "WIS",
    "Medicina": "WIS",
    "Percepção": "WIS",
    "Sobrevivência": "WIS",
    # CARISMA
    "Enganação": "CHA",
    "Intimidação": "CHA",
    "Performance": "CHA",
    "Persuasão": "CHA"
}

PERICIAS_POR_ATRIBUTO = {
    "STR": ["Atletismo"],
    "DEX": ["Acrobacia", "Furtividade", "Prestidigitação"],
    "INT": ["Arcanismo", "História", "Investigação", "Natureza", "Religião"],
    "WIS": ["Adestrar Animais", "Intuição", "Medicina", "Percepção", "Sobrevivência"],
    "CHA": ["Enganação", "Intimidação", "Performance", "Persuasão"]
}

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
    "Goblin Salteador":         "https://cdn.cardsrealm.com/images/cartas/7ed-seventh-edition/en/crop-med/goblin-raider-192.jpeg",
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

# ── Inventário e Saque Inteligente ──────────────────────────────────────────────
def obter_inventario_limpo(inv_bruto) -> list:
    if not inv_bruto:
        return []
    
    # FAST PATH: Se já for uma lista nativa (o padrão do SQLAlchemy limpo), apenas retorna os itens válidos
    if isinstance(inv_bruto, list):
        return [str(item).strip() for item in inv_bruto if str(item).strip()]
    
    # SLOW PATH (LEGADO): Se por acaso veio como string do banco, faz o parse do Frankenstein
    inv_str = str(inv_bruto)

    if '\\u' in inv_str or '\\n' in inv_str:
        try:
            inv_str = inv_str.encode('utf-8').decode('unicode_escape')
        except Exception:
            pass

    for char in ['[', ']', '"', "'", '•']:
        inv_str = inv_str.replace(char, '')

    inv_str = inv_str.replace('\n', ',')

    itens_limpos = []
    for item in inv_str.split(','):
        limpo = item.strip()
        if limpo:
            itens_limpos.append(limpo)
            
    return itens_limpos

def formatar_inventario_para_display(lista_itens: list) -> str:
    if not lista_itens:
        return "Inventário vazio."
        
    contagem = {}
    for item in lista_itens:
        contagem[item] = contagem.get(item, 0) + 1
        
    linhas = []
    for item, qtd in contagem.items():
        if qtd > 1:
            linhas.append(f"{qtd}x {item}")
        else:
            linhas.append(item)
            
    return "\n".join(linhas)

def adicionar_ao_inventario(jogador, novos_itens: list) -> list:
    """
    Adiciona itens ao inventário INDIVIDUAL do jogador.
    """
    inv = obter_inventario_limpo(jogador.inventario)
    itens_adicionados_msg = []
    
    for item in novos_itens:
        item_limpo = str(item).replace("•", "").replace("-", "").strip()
        
        match_ouro = re.search(r'(\d+)\s*(PO|po|peças de ouro|ouro)', item_limpo, re.IGNORECASE)
        if match_ouro:
            quantidade = int(match_ouro.group(1))
            jogador.gold += quantidade
            itens_adicionados_msg.append(f"{quantidade} PO (adicionado à bolsa)")
            continue 
            
        if item_limpo:
            inv.append(item_limpo)
            itens_adicionados_msg.append(item_limpo)
            
    # REATRIBUIÇÃO OBRIGATÓRIA para o SQLAlchemy rastrear a mutação do JSON
    jogador.inventario = inv
    return itens_adicionados_msg

async def processar_saque(message, jogador, narracao: str, db):
    from ai_engine import extrair_itens_da_narracao
    itens = await extrair_itens_da_narracao(narracao)
    if itens:
        itens_reais = adicionar_ao_inventario(jogador, itens)
        db.commit()
        lista = ", ".join(itens_reais)
        await message.answer(f"<b>Loot Encontrado!</b> Adicionado: {lista}", parse_mode="HTML")

# ── Loot Dinâmico e Armadilhas ─────────────────────────────────────────────────
def gerar_loot_inimigo_comum() -> list:
    roll = random.randint(1, 100)
    if roll <= 50:
        return []
    elif roll <= 80:
        ouro = random.randint(1, 6)
        return [f"{ouro} PO"]
    elif roll <= 95:
        armas = ["Adaga", "Espada Curta", "Arco Curto", "Machadinha", "Funda"]
        return [random.choice(armas)]
    else:
        return ["Poção de Cura"]

def gerar_loot_bau(nivel=1) -> list:
    roll = random.randint(1, 100)
    ouro = random.randint(10, 50) * nivel
    
    if roll <= 40:
        return [f"{ouro} PO"]
    elif roll <= 75:
        return [f"{ouro} PO", "Poção de Cura"]
    elif roll <= 95:
        equipamento = ["Espada Longa", "Machado de Batalha", "Rapieira", "Armadura de Couro", "Corda de Seda (15m)"]
        return [f"{ouro} PO", random.choice(equipamento)]
    else:
        return [f"{ouro} PO", "Poção de Cura Maior", "Kit de Aventureiro"]

# ── Teclados e menus ───────────────────────────────────────────────────────────
def texto_saidas(sala) -> str:
    if not sala or not sala.conexoes:
        return "\n━━━━━━━━━━━━━━━━\n<b>Nenhuma saída óbvia.</b>\n❓ O que você faz?"
    saidas_validas = [k.title() for k, v in sala.conexoes.items() if isinstance(v, str) and v.strip()]
    if not saidas_validas:
        return "\n━━━━━━━━━━━━━━━━\n<b>Nenhuma saída óbvia.</b>\n❓ O que você faz?"
    lista = ", ".join(saidas_validas)
    return f"\n━━━━━━━━━━━━━━━━\n🗺️ <b>Saídas:</b> {lista}\n❓ O que você faz?"

def teclado_saidas(sala):
    if not sala or not sala.conexoes:
        return ReplyKeyboardRemove()
    botoes = [KeyboardButton(text=k.title()) for k, v in sala.conexoes.items() if isinstance(v, str) and v.strip()]
    if not botoes:
        return ReplyKeyboardRemove()
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

def menu_classes():
    classes = [
        ["Bárbaro", "Bardo", "Bruxo", "Artífice"],
        ["Clérigo", "Druida", "Feiticeiro"],
        ["Guerreiro", "Ladino", "Mago"],
        ["Monge", "Paladino", "Patrulheiro"]
    ]
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=c) for c in linha] for linha in classes],
        resize_keyboard=True, one_time_keyboard=True
    )

def menu_racas():
    racas = [
        ["Humano", "Elfo", "Anão"],
        ["Halfling", "Draconato", "Meio-Orc"],
        ["Meio-Elfo", "Tiefling", "Gnomo"]
    ]
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=c) for c in linha] for linha in racas],
        resize_keyboard=True, one_time_keyboard=True
    )

def menu_backgrounds():
    bg = [
        ["Acólito", "Criminoso"],
        ["Herói do Povo", "Nobre"],
        ["Sábio", "Soldado"],
        ["Forasteiro"]
    ]
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=c) for c in linha] for linha in bg],
        resize_keyboard=True, one_time_keyboard=True
    )

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
    if "ouro" not in bolsa: bolsa["ouro"] = 0
    if "itens" not in bolsa: bolsa["itens"] = []
    
    itens_adicionados_msg = []
    
    for item in novos_itens:
        item_limpo = str(item).replace("•", "").replace("-", "").strip()
        
        match_ouro = re.search(r'(\d+)\s*(PO|po|peças de ouro|ouro)', item_limpo, re.IGNORECASE)
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
# CONDIÇÕES OFICIAIS D&D 5E
# =============================================================================
CONDICOES_DND_5E = {
    "Cego": {
        "descricao": "Não pode ver e falha automaticamente em testes de habilidade que requerem visão.",
        "efeitos": {"desvantagem_ataques": True, "vantagem_ataques_contra": True, "falha_testes_visao": True}
    },
    "Surdo": {"descricao": "Não pode ouvir e falha automaticamente em testes de habilidade que requerem audição.", "efeitos": {"falha_testes_audicao": True}},
    "Paralisado": {
        "descricao": "Incapacitado, não pode se mover ou falar, falha automaticamente em testes de Força e Destreza.",
        "efeitos": {"incapacitado": True, "movimento_zero": True, "falha_testes_forca_destreza": True, "vantagem_ataques_contra": True, "critico_automatico_range": True}
    },
    "Petrificado": {
        "descricao": "Transformado em substância inanimada, inconsciente, resistente a todos os danos.",
        "efeitos": {"incapacitado": True, "inconsciente": True, "resistencia_todos_danos": True, "peso_multiplicado_10": True}
    },
    "Invisível": {
        "descricao": "Não pode ser visto sem auxílio mágico ou sentidos especiais.",
        "efeitos": {"vantagem_ataques": True, "desvantagem_ataques_contra": True, "invisivel": True}
    },
    "Agarrado": {"descricao": "Velocidade reduzida a 0, não pode se beneficiar de bônus de velocidade.", "efeitos": {"velocidade_zero": True, "condicao_termina_se_movido": True}},
    "Restrito": {
        "descricao": "Velocidade 0, desvantagem em ataques, vantagem em ataques contra ele.",
        "efeitos": {"velocidade_zero": True, "desvantagem_ataques": True, "vantagem_ataques_contra": True, "desvantagem_testes_destreza": True}
    },
    "Inconsciente": {
        "descricao": "Incapacitado, cai no chão, falha automaticamente em testes de Força e Destreza.",
        "efeitos": {"incapacitado": True, "caido": True, "falha_testes_forca_destreza": True, "vantagem_ataques_contra": True, "critico_automatico_range": True}
    },
    "Morto": {
        "descricao": "O personagem faleceu. Apenas magia poderosa como Ressurreição ou Desejo pode trazê-lo de volta.",
        "efeitos": {"hp_zero_incuravel": True, "fim_jogo": True}
    },
    "Envenenado": {"descricao": "Desvantagem em testes de ataque e testes de habilidade.", "efeitos": {"desvantagem_ataques": True, "desvantagem_testes_habilidade": True}},
    "Atordoado": {
        "descricao": "Incapacitado, não pode agir, fala arrastada, falha em testes de Força e Destreza.",
        "efeitos": {"incapacitado": True, "falha_testes_forca_destreza": True, "vantagem_ataques_contra": True}
    },
    "Assustado": {
        "descricao": "Desvantagem em testes de habilidade e ataques enquanto fonte do medo estiver à vista.",
        "efeitos": {"desvantagem_ataques": True, "desvantagem_testes_habilidade": True, "nao_pode_aproximar": True}
    },
    "Caído": {
        "descricao": "No chão. Ataques corpo-a-corpo contra têm vantagem, ataques à distância contra têm desvantagem.",
        "efeitos": {"desvantagem_ataques_proprios": True, "levantar_gasta_metade_movimento": True}
    },
    "Esquivando": {
        "descricao": "Posição defensiva. Inimigos têm desvantagem para atacar até o próximo turno.",
        "efeitos": {"desvantagem_ataques_contra": True, "dura_ate_proximo_turno": True}
    },
    "Cobertura": {"descricao": "Protegido por obstáculo. +2 na CA contra ataques.", "efeitos": {"bonus_ca": 2, "cobertura_parcial": True}},
    "Ajudado": {
        "descricao": "Preparou ajuda para aliado. Próximo ataque do grupo tem vantagem.",
        "efeitos": {"concede_vantagem_aliado": True, "consumido_no_proximo_ataque": True}
    },
    "Fúria": {
        "descricao": "Bárbaro em fúria. +dano, resistência a dano físico, vantagem em testes de Força.",
        "efeitos": {"bonus_dano": 2, "resistencia_contundente": True, "resistencia_perfurante": True, "resistencia_cortante": True, "vantagem_testes_forca": True}
    }
}

# =============================================================================
# TIPOS DE DANO D&D 5E
# =============================================================================
TIPOS_DANO = {
    "ácido": {"icone": "🧪", "descricao": "Dano corrosivo"},
    "fogo": {"icone": "🔥", "descricao": "Dano por chamas"},
    "frio": {"icone": "❄️", "descricao": "Dano congelante"},
    "elétrico": {"icone": "⚡", "descricao": "Dano por lightning"},
    "trovejante": {"icone": "🔊", "descricao": "Dano sônico/trovão"},
    "perfurante": {"icone": "🗡️", "descricao": "Dano físico perfurante"},
    "cortante": {"icone": "⚔️", "descricao": "Dano físico cortante"},
    "contundente": {"icone": "👊", "descricao": "Dano físico de impacto"},
    "venenoso": {"icone": "☠️", "descricao": "Dano por toxinas"},
    "radiante": {"icone": "✨", "descricao": "Dano divino/luz"},
    "necrótico": {"icone": "💀", "descricao": "Dano de energia negativa"},
    "força": {"icone": "💫", "descricao": "Dano de força pura mágica"},
    "psíquico": {"icone": "🧠", "descricao": "Dano mental"}
}

# =============================================================================
# AÇÕES DE COMBATE D&D 5E
# =============================================================================
ACOES_COMBATE = {
    "Ataque": {"descricao": "Realiza um ataque corpo-a-corpo ou à distância", "acao_principal": True},
    "Destruir/Arrombar": {"descricao": "Teste de Força para quebrar objetos ou portas", "acao_principal": True, "teste": "STR"},
    "Usar Objeto": {"descricao": "Interage com um objeto do cenário", "acao_principal": False, "limitacao": "1 por turno"},
    "Preparar Ação": {"descricao": "Prepara uma ação para ser executada como reação quando um gatilho ocorrer", "acao_principal": True, "requer_reacao": True},
    "Ajuda": {"descricao": "Concede vantagem ao próximo ataque de um aliado contra criatura próxima", "acao_principal": True, "alcance": "5 pés"},
    "Investida": {"descricao": "Move-se até metade do deslocamento e empurra alvo", "acao_principal": True, "teste": "STR (Atletismo) vs STR ou DES do alvo"},
    "Derrubar": {"descricao": "Tenta derrubar alvo no chão", "acao_principal": True, "substitui_ataque": True, "teste": "STR (Atletismo) vs STR ou DES do alvo"},
    "Desengajar": {"descricao": "Movimento não provoca ataques de oportunidade", "acao_principal": True},
    "Correr": {"descricao": "Dobra o deslocamento neste turno", "acao_principal": True},
    "Esquivar": {"descricao": "Inimigos têm desvantagem contra você até seu próximo turno", "acao_principal": True, "dura_ate": "proximo_turno"},
    "Ataque de Oportunidade": {"descricao": "Ataque gratuito quando inimigo sai do seu alcance", "reação": True, "gasta_reacao": True}
}

# =============================================================================
# COBERTURA (Cover)
# =============================================================================
COBERTURA_BONUS = {
    "parcial": {"ca_bonus": 2, "des_bonus": 2, "descricao": "Protegido por pelo menos metade do corpo"},
    "tres_quartos": {"ca_bonus": 5, "des_bonus": 5, "descricao": "Protegido por três quartos do corpo"},
    "total": {"invisivel": True, "descricao": "Completamente escondido"}
}

# =============================================================================
# MOVIMENTO E TERRENO
# =============================================================================
TERRENOS = {
    "normal": {"custo_movimento": 1, "descricao": "Terreno comum"},
    "difícil": {"custo_movimento": 2, "descricao": "Cada pé custa 1 pé extra"},
    "íngreme": {"custo_movimento": 2, "descricao": "Subida íngreme"},
    "nadando": {"custo_movimento": 2, "descricao": "Natação"},
    "escalada": {"custo_movimento": 2, "descricao": "Escalada sem ferramentas"}
}
