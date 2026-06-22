"""
game_helpers.py — Constantes, parsers e regras de jogo compartilhadas.

Centraliza:
- Strings mágicas de status/condição (evita typos espalhados)
- Parser único de notação de dados ("1d8+2", "2d6-1")
- Lógica de Level Up (HP, slots, hit dice, proficiência, dano do Monge)
- Lógica de "Morte & Resgate" (HP=full, gold-=10, volta pra Carvalhal)
- Mapa de palavras-chave por classe (Fúria, Smite, Surto, etc.)
- Helpers para manipular `status_efeitos` (lista mutável por trás do JSON)

Antes essas regras estavam duplicadas entre combat_logic.py, action_resolver.py,
main.py e handlers/menus.py. Centralizar aqui reduz risco de divergência.
"""
from __future__ import annotations

import html as _html
import math
import random
import re
from typing import Tuple, List, Optional


# =============================================================================
# CONSTANTES DE STATUS / CONDIÇÃO
# =============================================================================
class Status:
    """Strings canônicas usadas em `jogador.status_efeitos`."""
    ATORDOADO = "Atordoado"
    PARALISADO = "Paralisado"
    INCONSCIENTE = "Inconsciente"
    CAIDO = "Caído"               # com acento — forma canônica
    CAIDO_ALT = "Caido"           # sem acento — forma tolerada (legado)
    ENVENENADO = "Envenenado"
    AGARRADO = "Agarrado"
    FURIA = "Fúria"
    SURTO = "Surto"
    SMITE = "Smite"
    FORMA_SELVAGEM = "Forma Selvagem"
    ESQUIVANDO = "Esquivando"
    COBERTURA = "Cobertura"
    AJUDADO = "Ajudado"
    DEATH_SAVE_SUCESSO = "DeathSave_Sucesso"
    DEATH_SAVE_FALHA = "DeathSave_Falha"

    # Conjunto de condições que bloqueiam a ação do turno
    BLOQUEIO_TURNO = {ATORDOADO, PARALISADO, INCONSCIENTE}

    # Variantes ortográficas aceitas como equivalentes
    VARIANTES = {
        CAIDO: {CAIDO, CAIDO_ALT},
    }


# =============================================================================
# CONSTANTES DE CENA
# =============================================================================
class Scene:
    CARVALHAL = "carvalhal"  # Hub / vila — descanso longo permitido
    TAVERNA = "taverna"      # Lobby central — mesma lógica de CARVALHAL


# =============================================================================
# PALAVRAS-CHAVE DE CLASSE (EFEITOS TÁTICOS)
# =============================================================================
# Cada entrada: keyword (lowercase) → efeitos a aplicar.
# Substitui os dois dicionários duplicados em combat_logic.py e action_resolver.py
# (que tinham pequenas divergências entre si).
KEYWORDS_POR_CLASSE = {
    "bárbaro": {
        "fúria": {},
    },
    "artífice": {
        "explosão arcana": {"bonus_dano": 4},
        "infusão": {"bonus_ca": 2},
    },
    "guerreiro": {
        "estocar": {"bonus_ataque": 2},
        "defesa total": {"bonus_ca": 4},
        "surto": {"bonus_ataque": 5},  # BUG #10 FIX: Surto de Ação — keyword ativável
    },
    "paladino": {
        "aura": {"bonus_ca": 3},
        "abjurar": {"bonus_ca": 5},
    },
    "monge": {
        "flurry": {"ataque_extra": True},
        "torrente": {"ataque_extra": True},
        "ki": {"bonus_ataque": 2},
    },
    "patrulheiro": {
        "marca": {"bonus_dano": 6},
        "marca do caçador": {"bonus_dano": 6},
    },
    "bardo": {
        "zombaria": {"desvantagem_inimigo": True},
    },
}


# =============================================================================
# ATAQUE DE OPORTUNIDADE (FUGA)
# =============================================================================
DANO_ATAQUE_OPORTUNIDADE = "1d6+2"   # era hardcoded em action_resolver.py


# =============================================================================
# PARSER DE NOTAÇÃO DE DADOS
# =============================================================================
_DICE_RE = re.compile(r"^\s*(\d+)?\s*d\s*(\d+)\s*([+-]\s*\d+)?\s*$", re.IGNORECASE)


