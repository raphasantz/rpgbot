"""
ActionResolver — Cérebro Determinístico do MezzaRPG (D&D 5e).
Versão síncrona para FastAPI + modelos_web.

Responsabilidades:
1. Receber JSON da IA + texto livre do jogador
2. Aplicar regras de status (D&D 5e) — atordoado, paralisado, inconsciente, agarrado, etc.
3. Roteiar ação para submétodo apropriado (combate, magia, manobra, navegação, interação, descanso)
4. Persistir mutações no JogadorWeb / CampanhaWeb / entidades do banco
"""

import logging
import random
import math
import re
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger("mezzarpg.action_resolver")

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from modelos_web import (
    JogadorWeb, CampanhaWeb, Cena, Encontro, Inimigo,
    ObjetoDestrutivel, Npc, Interativo, Missao,
    SessionLocal, get_db,
)
from combat_logic import processar_ataque_fisico, processar_ataque_objeto
from ui_utils import (
    MAGIAS_POR_CLASSE, XP_POR_NIVEL, HP_POR_CLASSE,
    gerar_loot_inimigo_comum, adicionar_ao_inventario,
    obter_inventario_limpo, BACKGROUND_SKILLS, gerar_loot_bau,
    PERICIAS_DND_5E, LOJA_CARVALHAL, ARMAS_DB,
)
from mapa_engine import extrair_direcao_sync
from dnd_5e_rules import CONDICOES_DND_5E
from game_helpers import (
    set_status_efeitos, set_inventario, parse_dice_string, rolar_dados, aplicar_level_up,
    KEYWORDS_POR_CLASSE, calcular_vulnerabilidade_fogo, aplicar_hazards as aplicar_hazards_gh,
    Status, get_difficulty_factor, split_gold,
)

# =====================================================================
# CONSTANTES DE DOMÍNIO
# =====================================================================

# Status importado de game_helpers (fonte canônica — NÃO definir aqui)

STATUS_RESTRITIVOS = {Status.ATORDOADO, Status.PARALISADO, Status.INCONSCIENTE}

PALAVRAS_ESQUIVA = ("esquivar", "defender", "dodge", "defesa total")
PALAVRAS_COBERTURA = ("cobertura", "esconder", "proteger")
PALAVRAS_AJUDA = ("ajudar", "ajudo", "suportar")
PALAVRAS_FUGA = ("fugir", "fujo", "correr", "escapar", "recuar")
PALAVRAS_TESTE = ("teste", "rolar", "perceção", "percepção", "história", "arcanismo", "escutar")
PALAVRAS_VASCULHAR = ("vasculhar", "procurar", "sala", "chão")
PALAVRAS_BEBER_POCAO = ("poção", "antídoto", "pocao", "antidoto")
INIMIGOS_VENENOSOS = ("rato", "aranha", "cobra")
SALA_INICIO = "taverna"
CHANCE_ENVENENAR = 20

SINONIMOS_DIRECAO: Dict[str, List[str]] = {
    "baixo": ["baixo", "descer", "descida", "poço", "buraco"],
    "cima": ["cima", "subir", "subida", "escada"],
    "dentro": ["dentro", "entrar", "porta"],
    "fora": ["fora", "sair", "rua"],
}


def _parse_mod_ataque(s) -> int:
    """Extrai o modificador de ataque de uma string como '+3' ou '2d6+1'.
    Usa regex para encontrar todos os [+-]\\d+ e pega o último match.
    Fallback 0 se nada for encontrado."""
    try:
        s_str = str(s)
        matches = re.findall(r'[+-]\d+', s_str)
        if matches:
            return int(matches[-1])
    except Exception:
        pass
    return 0


# =====================================================================
# DATACLASSES DE RETORNO
# =====================================================================

@dataclass
class ActionResult:
    sucesso: bool
    tipo_acao: str  # "combate", "magia", "manobra", "navegacao", "interacao", "descanso", "outro", "status"
    narrativa_mecanica: str
    dados_extras: Dict[str, Any] = field(default_factory=dict)


# =====================================================================
# RESOLVER PRINCIPAL
# =====================================================================