def parse_dice_string(s: str, default_qtd: int = 1, default_faces: int = 6) -> Tuple[int, int, int]:
    """
    Parse '1d8+2', '2d6-1', '1d20' → (qtd, faces, modificador).

    Aceita também formas parciais ('d20' → 1d20; '8' → 1d8 com mod 0).
    Retorna (default_qtd, default_faces, 0) em qualquer entrada inválida.
    """
    if not s or not isinstance(s, str):
        return default_qtd, default_faces, 0
    m = _DICE_RE.match(s)
    if not m:
        return default_qtd, default_faces, 0
    qtd = int(m.group(1)) if m.group(1) else 1
    faces = int(m.group(2))
    mod = int(m.group(3).replace(" ", "")) if m.group(3) else 0
    return qtd, faces, mod


def rolar_dados(qtd: int, faces: int, mod: int = 0) -> Tuple[int, List[int]]:
    """
    Rola `qtd` dados de `faces` faces e soma `mod`.
    Retorna (total, lista_de_rolagens). Útil para narrar os dados.
    """
    rolagens = [random.randint(1, faces) for _ in range(max(1, qtd))]
    return sum(rolagens) + mod, rolagens


def rolar_dano(dano_str: str, mod: int = 0) -> Tuple[int, List[int]]:
    """Atalho: parse + rola + soma mod. Retorna (dano_total, rolagens)."""
    qtd, faces, mod_extra = parse_dice_string(dano_str)
    return rolar_dados(qtd, faces, mod + mod_extra)


def rolar_d20_unico() -> int:
    """Atalho: 1d20 simples."""
    return random.randint(1, 20)