class ActionResolver:
    """
    O Cérebro Determinístico do MezzaRPG.
    Roteia o JSON da IA, aplica regras de status e invoca o motor de dados.
    """

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # PIPELINE PRINCIPAL
    # ------------------------------------------------------------------

    def resolver_acao(
        self,
        jogador: JogadorWeb,
        campanha: CampanhaWeb,
        cena_atual: Optional[Cena],
        json_ia: Dict[str, Any],
        texto_jogador: str,
    ) -> ActionResult:
        """Pipeline principal de resolução de turnos."""
        status_jogador = list(getattr(jogador, "status_efeitos", []) or [])

        # 1) Filtro de status restritivos globais
        status_bloqueio = self._status_restritivo(status_jogador)
        if status_bloqueio:
            return ActionResult(
                False, "status",
                f"💫 Estás {status_bloqueio}! Perdes o teu turno e não consegues agir.",
                {},
            )

        intencao = json_ia.get("intencao", "OUTRO").upper()

        # 2) Interceptar ações tácticas (esquiva, cobertura, ajuda) ANTES do roteamento
        # A IA pode mapear "esquivar" para MANOBRA, mas essas são ações livres
        texto_low = texto_jogador.lower()
        if any(p in texto_low for p in PALAVRAS_ESQUIVA):
            if self._adicionar_status_unico(jogador, Status.ESQUIVANDO):
                return ActionResult(True, "status",
                    "🛡️ <b>Posição Defensiva!</b> Inimigos terão desvantagem para te acertar até teu próximo turno.", {})
            return ActionResult(False, "status", "⚠️ Já estás em posição defensiva.", {})
        if any(p in texto_low for p in PALAVRAS_COBERTURA):
            if self._adicionar_status_unico(jogador, Status.COBERTURA):
                return ActionResult(True, "status",
                    "🧱 <b>Cobertura!</b> Protegeste-te. Ganhaste +2 de CA contra os próximos ataques.", {})
            return ActionResult(False, "status", "⚠️ Já estás protegido em cobertura.", {})
        if any(p in texto_low for p in PALAVRAS_AJUDA):
            if self._adicionar_status_unico(jogador, Status.AJUDADO):
                return ActionResult(True, "status",
                    "🤝 Posicionaste-te para dar suporte! O próximo ataque do grupo terá Vantagem.", {})
            return ActionResult(False, "status", "⚠️ Já estás a dar suporte. Aguarda o próximo turno.", {})

        # 3) Roteamento por intenção
        roteadores = {
            "COMBATE": lambda: self._resolver_combate(
                jogador, campanha, cena_atual,
                json_ia.get("alvo"), json_ia.get("estilo"), texto_jogador,
            ),
            "MAGIA": lambda: self._resolver_magia(
                jogador, campanha, cena_atual,
                json_ia.get("magia_usada"), json_ia.get("alvo"), texto_jogador,
            ),
            "MANOBRA": lambda: self._resolver_manobra(
                jogador, campanha, cena_atual,
                json_ia.get("manobra"), json_ia.get("alvo"), texto_jogador,
            ),
            "NAVEGAR": lambda: self._resolver_navegacao(
                jogador, campanha, cena_atual,
                json_ia.get("direcao"), texto_jogador,
            ),
            "INTERACAO": lambda: self._resolver_interacao(
                jogador, campanha, cena_atual,
                json_ia.get("alvo"), json_ia.get("item"), texto_jogador,
            ),
            "DESCANSAR": lambda: self._resolver_descanso(jogador, campanha, cena_atual, texto_jogador),
        }
        roteador = roteadores.get(intencao)
        if roteador:
            return roteador()

        # 4) Intercepção de testes e ações não-rooteadas (texto livre)
        return self._resolver_acao_livre(jogador, campanha, cena_atual, intencao, texto_jogador)

    # ------------------------------------------------------------------
    # HELPERS DE DOMÍNIO
    # ------------------------------------------------------------------

    @staticmethod
    def _status_restritivo(status: List[str]) -> Optional[str]:
        if Status.ATORDOADO in status: return "atordoado"
        if Status.PARALISADO in status: return "paralisado"
        if Status.INCONSCIENTE in status: return "inconsciente"
        return None

    @staticmethod
    def _adicionar_status_unico(jogador: JogadorWeb, status: str) -> bool:
        efeitos = list(getattr(jogador, "status_efeitos", []) or [])
        if status in efeitos: return False
        efeitos.append(status)
        set_status_efeitos(jogador, efeitos)
        return True

    @staticmethod
    def _remover_status(jogador: JogadorWeb, *status: str) -> None:
        efeitos = list(getattr(jogador, "status_efeitos", []) or [])
        set_status_efeitos(jogador, [e for e in efeitos if e not in status])

    @staticmethod
    def _nocauteado_para_vila(jogador: JogadorWeb, campanha: CampanhaWeb) -> str:
        jogador.hp_atual = jogador.hp_maximo
        jogador.gold = max(0, jogador.gold - 10)
        campanha.cena_atual = SALA_INICIO
        jogador.cena_atual = SALA_INICIO
        campanha.em_combate = False
        set_status_efeitos(jogador, [])
        return "\n💀 Caíste! A Patrulha de Carvalhal resgatou-te, mas perdeste algum ouro..."

    def _resolver_acao_livre(
        self,
        jogador: JogadorWeb,
        campanha: CampanhaWeb,
        cena: Optional[Cena],
        intencao: str,
        texto: str,
    ) -> ActionResult:
        """Detecta ações tácicas (esquiva, cobertura, ajuda) e testes pelo texto livre."""
        texto_low = texto.lower()

        # Ações tácticas
        if any(p in texto_low for p in PALAVRAS_ESQUIVA):
            if self._adicionar_status_unico(jogador, Status.ESQUIVANDO):
                return ActionResult(True, "status",
                    "🛡️ <b>Posição Defensiva!</b> Inimigos terão desvantagem para te acertar até teu próximo turno.", {})
            return ActionResult(False, "status", "⚠️ Já estás em posição defensiva.", {})

        if intencao == "COBERTURA" or any(p in texto_low for p in PALAVRAS_COBERTURA):
            if self._adicionar_status_unico(jogador, Status.COBERTURA):
                return ActionResult(True, "status",
                    "🧱 <b>Cobertura!</b> Protegeste-te. Ganhaste +2 de CA contra os próximos ataques.", {})
            return ActionResult(False, "status", "⚠️ Já estás protegido em cobertura.", {})

        if intencao == "AJUDAR" or any(p in texto_low for p in PALAVRAS_AJUDA):
            if self._adicionar_status_unico(jogador, Status.AJUDADO):
                return ActionResult(True, "status",
                    "🤝 Posicionaste-te para dar suporte! O próximo ataque do grupo terá Vantagem.", {})
            return ActionResult(False, "status", "⚠️ Já estás a dar suporte. Aguarda o próximo turno.", {})

        # Testes manuais
        if intencao in {"INTERACAO", "OUTRO", "TESTE"} and any(p in texto_low for p in PALAVRAS_TESTE):
            return self._resolver_teste(jogador, cena, texto)

        # ── Ações específicas da Taverna ──
        if campanha.cena_atual == SALA_INICIO:
            resultado_taverna = self._resolver_taverna(jogador, campanha, cena, texto)
            if resultado_taverna: return resultado_taverna

        # Fallback narrativo
        return ActionResult(True, "outro", "Ação resolvida pelo ambiente ou narrativa.", {"intencao": intencao})

    # ------------------------------------------------------------------
    # COMBATE
    # ------------------------------------------------------------------

    def _resolver_combate(
        self,
        jogador: JogadorWeb,
        campanha: CampanhaWeb,
        cena: Optional[Cena],
        alvo_nome: Optional[str],
        estilo: Optional[str],
        texto: str,
        is_magia: bool = False,
    ) -> ActionResult:
        estado = dict(campanha.estado_salas or {})
        encontro, inimigo = self._selecionar_inimigo(cena, estado)
        if encontro is None:
            return self._resolver_ataque_objeto(jogador, cena, alvo_nome, texto)
        if inimigo is None:
            return ActionResult(False, "combate", f"O monstro {encontro.nome_inimigo} não tem ficha no bestiário!", {})

        campanha.em_combate = True
        # BUG #7 FIX: Limpar flag de poção usada no início de cada turno
        estado.pop("pocao_usada_turno", None)

        chave_hp = f"hp_{encontro.id}"
        hp_max_inimigo = max(1, inimigo.hp_max or 10)
        chave_hp_max = f"hp_max_grupo_{encontro.id}"
        # Difficulty scaling: escala HP/quantidade baseado no tamanho da party
        if chave_hp not in estado:
            num_players = self.db.query(func.count()).select_from(JogadorWeb).filter(
                JogadorWeb.party_id == campanha.party_id,
                JogadorWeb.hp_atual > 0,
            ).scalar() or 1
            factor = get_difficulty_factor(num_players)
            qty_scaled = max(1, math.ceil(encontro.quantidade * factor))
            hp_grupo = math.ceil(hp_max_inimigo * qty_scaled)
            estado[chave_hp_max] = hp_grupo
        else:
            hp_grupo = estado.get(chave_hp, hp_max_inimigo * encontro.quantidade)
        hp_max_grupo = estado.get(chave_hp_max, hp_grupo)
        ca_alvo = inimigo.ca
        is_durnn_furia = self._aplicar_furia_boss(inimigo, hp_grupo, hp_max_grupo, estado)

        ca_alvo_atual = max(10, ca_alvo - 2) if is_durnn_furia else ca_alvo
        estado["ca_alvo"] = ca_alvo_atual
        campanha.estado_salas = estado

        efeitos_atuais = list(getattr(jogador, "status_efeitos", []) or [])
        vantagem, desvantagem, str_vantagem = self._calcular_modificadores_combate(jogador, estilo, efeitos_atuais)

        # Backup dos modificadores (para reverter após o turno)
        mod_ataque_orig = getattr(jogador, "modificador_ataque", 0)
        mod_defesa_orig = getattr(jogador, "modificador_defesa", 10)
        dano_extra = 0
        keyword_feature_msg = ""
        # BUG #3 FIX: Aplicar bônus de CA da Cobertura (+2) — D&D 5e
        # Deve vir APÓS o backup (para ser restaurado no final) e ANTES das keywords
        if Status.COBERTURA in efeitos_atuais:
            jogador.modificador_defesa = (jogador.modificador_defesa or 10) + 2

        # Processar keywords de classe (antes do ataque)
        dano_extra, keyword_feature_msg = self._aplicar_keyword_classe(jogador, campanha, texto, efeitos_atuais)

        # Iniciativa
        if is_magia:
            # BUG #2 FIX: Magia NÃO rola iniciativa — é a ação do turno, jogador vai primeiro
            inimigo_primeiro = False
            narrativa = ""
        else:
            ini_jogador = random.randint(1, 20) + jogador.mod_dex
            ini_inimigo = random.randint(1, 20) + getattr(inimigo, "mod_destreza", 0)
            narrativa = f"⚡ INICIATIVA: {jogador.nome} {ini_jogador} vs {inimigo.nome} {ini_inimigo}\n\n"
            inimigo_primeiro = ini_inimigo >= ini_jogador

        # Revide do inimigo (se ganhar iniciativa — nunca acontece em magia)
        if inimigo_primeiro:
            texto_rev, efeitos_atuais = self._resolver_revide_inimigo(
                jogador, campanha, encontro, inimigo, hp_grupo, hp_max_inimigo, efeitos_atuais, is_durnn_furia,
            )
            narrativa += texto_rev
            if jogador.hp_atual <= 0:
                narrativa += self._nocauteado_para_vila(jogador, campanha)
                return ActionResult(True, "combate", narrativa.strip(), {"dano": 0, "acertou": False})

        # Turno do jogador (ataque com dados da magia)
        dano_causado, acertou, narrativa_ataque, contexto_critico = self._ataque_jogador(
            jogador=jogador, ca_alvo=ca_alvo_atual, estilo=estilo, alvo_nome=alvo_nome,
            texto=texto, dano_extra=dano_extra, keyword_feature_msg=keyword_feature_msg,
            efeitos_atuais=efeitos_atuais, hp_grupo=hp_grupo, hp_max_inimigo=hp_max_inimigo,
            chave_hp=chave_hp, estado=estado, campanha=campanha, encontro=encontro,
            inimigo=inimigo, is_durnn_furia=is_durnn_furia,
        )
        narrativa += narrativa_ataque
        hp_grupo = estado.get(chave_hp, hp_max_inimigo * encontro.quantidade)

        # Revide do inimigo (se o inimigo sobreviveu — SEMPRE em magia, pois inimigo_primeiro=False)
        if not inimigo_primeiro and campanha.em_combate and hp_grupo > 0 and jogador.hp_atual > 0:
            texto_rev, efeitos_atuais = self._resolver_revide_inimigo(
                jogador, campanha, encontro, inimigo, hp_grupo, hp_max_inimigo, efeitos_atuais, is_durnn_furia,
            )
            narrativa += "\n" + texto_rev

        # Restaurar modificadores (evita acúmulo permanente no DB)
        jogador.modificador_ataque = mod_ataque_orig
        jogador.modificador_defesa = mod_defesa_orig

        # Veneno no fim do turno
        if Status.ENVENENADO in efeitos_atuais:
            dano_veneno = random.randint(1, 4)
            jogador.hp_atual = max(0, jogador.hp_atual - dano_veneno)
            narrativa += f"🤢 Veneno: Sofres {dano_veneno} de dano direto!\n"

        # Limpeza de status pós-turno
        if Status.ESQUIVANDO in efeitos_atuais:
            efeitos_atuais.remove(Status.ESQUIVANDO)
        set_status_efeitos(jogador, efeitos_atuais)
        campanha.estado_salas = estado

        if jogador.hp_atual <= 0:
            narrativa += self._nocauteado_para_vila(jogador, campanha)
            return ActionResult(True, "combate", narrativa.strip(), {"dano": dano_causado, "acertou": acertou, "contexto_critico": contexto_critico})

        return ActionResult(True, "combate", narrativa.strip(), {"dano": dano_causado, "acertou": acertou, "contexto_critico": contexto_critico})

    # ------------------------------------------------------------------
    # COMBATE — sub-passos
    # ------------------------------------------------------------------

    def _selecionar_inimigo(self, cena: Optional[Cena], estado: Dict[str, Any]) -> Tuple[Optional[Encontro], Optional[Inimigo]]:
        if not cena:
            return None, None
        encontros = self.db.execute(select(Encontro).filter(Encontro.cod_sala == cena.cod_sala)).scalars().all()
        encontros_vivos = [e for e in encontros if not estado.get(f"derrotado_{e.id}")]
        if not encontros_vivos:
            return None, None
        # TODO: permitir escolha de alvo — por enquanto pega o primeiro encontro vivo
        encontro = encontros_vivos[0]
        inimigo = self.db.execute(select(Inimigo).filter(Inimigo.nome == encontro.nome_inimigo)).scalars().first()
        return encontro, inimigo

    @staticmethod
    def _aplicar_furia_boss(inimigo: Inimigo, hp_grupo: int, hp_max_grupo: int, estado: Dict[str, Any]) -> bool:
        # BUG #6 FIX: Comparar HP do grupo (escalando) contra HP máximo do GRUPO, não de um inimigo
        if getattr(inimigo, "is_boss", False) and hp_max_grupo > 0 and 0 < hp_grupo <= (hp_max_grupo / 2):
            return True
        return False

    @staticmethod
    def _calcular_modificadores_combate(jogador: JogadorWeb, estilo: Optional[str], efeitos: List[str]) -> Tuple[bool, bool, str]:
        vantagem = estilo in ("furtivo", "temerario")
        desvantagem = any(s in efeitos for s in (Status.CAIDO, Status.CAIDO_ALT))
        str_vant = ""
        if vantagem and not desvantagem: str_vant = "(Vantagem)"
        if desvantagem: str_vant = "(Desvantagem)"
        return vantagem, desvantagem, str_vant

    def _aplicar_keyword_classe(
        self, jogador: JogadorWeb, campanha: CampanhaWeb, texto: str, efeitos_atuais: List[str],
    ) -> Tuple[int, str]:
        dano_extra = 0
        msg = ""
        mod_ataque_orig = getattr(jogador, "modificador_ataque", 0)
        mod_defesa_orig = getattr(jogador, "modificador_defesa", 10)

        cls = jogador.classe.lower()
        texto_low = texto.lower()
        for kw_texto, kw_efeitos in KEYWORDS_POR_CLASSE.get(cls, {}).items():
            if kw_texto not in texto_low: continue

            if kw_efeitos.get("bonus_dano"): dano_extra += kw_efeitos["bonus_dano"]
            if kw_efeitos.get("bonus_ataque"): jogador.modificador_ataque = mod_ataque_orig + kw_efeitos["bonus_ataque"]
            if kw_efeitos.get("bonus_ca"): jogador.modificador_defesa = mod_defesa_orig + kw_efeitos["bonus_ca"]
            if kw_efeitos.get("desvantagem_inimigo"):
                estado = dict(campanha.estado_salas or {})
                estado["inimigo_debilidade"] = True
                campanha.estado_salas = estado

            # Fúria → status persistente
            if kw_texto == "fúria" and Status.FURIA not in efeitos_atuais:
                efeitos_atuais.append(Status.FURIA)
                set_status_efeitos(jogador, efeitos_atuais)

            # Surto de Ação → status persistente (guerreiro apenas)
            if kw_texto == "surto" and Status.SURTO not in efeitos_atuais:
                efeitos_atuais.append(Status.SURTO)
                set_status_efeitos(jogador, efeitos_atuais)

            msg = f"\n⚡ <i>{kw_texto.title()} ativado!</i>"
            break
        return dano_extra, msg

    def _ataque_jogador(
        self,
        *,
        jogador: JogadorWeb,
        ca_alvo: int,
        estilo: Optional[str],
        alvo_nome: Optional[str],
        texto: str,
        dano_extra: int,
        keyword_feature_msg: str,
        efeitos_atuais: List[str],
        hp_grupo: int,
        hp_max_inimigo: int,
        chave_hp: str,
        estado: Dict[str, Any],
        campanha: CampanhaWeb,
        encontro: Encontro,
        inimigo: Inimigo,
        is_durnn_furia: bool,
    ) -> Tuple[int, bool, str, Dict[str, Any]]:
        vantagem, desvantagem, str_vantagem = self._calcular_modificadores_combate(jogador, estilo, efeitos_atuais)
        if Status.AJUDADO in efeitos_atuais:
            vantagem = True
            str_vantagem = "(Vantagem)"
            efeitos_atuais.remove(Status.AJUDADO)
            set_status_efeitos(jogador, efeitos_atuais)

        resultado = processar_ataque_fisico(
            jogador=jogador, inimigo_ca=ca_alvo, defensor_status=[],
            tipo_ataque="melee", vantagem_extra=vantagem, desvantagem_extra=desvantagem,
            inimigo_resistencias=getattr(inimigo, 'resistencias', None),
            inimigo_vulnerabilidades=getattr(inimigo, 'vulnerabilidades', None),
            inimigo_imunidades=getattr(inimigo, 'imunidades', None),
        )

        dados_str, mod_calc = self._formatar_detalhes_d20(resultado)
        mod_str = f"+{mod_calc}" if isinstance(mod_calc, int) and mod_calc >= 0 else str(mod_calc)
        str_vant = f" {str_vantagem}" if str_vantagem else ""

        # Contexto para imagens criticas
        contexto_critico = {}
        if resultado.critico or resultado.d20 == 1:
            contexto_critico = {
                "tipo": "critico_acerto" if resultado.critico else "critico_falha",
                "d20": resultado.d20,
                "atacante": jogador.nome,
                "classe": getattr(jogador, "classe", "Guerreiro"),
                "arma": getattr(jogador, "arma_equipada", "Desarmado"),
                "alvo": inimigo.nome if inimigo else "Desconhecido",
                "dano": resultado.dano if resultado.critico else 0,
                "texto_jogador": texto[:100],
            }

        if not resultado.acertou:
            narrativa = f"🎲 Dados: d20={dados_str}{str_vant}{mod_str}={resultado.total_ataque} vs CA {ca_alvo} ❌\n💨 Ataque falhou\n"
            return 0, False, narrativa, contexto_critico

        # Dano base + habilidades + keyword
        dano_causado, dano_habilidade, texto_furia, dano_extra_furtivo = self._calcular_dano_total(
            jogador=jogador, estilo=estilo, resultado=resultado,
            dano_extra=dano_extra, texto=texto, efeitos_atuais=efeitos_atuais,
        )
        # Vulnerabilidade da Árvore Gulthias ao fogo (centralizada em game_helpers)
        # Guard: só aplicar se NÃO foi já coberta por calcular_dano_com_resistencias
        inimigo_vulns = getattr(inimigo, 'vulnerabilidades', None) or []
        ja_coberto = "fogo" in inimigo_vulns
        narrativa_vuln = ""
        if not ja_coberto and calcular_vulnerabilidade_fogo(alvo_nome, texto):
            dano_causado *= 2
            narrativa_vuln = "🔥 VULNERÁVEL! O fogo causa o dobro do dano!\n"

        # Mortalidade do grupo de inimigos
        vivos_antes = math.ceil(hp_grupo / hp_max_inimigo) if hp_grupo > 0 else 0
        hp_grupo -= dano_causado
        vivos_depois = math.ceil(hp_grupo / hp_max_inimigo) if hp_grupo > 0 else 0
        mortos_turno = vivos_antes - vivos_depois
        texto_crit = "💥 CRÍTICO! Dano: " if resultado.critico else "💥 Dano: "
        texto_morte = f" (💀 {mortos_turno} eliminado{'s' if mortos_turno > 1 else ''}!)" if mortos_turno > 0 else ""

        narrativa = (
            f"🎲 Dados: d20={dados_str}{str_vant}{mod_str}={resultado.total_ataque} vs CA {ca_alvo} ✅\n"
            f"{texto_crit}{dano_causado}{texto_morte}\n"
        )
        if dano_extra_furtivo: narrativa += f" (Inclui +{dano_extra_furtivo} Furtivo)\n"
        if dano_habilidade: narrativa += f" (+{dano_habilidade} de Habilidades)\n"
        if dano_extra: narrativa += f" (+{dano_extra} de Classe)\n"
        narrativa += f"{texto_furia}{keyword_feature_msg}\n{narrativa_vuln}"

        estado["hp_grupo"] = hp_grupo
        estado[chave_hp] = hp_grupo

        # Vitória?
        if hp_grupo <= 0:
            narrativa += self._vitoria_combate(jogador, campanha, encontro, inimigo, estado)
        else:
            if is_durnn_furia: narrativa += "\n😡 O Boss entrou em Fúria Sanguinária!\n"
            # Surto de ação do guerreiro
            narrativa_surto, hp_grupo = self._surto_acao_guerreiro(
                jogador=jogador, ca_alvo=ca_alvo, estado=estado, chave_hp=chave_hp,
                hp_grupo=hp_grupo, hp_max_inimigo=hp_max_inimigo,
                efeitos_atuais=efeitos_atuais, campanha=campanha,
                encontro=encontro, inimigo=inimigo,
            )
            narrativa += narrativa_surto

        return dano_causado, True, narrativa, contexto_critico

    @staticmethod
    def _formatar_detalhes_d20(resultado: Any) -> Tuple[str, Any]:
        detalhes = resultado.detalhes_d20
        mod_calc = "?"
        try:
            if isinstance(detalhes, list): dados_str = f"[{', '.join(map(str, detalhes))}]"
            elif isinstance(detalhes, int): dados_str = f"[{detalhes}]"
            else: dados_str = f"[{detalhes}]"
            if isinstance(detalhes, int): mod_calc = resultado.total_ataque - detalhes
        except Exception: dados_str = f"[{detalhes}]"
        return dados_str, mod_calc

    def _calcular_dano_total(
        self, *, jogador: JogadorWeb, estilo: Optional[str], resultado: Any,
        dano_extra: int, texto: str, efeitos_atuais: List[str],
    ) -> Tuple[int, int, str, int]:
        dano = resultado.dano
        habilidade = 0

        # Smite (modifica efeitos_atuais in-place; o caller persiste com set_status_efeitos)
        if Status.SMITE in efeitos_atuais:
            dados_smite = min(5, 2 + (jogador.nivel // 4))
            habilidade += sum(random.randint(1, 8) for _ in range(dados_smite))
            efeitos_atuais.remove(Status.SMITE)

        # Forma Selvagem
        if Status.FORMA_SELVAGEM in efeitos_atuais:
            habilidade += sum(random.randint(1, 6) for _ in range(2))
            efeitos_atuais.remove(Status.FORMA_SELVAGEM)

        # Fúria do Bárbaro
        msg_furia = ""
        if Status.FURIA in efeitos_atuais:
            bonus = 4 if jogador.nivel >= 16 else (3 if jogador.nivel >= 9 else 2)
            habilidade += bonus
            msg_furia = f"\n😡 <b>Fúria Bárbaro:</b> +{bonus} de dano e Resistência Ativada!"

        dano += habilidade + dano_extra

        # Furtivo do Ladino
        furtivo = 0
        if estilo == "furtivo" and jogador.classe.lower() == "ladino":
            dados_furtivo = math.ceil(jogador.nivel / 2)
            furtivo = sum(random.randint(1, 6) for _ in range(dados_furtivo))
            dano += furtivo

        return dano, habilidade, msg_furia, furtivo

    def _vitoria_combate(self, jogador: JogadorWeb, campanha: CampanhaWeb,
                         encontro: Encontro, inimigo: Inimigo, estado: Dict[str, Any]) -> str:
        estado[f"derrotado_{encontro.id}"] = True
        campanha.em_combate = False

        xp_total = getattr(inimigo, "xp_recompensa", 50) * encontro.quantidade
        ouro_total = getattr(inimigo, "ouro_recompensa", 5) * encontro.quantidade

        # Contar jogadores vivos na party para split
        num_players = self.db.query(func.count()).select_from(JogadorWeb).filter(
            JogadorWeb.party_id == campanha.party_id,
            JogadorWeb.hp_atual > 0,
        ).scalar() or 1

        # XP: todos recebem integral (regra D&D 5e)
        jogadores_party = self.db.query(JogadorWeb).filter(
            JogadorWeb.party_id == campanha.party_id,
            JogadorWeb.hp_atual > 0,
        ).all()
        for j in jogadores_party:
            j.xp += xp_total

        # Gold: split igual; executor ganha remainder
        gold_split = split_gold(ouro_total, num_players)
        # Garantir que o executor (jogador que deu o golpe final) recebe o remainder
        executor_idx = next((i for i, j in enumerate(jogadores_party) if j.telefone == jogador.telefone), 0)
        if executor_idx != 0 and executor_idx < num_players:
            gold_split[executor_idx], gold_split[0] = gold_split[0], gold_split[executor_idx]
        for idx, j in enumerate(jogadores_party):
            j.gold += gold_split.get(idx, 0)

        executor_gold = gold_split.get(executor_idx, ouro_total)
        narrativa = f"\n🏆 VITÓRIA! O grupo recebe {xp_total} XP cada."
        if num_players > 1:
            narrativa += f" Gold: {executor_gold} PO para ti, split entre {num_players} jogadores ({ouro_total} PO total).\n"
        else:
            narrativa += f" {ouro_total} PO.\n"

        # Loot (itens ficam com quem executou — item é físico)
        loot = gerar_loot_inimigo_comum()
        if loot:
            itens = adicionar_ao_inventario(jogador, loot)
            if itens: narrativa += f"🎁 Saque: {', '.join(itens)}\n"

        # Level-up (checar para todos os jogadores da party)
        for j in jogadores_party:
            if j.xp >= XP_POR_NIVEL.get(j.nivel + 1, 999_999):
                narrativa += self._aplicar_level_up(j)

        return narrativa

    def _surto_acao_guerreiro(
        self, *, jogador: JogadorWeb, ca_alvo: int, estado: Dict[str, Any],
        chave_hp: str, hp_grupo: int, hp_max_inimigo: int,
        efeitos_atuais: List[str], campanha: CampanhaWeb,
        encontro: Encontro, inimigo: Inimigo,
    ) -> Tuple[str, int]:
        efeitos = list(getattr(jogador, "status_efeitos", []) or [])
        if Status.SURTO not in efeitos or hp_grupo <= 0:
            return "", hp_grupo

        efeitos.remove(Status.SURTO)
        set_status_efeitos(jogador, efeitos)

        res = processar_ataque_fisico(
            jogador=jogador, inimigo_ca=ca_alvo, defensor_status=[], tipo_ataque="melee",
        )
        if not res.acertou:
            return "\n⚔️ <b>Surto de Ação!</b> Ataque extra falhou! ❌\n", hp_grupo

        vivos_antes = math.ceil(hp_grupo / hp_max_inimigo) if hp_grupo > 0 else 0
        hp_grupo -= res.dano
        vivos_depois = math.ceil(hp_grupo / hp_max_inimigo) if hp_grupo > 0 else 0
        mortos = vivos_antes - vivos_depois
        estado[chave_hp] = hp_grupo
        crit = "💥 CRÍTICO! Dano: " if res.critico else "💥 Dano: "
        morte = f" (💀 {mortos} eliminado{'s' if mortos > 1 else ''}!)" if mortos > 0 else ""
        narrativa = f"\n⚔️ <b>Surto de Ação!</b> Ataque extra! ✅\n{crit}{res.dano}{morte}\n"

        if hp_grupo <= 0:
            narrativa += self._vitoria_combate(jogador, campanha, encontro, inimigo, estado)
        return narrativa, hp_grupo

    @staticmethod
    def _aplicar_level_up(jogador: JogadorWeb) -> str:
        # Delega SEMPRE para a implementação canônica em game_helpers.
        # A duplicação local foi removida para evitar divergências de lógica.
        try:
            niveis = aplicar_level_up(jogador)
            if niveis > 0:
                return f"🌟 Subiste para o Nível {jogador.nivel}! HP, Magia e Hit Dice atualizados!\n"
        except Exception as e:
            logger.warning("[LEVEL UP] Falha ao delegar para game_helpers: %s", e)
        return ""

    # ------------------------------------------------------------------
    # REVIDE DO INIMIGO
    # ------------------------------------------------------------------

    def _resolver_revide_inimigo(
        self, jogador: JogadorWeb, campanha: CampanhaWeb,
        encontro: Encontro, inimigo: Inimigo,
        hp_grupo: int, hp_max_inimigo: int,
        efeitos_atuais: List[str], is_durnn_furia: bool,
    ) -> Tuple[str, List[str]]:
        narrativa = ""
        dan_final = 0

        if not (campanha.em_combate and hp_grupo > 0):
            return narrativa, efeitos_atuais

        vivos_agora = math.ceil(hp_grupo / hp_max_inimigo)
        mod_inimigo = _parse_mod_ataque(inimigo.ataque)

        # Contar jogadores vivos na mesma sala
        result_count = self.db.execute(select(func.count()).select_from(JogadorWeb).filter(
            JogadorWeb.party_id == campanha.party_id,
            JogadorWeb.hp_atual > 0,
            JogadorWeb.cena_atual == campanha.cena_atual,
        ))
        jogadores_vivos = result_count.scalar() or 1
        limite_ataques = jogadores_vivos + (getattr(encontro, "multiplicador_ameaca", 1) or 1)
        atacantes = min(vivos_agora, limite_ataques)

        narrativa += f"⚠️ ATAQUE INIMIGO: {atacantes}x {inimigo.nome} {'ataca' if atacantes == 1 else 'atacam'}! (De {vivos_agora} vivos)\n"
        acertos = 0

        # ESQUIVANDO (Dodge): desvantagem nos ataques inimigos (D&D 5e)
        tem_desvantagem = Status.ESQUIVANDO in efeitos_atuais

        for i in range(atacantes):
            # Vantagem do inimigo (ex: Fúria de Durnn) vs Desvantagem do jogador (Esquivando)
            # Em D&D 5e, vantagem e desvantagem cancelam-se → rolagem normal
            if is_durnn_furia and tem_desvantagem:
                d20 = random.randint(1, 20)
            elif is_durnn_furia:
                d20 = max(random.randint(1, 20), random.randint(1, 20))
            elif tem_desvantagem:
                d20 = min(random.randint(1, 20), random.randint(1, 20))
            else:
                d20 = random.randint(1, 20)

            if d20 + mod_inimigo >= jogador.modificador_defesa or d20 == 20:
                acertos += 1
                # Usar dano do bestiário em vez de 1d4 hardcoded
                try:
                    qtd_d, faces_d, mod_d = parse_dice_string(inimigo.dano)
                    dano_base, _ = rolar_dados(qtd_d, faces_d, mod_d)
                except Exception:
                    dano_base = random.randint(1, 4)  # fallback seguro
                if is_durnn_furia: dano_base += 2
                if d20 == 20:
                    # BUG #4 FIX: Crit dobra os DADOS (não o modifier) — D&D 5e
                    dano_crit_extra, _ = rolar_dados(qtd_d, faces_d, 0)
                    dano_base += dano_crit_extra
                dan_final += dano_base
                narrativa += f"🗡️ Atk {i + 1}: Hit ({dano_base} dano)\n"
            else:
                narrativa += f"💨 Atk {i + 1}: Miss\n"

        if acertos == 0:
            narrativa += "🛡️ Esquivaste todos os ataques!\n\n"
            return narrativa, efeitos_atuais

        # Redução de dano pela Fúria
        if Status.FURIA in efeitos_atuais:
            original = dan_final
            dan_final = max(1, dan_final // 2)
            narrativa += f"🛡️ A tua Fúria reduziu o dano sofrido pela metade! (Original: {original})\n"

        narrativa += f"🩸 Dano total recebido: {dan_final}\n\n"
        jogador.hp_atual = max(0, jogador.hp_atual - dan_final)

        # Possível envenenamento
        if (random.randint(1, 100) <= CHANCE_ENVENENAR
            and Status.ENVENENADO not in efeitos_atuais
            and any(n in inimigo.nome.lower() for n in INIMIGOS_VENENOSOS)):
            efeitos_atuais.append(Status.ENVENENADO)
            narrativa += "🤢 Foste Envenenado pelo ataque inimigo!\n\n"

        return narrativa, efeitos_atuais

    # ------------------------------------------------------------------
    # ATAQUE A OBJETO
    # ------------------------------------------------------------------

    def _resolver_ataque_objeto(
        self, jogador: JogadorWeb, cena: Optional[Cena],
        alvo_nome: Optional[str], texto: str,
    ) -> ActionResult:
        if not cena:
            return ActionResult(False, "combate", "Não há alvos válidos para atacar aqui.", {})

        objs = self.db.execute(select(ObjetoDestrutivel).filter(
            ObjetoDestrutivel.cod_sala == cena.cod_sala,
            ObjetoDestrutivel.ativo.is_(True),
        )).scalars().all()

        alvo = next(
            (o for o in objs if alvo_nome and alvo_nome.lower() in o.nome.lower()),
            objs[0] if objs else None,
        )
        if not alvo:
            return ActionResult(False, "combate", "Não há alvos válidos para atacar aqui.", {})

        res = processar_ataque_objeto(jogador, alvo)
        if res.quebrou_por_forca:
            alvo.hp_atual = 0
            alvo.ativo = False
            return ActionResult(True, "combate", f"💪 Força bruta! {alvo.nome} destruído.", {})
        if res.acertou:
            alvo.hp_atual = res.hp_restante
            if res.destruido:
                alvo.ativo = False
                loot = getattr(alvo, "recompensa_ao_destruir", []) or []
                if loot: adicionar_ao_inventario(jogador, loot)
                return ActionResult(True, "combate", f"🔨 {alvo.nome} destruído! Dano: {res.dano}", {})
            return ActionResult(True, "combate",
                f"💥 Acertaste {alvo.nome}. Dano: {res.dano}. HP restante: {alvo.hp_atual}/{alvo.hp_max}", {})
        return ActionResult(False, "combate", f"Errouste o golpe em {alvo.nome}.", {})

    # ------------------------------------------------------------------
    # MAGIA
    # ------------------------------------------------------------------

    def _resolver_magia(
        self, jogador: JogadorWeb, campanha: CampanhaWeb,
        cena: Optional[Cena], magia_nome: Optional[str],
        alvo_nome: Optional[str], texto: str,
    ) -> ActionResult:
        # Cantrips (truques) não gastam slots de magia em D&D 5e
        CANTRIPS_POR_CLASSE = {
            "clérigo": {"chama sagrada", "guidance", "sacred flame", "produce flame", "thaumaturgy"},
            "druida": {"chicote de espinhos", "shillelagh", "thunderclap", "druidcraft", "produce flame"},
            "mago": {"rajada arcana", "fire bolt", "mage hand", "minor illusion", "prestidigitation", "ray of frost", "shocking grasp"},
            "feiticeiro": {"fire bolt", "mage hand", "minor illusion", "prestidigitation", "shocking grasp"},
            "bruxo": {"rajada mística", "eldritch blast", "minor illusion", "prestidigitation"},
            "bardo": {"onda trovejante", "vicious mockery", "minor illusion", "prestidigitation"},
        }
        cls = jogador.classe.lower()
        nome_magia = (magia_nome or "").lower().strip()
        cantrips_cls = CANTRIPS_POR_CLASSE.get(cls, set())
        eh_cantrip = nome_magia in cantrips_cls

        # Validar se a magia é conhecida antes de gastar slot
        chave_classe = cls if cls in MAGIAS_POR_CLASSE else "default"
        magia_da_classe = MAGIAS_POR_CLASSE.get(chave_classe, {}).get("nome", "").lower()
        nome_fornecido = bool(nome_magia)
        eh_magia_conhecida = (not nome_fornecido  # usa default da classe
                              or nome_magia in magia_da_classe
                              or magia_da_classe in nome_magia)  # match parcial

        if not eh_cantrip and not eh_magia_conhecida:
            magia_default = MAGIAS_POR_CLASSE.get(chave_classe, {}).get("nome", "desconhecida")
            return ActionResult(False, "magia",
                f"✨ '{magia_nome}' não é uma magia conhecida pelo {jogador.classe}.\n"
                f"Magia disponível: {magia_default}. Cantrips: {', '.join(sorted(cantrips_cls)[:3])}...", {})

        if not eh_cantrip and jogador.slots_magia <= 0:
            return ActionResult(False, "magia", "✨ Sem Usos de Magia restantes!", {})

        if not eh_cantrip:
            jogador.slots_magia -= 1
        magia_info = dict(MAGIAS_POR_CLASSE[chave_classe])
        if magia_nome: magia_info["nome"] = magia_nome

        # Backup dos stats que serão alterados pela magia
        mod_atk_orig = jogador.modificador_ataque
        dano_dado_orig = jogador.dano_dado
        # Modificador de ataque mágico depende da classe (D&D 5e)
        _CASTING_MOD = {"mago": "int", "clérigo": "wis", "druida": "wis", "patrulheiro": "wis",
                        "feiticeiro": "cha", "bardo": "cha", "bruxo": "cha", "paladino": "cha"}
        _attr = _CASTING_MOD.get(cls, "cha")
        jogador.modificador_ataque = getattr(jogador, f"mod_{_attr}", jogador.mod_cha) + jogador.proficiencia
        jogador.dano_dado = magia_info.get("dano", "1d8")

        try:
            resultado = self._resolver_combate(jogador, campanha, cena, alvo_nome, None, texto, is_magia=True)
        finally:
            jogador.modificador_ataque = mod_atk_orig
            jogador.dano_dado = dano_dado_orig

        resultado.tipo_acao = "magia"
        resultado.narrativa_mecanica = (
            f"{magia_info.get('icone', '🔮')} {magia_info.get('nome', 'Magia')}: "
            + resultado.narrativa_mecanica
        )
        return resultado

    # ------------------------------------------------------------------
    # MANOBRA
    # ------------------------------------------------------------------

    def _resolver_manobra(
        self, jogador: JogadorWeb, campanha: CampanhaWeb,
        cena: Optional[Cena], manobra: Optional[str],
        alvo_nome: Optional[str], texto: str,
    ) -> ActionResult:
        efeitos = list(getattr(jogador, "status_efeitos", []) or [])

        # Levantar (saída de "Caído")
        if manobra and "levantar" in manobra.lower():
            if Status.CAIDO in efeitos or Status.CAIDO_ALT in efeitos:
                self._remover_status(jogador, Status.CAIDO, Status.CAIDO_ALT)
                return ActionResult(True, "manobra", "🏃 Levantaste-te! Já não estás Caído.", {})
            return ActionResult(False, "manobra", "Já estás de pé.", {})

        # Escapar de agarrado
        if Status.AGARRADO in efeitos:
            rolagem = random.randint(1, 20) + jogador.mod_str + jogador.proficiencia
            if rolagem >= 14:
                self._remover_status(jogador, Status.AGARRADO)
                return ActionResult(True, "manobra", f"🔓 Escapaste! (STR {rolagem} vs CD 14)", {})
            return ActionResult(False, "manobra", f"❌ Falhaste em libertar-te. (STR {rolagem} vs CD 14)", {})

        # Empurrar / Derrubar (manobras de combate)
        mod = jogador.mod_str if manobra in ("empurrar", "derrubar") else jogador.mod_dex
        rolagem = random.randint(1, 20) + mod + jogador.proficiencia
        if rolagem >= 14:
            estado = dict(campanha.estado_salas or {})
            estado["inimigo_debilidade"] = True
            campanha.estado_salas = estado
            return ActionResult(
                True, "manobra",
                f"🤸 Manobra bem sucedida! (Teste {rolagem}). O inimigo ficou vulnerável (Vantagem para o grupo).",
                {},
            )
        return ActionResult(False, "manobra", f"❌ Manobra falhou. (Teste {rolagem})", {})

    # ------------------------------------------------------------------
    # NAVEGAÇÃO
    # ------------------------------------------------------------------

    def _resolver_navegacao(
        self, jogador: JogadorWeb, campanha: CampanhaWeb,
        cena: Optional[Cena], direcao: Optional[str], texto: str,
    ) -> ActionResult:
        """Entrada pública: bloqueia agarrados, decide fuga vs. navegação, delega o resto."""
        if not cena:
            return ActionResult(False, "navegacao", "Não há cena atual.", {})

        efeitos = list(getattr(jogador, "status_efeitos", []) or [])
        if Status.AGARRADO in efeitos:
            return ActionResult(False, "navegacao",
                "⛓️ Estás Agarrado! Não podes mover-te. Usa uma MANOBRA para escapar.", {})

        texto_low = texto.lower()
        is_fuga = any(p in texto_low for p in PALAVRAS_FUGA)
        encontros_vivos = self._encontros_vivos(cena, campanha)

        if encontros_vivos and campanha.em_combate:
            encontro_bloqueio = encontros_vivos[0]
            if is_fuga:
                return self._executar_fuga(jogador, campanha, encontro_bloqueio, texto)
            return ActionResult(False, "navegacao",
                f"🛑 <b>Caminho Bloqueado!</b> Tens de lidar com "
                f"{encontro_bloqueio.nome_inimigo} primeiro ou tentar 'fugir'.", {})

        # 1) Descobrir o alvo (direção explícita, IA, ou cod_sala vinda da fuga)
        if is_fuga:
            # Fuga sem inimigos: resolver direcao pelas conexoes como navegacao normal
            if direcao:
                alvo_sala = self._resolver_alvo_sala(direcao, cena.conexoes or {})
                if not alvo_sala:
                    alvo_sala = campanha.cena_anterior or SALA_INICIO
            else:
                alvo_sala = campanha.cena_anterior or SALA_INICIO
        else:
            direcao_ia = self._descobrir_direcao(texto, direcao, cena)
            if not direcao_ia:
                return ActionResult(False, "navegacao",
                    "Para onde desejas ir? Direção não reconhecida.", {})
            alvo_sala = self._resolver_alvo_sala(direcao_ia, cena.conexoes or {})
            if not alvo_sala:
                return ActionResult(False, "navegacao",
                    f"Caminho bloqueado ou inexistente para '{texto}'.", {})
            direcao = direcao_ia

        return self._mover_para_sala(jogador, campanha, alvo_sala,
            direcao_exibida=direcao if not is_fuga else "uma área segura")

    def _executar_fuga(
        self, jogador: JogadorWeb, campanha: CampanhaWeb,
        encontro_bloqueio: Encontro, texto: str,
    ) -> ActionResult:
        """Resolve o ataque de oportunidade da fuga e depois executa a saída."""
        destino = campanha.cena_anterior or SALA_INICIO
        if campanha.cena_atual == SALA_INICIO:
            return ActionResult(False, "navegacao",
                "🛑 Não tens para onde recuar! Terás que lutar.", {})

        narrativa_fuga = self._rolar_ataque_oportunidade(jogador, campanha, encontro_bloqueio, destino)
        if narrativa_fuga is None:
            return ActionResult(False, "navegacao",
                "🛑 Não tens para onde recuar! Terás que lutar.", {})

        # Vai diretamente para a mudança de sala (sem recursão)
        resultado = self._mover_para_sala(jogador, campanha, destino, direcao_exibida="uma área segura")
        if resultado.narrativa_mecanica.startswith("👣"):
            resultado.narrativa_mecanica = f"{narrativa_fuga}\n\n{resultado.narrativa_mecanica}"
        return resultado

    def _rolar_ataque_oportunidade(
        self, jogador: JogadorWeb, campanha: CampanhaWeb,
        encontro_bloqueio: Encontro, destino: str,
    ) -> Optional[str]:
        if destino == SALA_INICIO and campanha.cena_atual == SALA_INICIO:
            return None

        # BUG #1 FIX: Usar stats reais do inimigo do bestiário (não hardcoded)
        inimigo = self.db.execute(
            select(Inimigo).filter(Inimigo.nome == encontro_bloqueio.nome_inimigo)
        ).scalars().first()

        mod_inimigo = _parse_mod_ataque(inimigo.ataque) if inimigo and inimigo.ataque else 4
        try:
            qtd_d, faces_d, mod_d = parse_dice_string(inimigo.dano) if inimigo and inimigo.dano else (1, 6, 2)
        except Exception:
            qtd_d, faces_d, mod_d = 1, 6, 2
        dano_fuga, _ = rolar_dados(qtd_d, faces_d, mod_d)

        d20 = random.randint(1, 20)
        acertou = (d20 + mod_inimigo >= jogador.modificador_defesa) or d20 == 20

        if acertou:
            jogador.hp_atual = max(0, jogador.hp_atual - dano_fuga)
            narrativa = (f"🩸 <b>Fuga Arriscada!</b> Ao virares as costas, "
                f"{encontro_bloqueio.nome_inimigo} acertou-te um Ataque de Oportunidade! "
                f"Sofreste {dano_fuga} de dano.")
            if jogador.hp_atual <= 0:
                narrativa += self._nocauteado_para_vila(jogador, campanha)
            return narrativa
        return (f"💨 <b>Fuga Ágil!</b> Conseguiste desviar-te do ataque de "
            f"{encontro_bloqueio.nome_inimigo} enquanto recuavas.")

    def _mover_para_sala(
        self, jogador: JogadorWeb, campanha: CampanhaWeb,
        alvo_sala: str, direcao_exibida: str,
    ) -> ActionResult:
        """Faz a transição efetiva para `alvo_sala` (cleanup de status, hazards, knock-out)."""
        self._remover_status(
            jogador,
            Status.COBERTURA, Status.FURIA, Status.ESQUIVANDO,
            Status.AJUDADO, Status.SURTO, Status.SMITE,
            Status.FORMA_SELVAGEM,
        )
        campanha.cena_anterior = campanha.cena_atual
        campanha.cena_atual = alvo_sala
        jogador.cena_atual = alvo_sala

        nova_cena = self.db.execute(select(Cena).filter(Cena.cod_sala == alvo_sala)).scalars().first()
        narrativa_hazard = self._aplicar_hazards(jogador, nova_cena)

        texto_final = f"👣 Segues para {direcao_exibida}."
        if narrativa_hazard: texto_final = f"{texto_final}\n{narrativa_hazard}"

        if jogador.hp_atual <= 0:
            texto_final += self._nocauteado_para_vila(jogador, campanha)
            return ActionResult(False, "navegacao", texto_final.strip(), {"nova_cena": SALA_INICIO})

        return ActionResult(True, "navegacao", texto_final.strip(), {"nova_cena": alvo_sala})

    def _encontros_vivos(self, cena: Cena, campanha: CampanhaWeb) -> List[Encontro]:
        estado = dict(campanha.estado_salas or {})
        encontros = self.db.execute(select(Encontro).filter(Encontro.cod_sala == cena.cod_sala)).scalars().all()
        return [e for e in encontros if not estado.get(f"derrotado_{e.id}")]

    def _descobrir_direcao(self, texto: str, direcao: Optional[str], cena: Cena) -> Optional[str]:
        if direcao: return direcao.lower().strip()
        dir_ia = extrair_direcao_sync(texto, cena.conexoes or {})
        if dir_ia and "invalido" not in dir_ia.lower():
            return dir_ia.lower().strip()
        return None

    @staticmethod
    def _resolver_alvo_sala(direcao: str, conexoes: Dict[str, str]) -> Optional[str]:
        direcao_low = direcao.lower().strip()
        # 1) Match exato case-insensitive contra as chaves de conexão
        for k, v in conexoes.items():
            if direcao_low == k.lower():
                return v
        # 2) Match parcial (substring) — como no rpg_bot
        for k, v in conexoes.items():
            if direcao_low in k.lower() or k.lower() in direcao_low:
                return v
        # 3) Sinônimos com match parcial
        for grupo in SINONIMOS_DIRECAO.values():
            if direcao_low in grupo:
                for k, v in conexoes.items():
                    if any(s in k.lower() for s in grupo):
                        return v
        return None

    def _aplicar_hazards(self, jogador: JogadorWeb, nova_cena: Optional[Cena]) -> str:
        if not nova_cena: return ""
        # Delegado para game_helpers.aplicar_hazards (versão canônica com parse_dice_string).
        hazards = getattr(nova_cena, "hazards", None) or []
        return aplicar_hazards_gh(jogador, hazards)

    @staticmethod
    def _rolar_dano(dano_str: str) -> int:
        try:
            qtd, faces, mod = parse_dice_string(dano_str)
            total, _ = rolar_dados(qtd, faces, mod)
            return total
        except Exception:
            try:
                m = re.match(r'(\d+)d(\d+)([+-]\d+)?', str(dano_str))
                if m:
                    qtd = int(m.group(1)) if m.group(1) else 1
                    faces = int(m.group(2))
                    mod = int(m.group(3)) if m.group(3) else 0
                    return sum(random.randint(1, faces) for _ in range(qtd)) + mod
            except Exception:
                pass
            return random.randint(1, 4)

    # ------------------------------------------------------------------
    # INTERAÇÃO
    # ------------------------------------------------------------------

    def _resolver_interacao(
        self, jogador: JogadorWeb, campanha: CampanhaWeb,
        cena: Optional[Cena], alvo_nome: Optional[str],
        item: Optional[str], texto: str,
    ) -> ActionResult:
        if not cena:
            return ActionResult(False, "interacao", "Não há cena atual.", {})

        texto_low = texto.lower()

        # 1) Vasculhar sala (loot fixo)
        if any(p in texto_low for p in PALAVRAS_VASCULHAR) and getattr(cena, "loot_fixo", None):
            itens = adicionar_ao_inventario(jogador, cena.loot_fixo)
            cena.loot_fixo = []
            return ActionResult(True, "interacao",
                f"👀 Vasculhaste a sala e encontraste: {', '.join(itens)}.", {})

        # 2) Usar poção / antídoto
        if item and any(p in item.lower() for p in PALAVRAS_BEBER_POCAO):
            em_combate = getattr(campanha, "em_combate", False)
            estado_combate = dict(getattr(campanha, "estado_salas", {}) or {})
            resultado = self._usar_pocao(jogador, item, em_combate=em_combate, estado=estado_combate)
            # BUG #7 FIX: Persistir estado da poção usada de volta ao campanha
            if em_combate:
                campanha.estado_salas = estado_combate
            return resultado

        # 3) NPCs (inclui missão do Ferreiro)
        resultado_npc = self._interagir_npcs(jogador, cena, alvo_nome, texto_low)
        if resultado_npc: return resultado_npc

        # 4) Interativos (baús, armadilhas, portas)
        resultado_interativo = self._interagir_objetos(jogador, campanha, cena, alvo_nome, texto_low)
        if resultado_interativo: return resultado_interativo

        return ActionResult(False, "interacao", "Não encontraste nada de útil para interagir diretamente.", {})

    def _usar_pocao(self, jogador: JogadorWeb, item: str, em_combate: bool = False, estado: dict = None) -> ActionResult:
        # BUG #7 FIX: Limitar 1 poção por turno em combate (D&D 5e: Bonus Action)
        if em_combate and estado is not None:
            if estado.get("pocao_usada_turno"):
                return ActionResult(False, "interacao", "⚡ Já usaste uma poção neste turno! Guarda-a para o próximo.", {})
            estado["pocao_usada_turno"] = True
        inv = obter_inventario_limpo(jogador.inventario)
        item_no_inv = next((i for i in inv if item.lower() in i.lower()), None)
        if not item_no_inv:
            return ActionResult(False, "interacao", f"Não tens {item} no inventário.", {})

        inv.remove(item_no_inv)
        set_inventario(jogador, inv)

        if "antídoto" in item_no_inv.lower() or "antidoto" in item_no_inv.lower():
            self._remover_status(jogador, Status.ENVENENADO)
            return ActionResult(True, "interacao", f"🧪 Bebeste {item_no_inv}. Veneno neutralizado!", {})

        # AR-3 FIX: Não consumir poção se HP já está cheio
        if jogador.hp_atual >= jogador.hp_maximo:
            inv.append(item_no_inv)  # devolver ao inventário
            set_inventario(jogador, inv)
            return ActionResult(False, "interacao",
                f"❤️ HP já está no máximo ({jogador.hp_maximo}/{jogador.hp_maximo}). "
                f"{item_no_inv} não foi consumido.", {})

        # Buscar dado de cura do LOJA_CARVALHAL (ex: "2d4+2", "4d4+4", "8d4+8", "10d4+20")
        dano_str = "2d4+2"  # fallback para Poção de Cura básica
        for nome_loja, dados_loja in LOJA_CARVALHAL.items():
            if item_no_inv.lower() in nome_loja.lower() or nome_loja.lower() in item_no_inv.lower():
                dano_str = dados_loja.get("dano", "2d4+2")
                break
        qtd, faces, mod = parse_dice_string(dano_str)
        cura, _ = rolar_dados(qtd, faces, mod)
        jogador.hp_atual = min(jogador.hp_maximo, jogador.hp_atual + cura)
        return ActionResult(True, "interacao", f"🧪 Bebeste {item_no_inv}. Curaste {cura} HP!", {})

    def _interagir_npcs(
        self, jogador: JogadorWeb, cena: Cena,
        alvo_nome: Optional[str], texto_low: str,
    ) -> Optional[ActionResult]:
        npcs = self.db.execute(select(Npc).filter(Npc.cod_sala == cena.cod_sala)).scalars().all()
        for npc in npcs:
            nome_npc = getattr(npc, 'nome', '') or ''
            nome_primeiro = nome_npc.lower().split()[0] if nome_npc.strip() else ''
            if not ((alvo_nome and nome_npc and alvo_nome.lower() in nome_npc.lower())
                or (nome_primeiro and nome_primeiro in texto_low)):
                continue
            dialogo = npc.dialogo_base
            inv = obter_inventario_limpo(jogador.inventario)
            if npc.item_gatilho and any(npc.item_gatilho.lower() in i.lower() for i in inv):
                dialogo = npc.dialogo_item_especial or npc.dialogo_base

            # Missão do Ferreiro
            if "ferreiro" in npc.nome.lower():
                resultado_missao = self._resolver_missao_ferreiro(jogador, npc, dialogo, inv)
                if resultado_missao: return resultado_missao

            return ActionResult(True, "interacao",
                f"🗣️ Falaste com {npc.nome}:\n\"{dialogo}\"", {})

        return None

    def _resolver_missao_ferreiro(
        self, jogador: JogadorWeb, npc: Npc, dialogo: str, inv: List[str],
    ) -> Optional[ActionResult]:
        missao = self.db.execute(select(Missao).filter(
            Missao.jogador_telefone == jogador.telefone,
            Missao.npc_nome == "Ferreiro de Carvalhal",
        )).scalars().first()
        qtd_dentes = sum(1 for i in inv if "Dente de Goblin" in i)

        if not missao:
            self.db.add(Missao(
                jogador_telefone=jogador.telefone,
                party_id=jogador.party_id,
                npc_nome="Ferreiro de Carvalhal",
                titulo="Lâminas e Dentes", descricao="Traz-me 3 Dentes de Goblin como prova de abate.",
                objetivo_item="Dente de Goblin", objetivo_quantidade=3,
                objetivo_total=3,
                recompensa_ouro=50, recompensa_xp=150,
            ))
            return ActionResult(True, "interacao",
                f"🔨 {npc.nome}:\n\"{dialogo}\"\n\n📜 Nova Missão: Lâminas e Dentes. (Anotado no teu /missoes)", {})

        if not missao.concluida and qtd_dentes >= missao.objetivo_quantidade:
            remover = missao.objetivo_quantidade
            removidos = 0
            for i in range(len(inv) - 1, -1, -1):
                if removidos >= remover:
                    break
                if "Dente de Goblin" in inv[i]:
                    inv.pop(i)
                    removidos += 1
            if removidos < remover:
                logger.warning("[MISSÃO FERREIRO] Removidos %s/%s Dentes de Goblin — inventário inconsistente.", removidos, remover)
            set_inventario(jogador, inv)
            jogador.gold += missao.recompensa_ouro
            jogador.xp += missao.recompensa_xp
            missao.concluida = True
            return ActionResult(True, "interacao",
                f"🔨 {npc.nome}:\n"
                f"\"Pelos Deuses, tu conseguiste mesmo! Aqui está o pagamento.\"\n\n"
                f"✅ Missão Concluída!\n🪙 +{missao.recompensa_ouro} PO\n🌟 +{missao.recompensa_xp} XP", {})
        return None

    def _interagir_objetos(
        self, jogador: JogadorWeb, campanha: CampanhaWeb,
        cena: Cena, alvo_nome: Optional[str], texto_low: str,
    ) -> Optional[ActionResult]:
        interativos = self.db.execute(select(Interativo).filter(
            Interativo.cod_sala == cena.cod_sala, Interativo.ativo.is_(True),
        )).scalars().all()
        for obj in interativos:
            if not ((alvo_nome and alvo_nome.lower() in obj.nome.lower())
                or (obj.tipo.lower() in texto_low)):
                continue

            atributo_base = obj.atributo_teste
            mod = getattr(jogador, f"mod_{atributo_base.lower()}", 0)
            bonus_prof = self._bonus_proficiencia(jogador, atributo_base)
            total = random.randint(1, 20) + mod + bonus_prof

            if total >= obj.cd_teste:
                obj.ativo = False
                loot = obj.recompensa if obj.recompensa else []
                if obj.tipo == "bau": loot = gerar_loot_bau(jogador.nivel)
                itens = adicionar_ao_inventario(jogador, loot)
                extra = f" Itens recolhidos: {', '.join(itens)}" if itens else ""
                return ActionResult(True, "interacao",
                    f"✅ Sucesso no teste de {atributo_base} ({total} vs CD {obj.cd_teste}). {obj.nome} manipulado!{extra}", {})

            dano = obj.dano_falha if obj.dano_falha > 0 else 0
            if dano > 0: jogador.hp_atual = max(0, jogador.hp_atual - dano)
            if obj.tipo == "armadilha": obj.ativo = False

            msg = f"❌ Falha no teste ({total} vs CD {obj.cd_teste}). {obj.nome} resistiu. Dano sofrido: {dano}"
            if jogador.hp_atual <= 0:
                msg += self._nocauteado_para_vila(jogador, campanha)
            return ActionResult(False, "interacao", msg, {})

        return None

    @staticmethod
    def _bonus_proficiencia(jogador: JogadorWeb, atributo: str) -> int:
        pericias_bg = BACKGROUND_SKILLS.get(jogador.background, [])
        for pericia, attr in PERICIAS_DND_5E.items():
            if attr == atributo and pericia in pericias_bg:
                return jogador.proficiencia
        return 0

    # ------------------------------------------------------------------
    # TAVERNA (Ações específicas do lobby)
    # ------------------------------------------------------------------

    TAVERNA_ACOES = {
        "beber": "🍺 Serviste-te de uma cerveja gelada. Sentees o calor da taverna...",
        "comer": "🍖 Encheste o bucho com estufado de carne. +2 HP temporários!",
        "musica": "🎵 Melodia toca uma balada encantada. Todos na taverna sorriem.",
        "musica_triste": "🎵 Melodia canta uma canção melancólica sobre guerreiros perdidos...",
        "quadro": "📜 No quadro de missões há: 'Caverna dos Goblins' (recompensa: 100 PO). Fala com Garrick para aceitar.",
        "quadro_missoes": "📜 No quadro de missões há: 'Caverna dos Goblins' (recompensa: 100 PO). Fala com Garrick para aceitar.",
        "estrangeiro": "👤 O estranho de capuz sussurra: 'Cuidado com a floresta... as árvores lembram.'",
        "estrada_velha": "🗺️ Garrick diz: 'A Estrada Velha leva à Cidadela. Dizem que há monstros por lá.'",
        "cidadela": "🗺️ Garrick diz: 'A Cidadela é perigosa. Leva tochas e pocoes.'",
    }

    def _resolver_taverna(
        self, jogador: JogadorWeb, campanha: CampanhaWeb,
        cena: Optional[Cena], texto: str,
    ) -> Optional[ActionResult]:
        """Ações especiais da taverna (lobby)."""
        texto_low = texto.lower()

        # Beber cerveja / comer
        # Ordenar por comprimento decrescente para match mais longo primeiro
        # (evita que "musica" dispare em vez de "musica_triste")
        for chave in sorted(self.TAVERNA_ACOES, key=len, reverse=True):
            if chave in texto_low:
                narrativa = self.TAVERNA_ACOES[chave]
                if chave == "comer":
                    jogador.hp_atual = min(jogador.hp_maximo, jogador.hp_atual + 2)
                if chave in ("musica", "musica_triste"):
                    # Narrar_taverna é async; o chat de taverna é tratado pelo
                    # endpoint /api/taverna_chat. Aqui usamos a narrativa estática.
                    pass
                return ActionResult(True, "interacao", narrativa, {})

        # Quadro de missões
        if "missao" in texto_low or "quadro" in texto_low or "tarefa" in texto_low:
            missoes_abertas = self.db.execute(select(Missao).filter(
                Missao.jogador_telefone == jogador.telefone,
                Missao.concluida == False,
            )).scalars().all()
            if missoes_abertas:
                lista = "\n".join(f"  • {m.titulo} ({m.progresso}/{m.objetivo_quantidade})" for m in missoes_abertas)
                return ActionResult(True, "interacao",
                    f"📋 Tuas missões ativas:\n{lista}", {})
            return ActionResult(True, "interacao",
                "📋 Não tens missões pendentes. Fala com Garrick para novas aventuras!", {})

        # Descanso longo na taverna (recupera tudo)
        if any(p in texto_low for p in ("dormir", "descansar", "cama", "quarto", "noite")):
            jogador.hp_atual = jogador.hp_maximo
            jogador.slots_magia = jogador.slots_magia_max
            jogador.hit_dice_atual = getattr(jogador, "hit_dice_max", 1)
            set_status_efeitos(jogador, [])
            return ActionResult(True, "descanso",
                "🛌 Passaste a noite na taverna. HP, magia e dados de vida restaurados!", {})

        return None

    # ------------------------------------------------------------------
    # DESCANSO
    # ------------------------------------------------------------------

    def _resolver_descanso(
        self, jogador: JogadorWeb, campanha: CampanhaWeb,
        cena: Optional[Cena], texto: str,
    ) -> ActionResult:
        if campanha.cena_atual == SALA_INICIO:
            jogador.hp_atual = jogador.hp_maximo
            jogador.slots_magia = jogador.slots_magia_max
            jogador.hit_dice_atual = getattr(jogador, "hit_dice_max", 1)
            set_status_efeitos(jogador, [])
            return ActionResult(True, "descanso",
                "🛌 Descanso Longo na Vila. HP e Magia restaurados!", {})

        if jogador.hit_dice_atual > 0:
            jogador.hit_dice_atual -= 1
            cura = max(1, (jogador.hp_maximo // 4) + jogador.mod_con)
            jogador.hp_atual = min(jogador.hp_maximo, jogador.hp_atual + cura)
            return ActionResult(True, "descanso",
                f"🏕️ Descanso Curto. Curaste {cura} HP. "
                f"Hit Dice: {jogador.hit_dice_atual}/{jogador.hit_dice_max}", {})

        # Sem hit dice → descanso de emergência (previne softlock)
        cura_emergencia = max(1, jogador.hp_maximo // 8)
        jogador.hp_atual = min(jogador.hp_maximo, jogador.hp_atual + cura_emergencia)
        return ActionResult(True, "descanso",
            f"😴 Descanso Exausto. Sem Hit Dice, mas recuperaste {cura_emergencia} HP por força de vontade.\n"
            f"💡 Volta à Vila para repor Hit Dice (Descanso Longo).", {})

    # ------------------------------------------------------------------
    # TESTES DE PERÍCIA / ATRIBUTO
    # ------------------------------------------------------------------

    def _resolver_teste(self, jogador: JogadorWeb, cena: Optional[Cena], texto: str) -> ActionResult:
        atr = decidir_atributo_teste(texto)

        pericia_encontrada = next(
            (p for p in PERICIAS_DND_5E if p.lower() in texto.lower()), None
        )
        if pericia_encontrada:
            atr = PERICIAS_DND_5E[pericia_encontrada]

        mod_base = getattr(jogador, f"mod_{atr.lower()}", 0)
        bonus_prof = (jogador.proficiencia
            if pericia_encontrada and pericia_encontrada in BACKGROUND_SKILLS.get(jogador.background, [])
            else 0)
        total = random.randint(1, 20) + mod_base + bonus_prof
        msg = f"🎲 <b>Teste de {atr}</b> ({pericia_encontrada or 'Geral'}): <b>{total}</b>"
        if bonus_prof: msg += f" (+{bonus_prof} Proficiência)"
        return ActionResult(True, "outro", msg, {})


# =====================================================================
# FUNÇÕES AUXILIARES (usadas pelo resolver)
# =====================================================================

# TODO: migrar para versão async de ai_engine_web.py (decidir_atributo_teste async).
# Versão sync mantida porque pode ser chamada em contexto sincrono (ActionResolver é sync).
def decidir_atributo_teste(acao_jogador: str) -> str:
    """Define qual atributo de D&D (STR, DEX, etc) deve ser usado para uma ação de TESTE.

    ⚠️  FUNÇÃO BLOQUEANTE: faz chamada síncrona à OpenAI API.
    NUNCA chamar diretamente de um handler async — usar asyncio.to_thread()
    ou garantir que está dentro de um contexto síncrono (ex: ActionResolver
    já roda em to_thread no handler api_acao).
    """
    from mapa_engine import client_sync

    ATRIBUTOS_VALIDOS = {"STR", "DEX", "CON", "INT", "WIS", "CHA"}
    prompt = f"Dada a ação: '{acao_jogador}', qual atributo de D&D 5e é o mais apropriado?\nResponda apenas com a sigla: STR, DEX, CON, INT, WIS ou CHA."
    if not client_sync:
        return "STR"
    try:
        response = client_sync.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            timeout=10.0,
        )
        atr = response.choices[0].message.content.strip().upper()
        return atr if atr in ATRIBUTOS_VALIDOS else "STR"
    except Exception:
        return "STR"