# =============================================================================
# LEVEL UP
# =============================================================================
def aplicar_level_up(jogador, *, forcar_ate: Optional[int] = None) -> int:
    """
    Sobe o nível do jogador enquanto o XP for suficiente. Centraliza a regra de
    progressão que aparecia em 3 lugares (main.py /party entrar, action_resolver.py
    vitória de combate, combat_logic.py style="temerario").

    Se `forcar_ate` for passado, sobe até esse nível (útil em level-up por festa).
    Retorna a quantidade de níveis subidos.
    """
    from ui_utils import XP_POR_NIVEL, HP_POR_CLASSE

    niveis_subidos = 0
    alvo = forcar_ate if forcar_ate is not None else jogador.nivel + 1
    while jogador.nivel < alvo or (forcar_ate is None and jogador.xp >= XP_POR_NIVEL.get(jogador.nivel + 1, float("inf"))):
        jogador.nivel += 1
        jogador.hp_maximo += HP_POR_CLASSE.get(jogador.classe, HP_POR_CLASSE.get(jogador.classe.title(), 8)) + jogador.mod_con
        jogador.hp_atual = jogador.hp_maximo

        jogador.slots_magia_max += 1
        jogador.slots_magia = jogador.slots_magia_max
        jogador.hit_dice_max = getattr(jogador, "hit_dice_max", 1) + 1
        jogador.hit_dice_atual = jogador.hit_dice_max

        nova_proficiencia = 2 + ((jogador.nivel - 1) // 4)
        if nova_proficiencia > jogador.proficiencia:
            jogador.proficiencia = nova_proficiencia
            jogador.modificador_ataque = jogador.mod_dano + jogador.proficiencia

        # Artes Marciais do Monge escalam por nível
        if jogador.classe.lower() == "monge" and "Desarmado" in getattr(jogador, "arma_equipada", ""):
            if jogador.nivel >= 17: jogador.dano_dado = "1d10"
            elif jogador.nivel >= 11: jogador.dano_dado = "1d8"
            elif jogador.nivel >= 5: jogador.dano_dado = "1d6"
            else: jogador.dano_dado = "1d4"

        niveis_subidos += 1
        if forcar_ate is None and niveis_subidos > 20:
            # segurança contra loop infinito em caso de XP_POR_NIVEL malformado
            break
    return niveis_subidos


# =============================================================================
# MORTE & RESGATE (PATRULHA DE CARVALHAL)
# =============================================================================
RESGATE_MENSAGEM = (
    "\n💀 Caíste em combate! A Patrulha de Carvalhal resgatou-te, "
    "mas perdeste algum ouro..."
)
RESGATE_PERDA_OURO = 10


def aplicar_morte_resgate(jogador, campanha) -> str:
    """
    Aplica o protocolo padrão de "quase-morte" do bot:
    - HP volta ao máximo
    - Perde 10 PO
    - Cena volta para Taverna (jogador e campanha) — consistente com party wipe e SALA_INICIO
    - Sai do combate
    - Limpa status_efeitos

    Retorna a mensagem narrativa a ser exibida.
    """
    jogador.hp_atual = jogador.hp_maximo
    jogador.gold = max(0, jogador.gold - RESGATE_PERDA_OURO)
    campanha.cena_atual = Scene.TAVERNA
    jogador.cena_atual = Scene.TAVERNA
    campanha.em_combate = False
    set_status_efeitos(jogador, [])
    return RESGATE_MENSAGEM


# =============================================================================
# DESCANSO (curto / longo)
# =============================================================================
DESCANSO_LONGO_SALA = Scene.CARVALHAL  # só dá pra descansar longo na vila


def aplicar_descanso(jogador, cena_atual: str) -> Tuple[bool, str]:
    """
    Resolve descanso curto (fora da vila) ou longo (na vila).
    Lógica canônica, sincrona, sem DB — usada pelo pygame e pode
    substituir o trecho equivalente em action_resolver._resolver_descanso.

    Retorna (sucesso: bool, narrativa: str).
    - Sucesso=True → descanso rolou (HP restaurado e/ou status limpo)
    - Sucesso=False → não rolou (sem hit dice, exausto)
    """
    if cena_atual == DESCANSO_LONGO_SALA:
        # descanso longo
        jogador.hp_atual = jogador.hp_maximo
        jogador.slots_magia = getattr(jogador, "slots_magia_max", 0)
        jogador.hit_dice_atual = getattr(jogador, "hit_dice_max", 1)
        set_status_efeitos(jogador, [])
        return True, (
            "🛌 Descanso Longo na Vila. HP, Magia e Hit Dice restaurados! "
            "Efeitos de status removidos."
        )

    # descanso curto
    if getattr(jogador, "hit_dice_atual", 0) > 0:
        jogador.hit_dice_atual -= 1
        cura = max(1, (jogador.hp_maximo // 4) + jogador.mod_con)
        jogador.hp_atual = min(jogador.hp_maximo, jogador.hp_atual + cura)
        return True, (
            f"🏕️ Descanso Curto. Curaste {cura} HP. "
            f"Hit Dice: {jogador.hit_dice_atual}/{jogador.hit_dice_max}"
        )

    return False, "⚠️ Exausto! Sem Hit Dice. Regressa à Vila pra Descanso Longo."


# =============================================================================
# FUGA COM ATAQUE DE OPORTUNIDADE
# =============================================================================
DANO_FUGA_DADO = "1d6+2"  # ataque de oportunidade padrão


def resolver_fuga(jogador, nome_inimigo: str, inimigo_dict: dict = None) -> Tuple[bool, str]:
    """
    Resolve a fuga do jogador: ataque de oportunidade ao sair do alcance.
    D&D 5e: ao sair do alcance de um inimigo sem se afastar discretamente,
    ele ganha um ataque de oportunidade (d20+mod vs CA do jogador).

    Args:
        inimigo_dict: dict do bestiário (com chaves 'ataque', 'dano').
                      Se fornecido, usa stats reais em vez de hardcoded.
    """
    # Usar stats reais do bestiário se disponíveis
    if inimigo_dict:
        atk_str = inimigo_dict.get("ataque", "+4")
        dano_str = inimigo_dict.get("dano", DANO_FUGA_DADO)
        try:
            mod_ataque = int(atk_str.replace("+", "").replace(" ", ""))
        except (ValueError, AttributeError):
            mod_ataque = 4
    else:
        mod_ataque = 4
        dano_str = DANO_FUGA_DADO

    dano_fuga, _ = rolar_dano(dano_str)
    d20 = random.randint(1, 20)
    acertou = (d20 + mod_ataque >= jogador.modificador_defesa) or d20 == 20

    if acertou:
        jogador.hp_atual = max(0, jogador.hp_atual - dano_fuga)
        narrativa = (
            f"🩸 Fuga Arriscada! Ao virares as costas, {nome_inimigo} "
            f"acertou-te um Ataque de Oportunidade! "
            f"d20={d20}+{mod_ataque}={d20+mod_ataque} vs CA {jogador.modificador_defesa}, "
            f"sofreste {dano_fuga} de dano."
        )
        if jogador.hp_atual == 0:
            narrativa += "\n💀 Caíste em combate! A Patrulha de Carvalhal te resgata..."
        return True, narrativa
    return False, (
        f"💨 Fuga Ágil! Conseguiste desviar-te do ataque de {nome_inimigo} "
        f"enquanto recuavas. d20={d20}+{mod_ataque}={d20+mod_ataque} vs CA {jogador.modificador_defesa}"
    )


# =============================================================================
# HAZARDS DE SALA (armadilhas, gases, etc)
# =============================================================================
def aplicar_hazards(jogador, hazards: Optional[list]) -> str:
    """
    Itera sobre hazards da sala e rola testes de resistência (DEX/STR/CON).
    Hazards com tipo='dano_automatico' causam dano sem teste.

    Formato de cada hazard (dict):
        {"tipo": "dex_save"|"str_save"|"con_save"|"dano_automatico",
         "cd": 13,
         "dano": "1d4"|"2d6"|etc,
         "descricao": "Armadilha de espinhos no chão"}

    Retorna string com a narrativa acumulada (vazia se sem hazards).
    Aplica dano no jogador se falhar teste ou se dano_automatico.
    """
    if not hazards:
        return ""
    narrativa = ""
    for hazard in hazards:
        tipo = hazard.get("tipo", "")
        cd = hazard.get("cd", 13)
        dano_str = hazard.get("dano", "1d4")
        descricao = hazard.get("descricao", "Um perigo oculto")

        # Calcula dano rolando os dados
        dano_total, _ = rolar_dano(dano_str)

        # Escolhe modificador baseado no tipo de save
        if tipo == "dano_automatico":
            jogador.hp_atual = max(0, jogador.hp_atual - dano_total)
            narrativa += f"\n🔥 {descricao}! Sofreste {dano_total} de dano inevitável na área."
        else:
            mod = (
                jogador.mod_dex if tipo == "dex_save"
                else jogador.mod_str if tipo == "str_save"
                else jogador.mod_con
            )
            rolagem = random.randint(1, 20) + mod
            if rolagem >= cd:
                narrativa += f"\n✅ {descricao}! Desviaste com sucesso (Teste {rolagem} vs CD {cd})."
            else:
                jogador.hp_atual = max(0, jogador.hp_atual - dano_total)
                narrativa += f"\n❌ {descricao}! Foste atingido (Teste {rolagem} vs CD {cd}). Sofreste {dano_total} de dano!"
    return narrativa


# =============================================================================
# VULNERABILIDADE AO FOGO (centralizada)
# =============================================================================
# Alvos vulneráveis a fogo (ex: Árvore Gulthias) e palavras-gatilho de fogo.
# Centraliza a lógica que estava duplicada em action_resolver.py e combat_logic.py.
ALVOS_VULNERAVEIS_FOGO = ("árvore", "arvore", "gulthias")
GATILHOS_FOGO = ("fogo", "ardente", "chamas", "bola")


def calcular_vulnerabilidade_fogo(alvo_nome: str, texto_acao: str) -> bool:
    """
    Retorna True se o alvo é vulnerável a fogo E a ação envolve fogo.
    Centraliza a verificação de ALVOS_VULNERAVEIS_FOGO + GATILHOS_FOGO que
    estava duplicada entre action_resolver.py e combat_logic.py.
    """
    if not alvo_nome or not texto_acao:
        return False
    alvo_low = alvo_nome.lower()
    texto_low = texto_acao.lower()
    if not any(t in alvo_low for t in ALVOS_VULNERAVEIS_FOGO):
        return False
    return any(p in texto_low for p in GATILHOS_FOGO)


# =============================================================================
# STATUS EFFECTS — HELPERS
# =============================================================================
def get_status_efeitos(jogador) -> list:
    """
    Retorna uma CÓPIA mutável dos status. Nunca retorna None — callers
    podem fazer append/remove sem medo de AttributeError.
    """
    return list(getattr(jogador, "status_efeitos", []) or [])


def set_status_efeitos(jogador, lista: list) -> None:
    """Substitui status_efeitos preservando o MutableList do SQLAlchemy (clear+extend)."""
    atual = getattr(jogador, "status_efeitos", None)
    if atual is None:
        jogador.status_efeitos = list(lista)
    else:
        atual.clear()
        atual.extend(lista)


def set_inventario(jogador, lista: list) -> None:
    """Substitui inventario preservando o MutableList do SQLAlchemy (clear+extend)."""
    inv = getattr(jogador, "inventario", None)
    if inv is None:
        jogador.inventario = list(lista)
    else:
        inv.clear()
        inv.extend(lista)


def add_status(jogador, *novos: str) -> bool:
    """Adiciona 1+ status sem duplicar. Retorna True se algo mudou."""
    atual = get_status_efeitos(jogador)
    mudou = False
    for s in novos:
        if s not in atual:
            atual.append(s)
            mudou = True
    if mudou:
        set_status_efeitos(jogador, atual)
    return mudou


def _expandir_variantes(alvos) -> set:
    """Dado um conjunto de status, devolve o conjunto expandido com variantes ortográficas."""
    expandido = set(alvos)
    for variantes in Status.VARIANTES.values():
        if expandido & variantes:
            expandido.update(variantes)
    return expandido


def remove_status(jogador, *alvos: str) -> bool:
    """Remove 1+ status. Aceita variantes (ex: remove_status(j, Status.CAIDO) tira Caido e Caído)."""
    atual = get_status_efeitos(jogador)
    a_remover = _expandir_variantes(alvos)
    nova = [s for s in atual if s not in a_remover]
    if nova != atual:
        set_status_efeitos(jogador, nova)
        return True
    return False


def tem_status(jogador, *alvos: str) -> bool:
    """Checa se o jogador tem algum dos status. Aceita variantes ortográficas."""
    atual = set(get_status_efeitos(jogador))
    return bool(atual & _expandir_variantes(alvos))


def status_bloqueia_turno(jogador) -> Optional[str]:
    """Retorna o nome do status que bloqueia o turno, ou None."""
    for s in get_status_efeitos(jogador):
        if s in Status.BLOQUEIO_TURNO:
            return s
    return None


# =============================================================================
# KEYWORD MATCHER (extrai efeito da palavra-chave da classe)
# =============================================================================
def match_keyword_classe(texto_acao: str, classe: str) -> Tuple[Optional[str], dict]:
    """
    Procura a keyword de classe presente no texto da ação.
    Retorna (keyword_encontrada, dict_de_efeitos) — ambos None/{}
    se não houver match. Case-insensitive.

    Ordena por comprimento decrescente para evitar match por prefixo
    (ex: "marca" casaria antes de "marca do caçador" se checasse em ordem
    de inserção do dict). Era bug latente do código original.
    """
    kws = KEYWORDS_POR_CLASSE.get((classe or "").lower(), {})
    texto_low = (texto_acao or "").lower()
    for kw in sorted(kws.keys(), key=len, reverse=True):
        if kw in texto_low:
            return kw, kws[kw]
    return None, {}


# =============================================================================
# DIFFICULTY SCALING — Escala de dificuldade por tamanho de party
# =============================================================================
SCALING_TABLE = {
    1: 0.40,   # 40% do HP/quantidade original (fácil)
    2: 0.60,   # 60%
    3: 0.80,   # 80%
    4: 1.00,   # 100% (baseline)
    5: 1.20,   # 120% (desafiador)
}

def get_difficulty_factor(num_players: int) -> float:
    """Retorna o fator de dificuldade baseado no tamanho da party."""
    if num_players <= 0:
        num_players = 1
    if num_players in SCALING_TABLE:
        return SCALING_TABLE[num_players]
    # Para parties > 5 (futuro), interpola linearmente
    return 1.20 + (num_players - 5) * 0.15


# =============================================================================
# LOOT SPLIT — Distribuição de recompensas por party
# =============================================================================
def split_gold(total_gold: int, num_players: int) -> dict:
    """
    Distribui gold igualmente entre jogadores da party.
    Resto (remainder) vai para quem executou (executor = idx 0).
    Retorna {jogador_idx: gold_recebido}.
    """
    if num_players <= 0:
        num_players = 1
    if num_players == 1:
        return {0: total_gold}
    base = total_gold // num_players
    remainder = total_gold % num_players
    result = {}
    for i in range(num_players):
        result[i] = base + (1 if i < remainder else 0)
    return result


# =============================================================================
# SANITIZAÇÃO DE INPUT — Anti Stored XSS
# =============================================================================
# O frontend renderiza narrativas de combate e chat de NPCs via x-html
# (Alpine.js innerHTML). Se um campo controlado pelo usuário (ex: nome do
# personagem) contiver HTML/JS malicioso, ele será executado no browser de
# todos os membros da party — inclusive scripts que forjam CSRF usando o
# cookie csrf_token (httponly=False).
# Esta função DEVE ser aplicada a todo texto livre do usuário que possa
# aparecer em saída HTML.

_TAG_RE = re.compile(r'<[^>]+>')


def sanitize_user_text(text: str, max_len: int = 100) -> str:
    """Sanitiza texto livre do usuário para prevenir stored XSS.

    1. Remove qualquer tag HTML (<...>)
    2. Escapa caracteres especiais (&, <, >, ", ')
    3. Trunca ao comprimento máximo
    4. Strip de whitespace nas bordas

    Retorna string vazia se input for None/vazio.
    """
    if not text or not isinstance(text, str):
        return ""
    # Remove tags HTML
    clean = _TAG_RE.sub("", text)
    # Escapa caracteres especiais (previne injection de entidades/atributos)
    clean = _html.escape(clean, quote=True)
    # Trunca
    return clean.strip()[:max_len]
