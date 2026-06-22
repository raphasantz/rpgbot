import random
import math
import re
from dataclasses import dataclass, field
from typing import Optional, List, Any
from dnd_5e_rules import CONDICOES_DND_5E, aplicar_modificadores_dano, calcular_salvacao_morte
from game_helpers import set_status_efeitos, Status, KEYWORDS_POR_CLASSE, calcular_vulnerabilidade_fogo, parse_dice_string, rolar_dados


# Variantes ortográficas aceitas para "Caído" (com/sem acento).
# Derivado do sistema de variantes de game_helpers.Status.VARIANTES.
CAIDO_VARIANTES = Status.VARIANTES.get(Status.CAIDO, {Status.CAIDO, Status.CAIDO_ALT})


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

@dataclass
class ResultadoAtaqueObjeto:
    d20: int
    total_ataque: int
    acertou: bool
    critico: bool
    dano: int
    destruido: bool
    hp_restante: int
    quebrou_por_forca: bool
    detalhes_d20: list = field(default_factory=list)

@dataclass
class ResultadoAtaque:
    d20: int
    total_ataque: int
    acertou: bool
    critico: bool
    dano: int
    detalhes_d20: list = field(default_factory=list)

@dataclass
class TurnoCombateResult:
    acertou: bool = False
    critico: bool = False
    dano_causado: int = 0
    hp_alvo_restante: int = 0
    mortos_turno: int = 0
    revide_acertos: int = 0
    dano_recebido: int = 0
    total_ataque_jogador: int = 0
    detalhes_d20: list = field(default_factory=list)
    narrativa: str = ""
    estado_jogador: str = "ativo" # ativo, inconsciente, estabilizado, morto
    status_aplicados: list = field(default_factory=list)


def rolar_dado(lados):
    if lados < 1:
        return 1
    return random.randint(1, lados)

def calcular_vantagem_desvantagem(atacante_status: List[str], defensor_status: List[str], tipo_ataque: str = "melee"):
    vantagem = False
    desvantagem = False

    # Verifica condições do atacante via Dicionário de Regras
    for status in atacante_status:
        cond = CONDICOES_DND_5E.get(status, {}).get("efeitos", {})
        if cond.get("desvantagem_ataques") or cond.get("desvantagem_ataques_proprios"): desvantagem = True
        if cond.get("vantagem_ataques"): vantagem = True

    # Verifica condições do defensor via Dicionário de Regras
    for status in defensor_status:
        cond = CONDICOES_DND_5E.get(status, {}).get("efeitos", {})
        if cond.get("vantagem_ataques_contra"): vantagem = True
        if cond.get("desvantagem_ataques_contra"): desvantagem = True
        if status in CAIDO_VARIANTES:
            if tipo_ataque == "melee": vantagem = True
            elif tipo_ataque == "distancia": desvantagem = True

    # Regra D&D: Vantagem e Desvantagem se anulam
    if vantagem and desvantagem:
        return False, False
    return vantagem, desvantagem

def rolar_d20_combate(vantagem: bool, desvantagem: bool):
    roll1 = rolar_dado(20)
    roll2 = rolar_dado(20)
    if vantagem: return max(roll1, roll2), [roll1, roll2]
    elif desvantagem: return min(roll1, roll2), [roll1, roll2]
    return roll1, [roll1]

def determinar_tipo_dano_arma(arma_nome: str) -> str:
    if not arma_nome: return 'contundente'
    arma = arma_nome.lower()
    if any(x in arma for x in ['clava', 'maca', 'maça', 'martelo', 'bordão', 'cajado', 'desarmado', 'soco', 'artes marciais']): return 'contundente'
    elif any(x in arma for x in ['espada', 'machado', 'adaga', 'foice', 'glaive', 'halberd']): return 'cortante'
    elif any(x in arma for x in ['arco', 'besta', 'lança', 'dardo', 'zarabatana', 'tridente']): return 'perfurante'
    return 'contundente'

def calcular_dano_com_resistencias(dano_base: int, tipo_dano: str, resistencias: list, vulnerabilidades: list, imunidades: list) -> int:
    return aplicar_modificadores_dano(dano_base, tipo_dano, vulnerabilidades, resistencias, imunidades)

def processar_ataque_fisico(jogador, inimigo_ca: int, defensor_status: list = None, 
                            tipo_ataque: str = "melee", vantagem_extra: bool = False, 
                            desvantagem_extra: bool = False, 
                            inimigo_resistencias: list = None, 
                            inimigo_vulnerabilidades: list = None,
                            inimigo_imunidades: list = None) -> ResultadoAtaque:
    if defensor_status is None: defensor_status = []
    if inimigo_resistencias is None: inimigo_resistencias = []
    if inimigo_vulnerabilidades is None: inimigo_vulnerabilidades = []
    if inimigo_imunidades is None: inimigo_imunidades = []
        
    atacante_status = getattr(jogador, 'status_efeitos', []) or []
    vantagem, desvantagem = calcular_vantagem_desvantagem(atacante_status, defensor_status, tipo_ataque)
    
    if vantagem_extra: vantagem = True
    if desvantagem_extra: desvantagem = True
    if vantagem and desvantagem:
        vantagem = False
        desvantagem = False
        
    d20, detalhes_d20 = rolar_d20_combate(vantagem, desvantagem)
    modificador = getattr(jogador, 'modificador_ataque', 0)
    total_ataque = d20 + modificador

    acertou = d20 == 20 or (d20 != 1 and total_ataque >= inimigo_ca)
    critico = d20 == 20
    dano = 0

    if acertou:
        dano_dado = getattr(jogador, 'dano_dado', '1d6')
        try:
            qtd_dados, faces_dano, _mod_dice = parse_dice_string(dano_dado)
        except Exception:
            qtd_dados, faces_dano = 1, 6

        mod_dano = getattr(jogador, 'mod_dano', 0)
        rolagem_dano = sum(rolar_dado(faces_dano) for _ in range(qtd_dados))
        if critico: rolagem_dano += sum(rolar_dado(faces_dano) for _ in range(qtd_dados))
            
        dano_bruto = rolagem_dano + mod_dano
        arma_equipada = getattr(jogador, 'arma_equipada', '') or 'Desarmado'
        tipo_dano = determinar_tipo_dano_arma(arma_equipada)
        
        dano = calcular_dano_com_resistencias(dano_bruto, tipo_dano, inimigo_resistencias, inimigo_vulnerabilidades, inimigo_imunidades)

    return ResultadoAtaque(d20=d20, total_ataque=total_ataque, acertou=acertou, critico=critico, dano=dano, detalhes_d20=detalhes_d20)

def resolver_turno_combate(
    jogador, inimigo_ca: int, inimigo_ataque_str: str, inimigo_nome: str,
    hp_alvo_atual: int, hp_max_inimigo: int, qtd_ataques_inimigo: int,
    texto_acao: str = "", estilo: str = None, is_durnn_furia: bool = False,
    inimigo_resistencias: list = None, inimigo_vulnerabilidades: list = None,
    inimigo_imunidades: list = None, inimigo_primeiro: bool = False,
    inimigo_dano_str: str = "1d4"
) -> TurnoCombateResult:
    # Guard contra divisão por zero (hp_max_inimigo pode ser 0/None)
    hp_max_inimigo = max(1, hp_max_inimigo or 1)
    res = TurnoCombateResult()
    efeitos_atuais = list(getattr(jogador, 'status_efeitos', []) or [])
    res.hp_alvo_restante = hp_alvo_atual
    narrativa = ""

    # 1. PROCESSAR DEATH SAVES (Salvamentos de Morte)
    if Status.INCONSCIENTE in efeitos_atuais or jogador.hp_atual <= 0:
        if Status.INCONSCIENTE not in efeitos_atuais:
            efeitos_atuais.append(Status.INCONSCIENTE)
            jogador.hp_atual = 0

        sucessos = efeitos_atuais.count("DeathSave_Sucesso")
        falhas = efeitos_atuais.count("DeathSave_Falha")
        rolagem = random.randint(1, 20)
        
        ds_res = calcular_salvacao_morte(rolagem, sucessos, falhas)
        narrativa += f"🩸 <b>Salvamento contra a Morte:</b> Rolaste {rolagem}.\n"
        
        if ds_res["estabilizou"]:
            narrativa += "✨ <b>Estabilizaste!</b> Não estás mais a morrer, mas continuas Inconsciente.\n"
            efeitos_atuais = [e for e in efeitos_atuais if e not in ["DeathSave_Sucesso", "DeathSave_Falha"]]
            res.estado_jogador = "estabilizado"
            if ds_res.get("hp_recuperado"):
                jogador.hp_atual = ds_res["hp_recuperado"]
                efeitos_atuais.remove(Status.INCONSCIENTE)
                res.estado_jogador = "ativo"
                narrativa += "🌟 Crítico! Recuperaste 1 HP e acordaste!\n"
        elif ds_res["morreu"]:
            narrativa += "💀 <b>Falhaste no 3º salvamento. A tua lenda termina aqui...</b>\n"
            res.estado_jogador = "morto"
        else:
            if ds_res["sucesso"]:
                efeitos_atuais.append("DeathSave_Sucesso")
                narrativa += f"✅ Sucesso ({ds_res['novos_sucessos']}/3)\n"
            else:
                novas_falhas_delta = ds_res['novas_falhas'] - falhas
                for _ in range(novas_falhas_delta):
                    efeitos_atuais.append("DeathSave_Falha")
                narrativa += f"❌ Falha ({ds_res['novas_falhas']}/3)\n"
            res.estado_jogador = "inconsciente"
        
        set_status_efeitos(jogador, efeitos_atuais)
        res.narrativa = narrativa
        return res

    def logica_ataque_jogador(is_surto=False):
        nonlocal narrativa, efeitos_atuais
        vantagem = estilo in ["furtivo", "temerario"] or "Ajudado" in efeitos_atuais
        desvantagem = False
        if "Ajudado" in efeitos_atuais: efeitos_atuais.remove("Ajudado")

        dano_extra = 0
        texto_low = texto_acao.lower()
        _cls_kw = (getattr(jogador, 'classe', '') or '').lower()
        _nivel = getattr(jogador, 'nivel', 1) or 1
        keyword_feature_msg = ""
        
        if not is_surto:
            # KEYWORDS_POR_CLASSE importado de game_helpers (versão canônica completa)
            for kw, ef in KEYWORDS_POR_CLASSE.get(_cls_kw, {}).items():
                if kw in texto_low:
                    if kw == "fúria" and Status.FURIA not in efeitos_atuais: efeitos_atuais.append(Status.FURIA)
                    if ef.get("bonus_dano"): dano_extra += ef["bonus_dano"]
                    keyword_feature_msg = f"\n⚡ <i>{kw.title()} ativado!</i>"
                    break

        ataque_res = processar_ataque_fisico(
            jogador=jogador, inimigo_ca=inimigo_ca, defensor_status=[], tipo_ataque="melee",
            vantagem_extra=vantagem, desvantagem_extra=desvantagem,
            inimigo_resistencias=inimigo_resistencias, inimigo_vulnerabilidades=inimigo_vulnerabilidades, inimigo_imunidades=inimigo_imunidades
        )
        
        if not is_surto:
            res.acertou = ataque_res.acertou
            res.critico = ataque_res.critico
            res.total_ataque_jogador = ataque_res.total_ataque
            res.detalhes_d20 = ataque_res.detalhes_d20

        if ataque_res.acertou:
            dano_habilidade = 0
            if Status.SMITE in efeitos_atuais:
                dano_habilidade += sum(random.randint(1, 8) for _ in range(min(5, 2 + (_nivel // 4))))
                if not is_surto: efeitos_atuais.remove(Status.SMITE)
            if Status.FORMA_SELVAGEM in efeitos_atuais:
                dano_habilidade += sum(random.randint(1, 6) for _ in range(2))
                if not is_surto: efeitos_atuais.remove(Status.FORMA_SELVAGEM)
            if Status.FURIA in efeitos_atuais:
                dano_habilidade += 4 if _nivel >= 16 else (3 if _nivel >= 9 else 2)

            dano_final = ataque_res.dano + dano_habilidade + dano_extra
            if estilo == "furtivo" and _cls_kw == "ladino" and not is_surto:
                filename_sneak = math.ceil(_nivel / 2)
                dano_final += sum(random.randint(1, 6) for _ in range(filename_sneak))

            # Vulnerabilidade da Árvore Gulthias ao fogo (fallback textual)
            # Só aplicar se NÃO foi já coberta por calcular_dano_com_resistencias
            ja_coberto = inimigo_vulnerabilidades and "fogo" in inimigo_vulnerabilidades
            if not ja_coberto and calcular_vulnerabilidade_fogo(inimigo_nome, texto_low):
                dano_final *= 2
                if not is_surto: narrativa += "🔥 VULNERÁVEL! O fogo causa o dobro do dano!\n"
            
            res.dano_causado += dano_final
            vivos_antes = math.ceil(res.hp_alvo_restante / hp_max_inimigo) if res.hp_alvo_restante > 0 else 0
            res.hp_alvo_restante -= dano_final
            vivos_depois = math.ceil(res.hp_alvo_restante / hp_max_inimigo) if res.hp_alvo_restante > 0 else 0
            mortos = vivos_antes - vivos_depois
            res.mortos_turno += mortos

            crit_text = "💥 CRÍTICO! Dano: " if ataque_res.critico else "💥 Dano: "
            prefix = "⚔️ Surto de Ação: " if is_surto else "🎲 Dados: "
            narrativa += f"{prefix}d20={ataque_res.detalhes_d20} -> {ataque_res.total_ataque} vs CA {inimigo_ca} ✅\n"
            narrativa += f"{crit_text}{dano_final}"
            if mortos > 0: narrativa += f" (💀 {mortos} eliminado{'s' if mortos > 1 else ''}!)"
            narrativa += f"{keyword_feature_msg}\n"
        else:
            prefix = "⚔️ Surto de Ação: " if is_surto else "🎲 Dados: "
            narrativa += f"{prefix}d20={ataque_res.detalhes_d20} -> {ataque_res.total_ataque} vs CA {inimigo_ca} ❌\n💨 Ataque falhou\n"

    # CRIT-04 FIX: Cobertura (+2 CA) — aplicada globalmente para inimigos atacarem
    mod_ca_base = getattr(jogador, 'modificador_defesa', 10) or 10
    if Status.COBERTURA in efeitos_atuais:
        mod_ca_base += 2

    def logica_revide_inimigo():
        nonlocal narrativa, efeitos_atuais
        if res.hp_alvo_restante > 0 and qtd_ataques_inimigo > 0:
            narrativa += f"\n⚠️ ATAQUE INIMIGO: {qtd_ataques_inimigo}x {inimigo_nome} ataca(m)!\n"
            mod_inimigo = _parse_mod_ataque(inimigo_ataque_str)
            dano_final_revide = 0

            # ESQUIVANDO (Dodge): desvantagem nos ataques inimigos (D&D 5e)
            tem_desvantagem = Status.ESQUIVANDO in efeitos_atuais

            for i in range(qtd_ataques_inimigo):
                # Vantagem vs Desvantagem cancelam-se → rolagem normal (D&D 5e)
                if is_durnn_furia and tem_desvantagem:
                    d20_inimigo = random.randint(1, 20)
                elif is_durnn_furia:
                    d20_inimigo = max(random.randint(1, 20), random.randint(1, 20))
                elif tem_desvantagem:
                    d20_inimigo = min(random.randint(1, 20), random.randint(1, 20))
                else:
                    d20_inimigo = random.randint(1, 20)
                
                if d20_inimigo + mod_inimigo >= mod_ca_base or d20_inimigo == 20:
                    res.revide_acertos += 1
                    # Usar dano do bestiário em vez de 1d4 hardcoded
                    try:
                        qtd_d, faces_d, mod_d = parse_dice_string(inimigo_dano_str)
                        dano_base, _ = rolar_dados(qtd_d, faces_d, mod_d)
                    except Exception:
                        dano_base = random.randint(1, 4)  # fallback seguro
                    if is_durnn_furia: dano_base += 2
                    if d20_inimigo == 20:
                        # BUG #4 FIX: Crit dobra os DADOS (não o modifier) — D&D 5e
                        dano_crit_extra, _ = rolar_dados(qtd_d, faces_d, 0)
                        dano_base += dano_crit_extra
                    dano_final_revide += dano_base
                    narrativa += f"🗡️ Atk {i+1}: Hit ({dano_base} dano)\n"
                else:
                    narrativa += f"💨 Atk {i+1}: Miss\n"

            if res.revide_acertos > 0:
                if Status.FURIA in efeitos_atuais and CONDICOES_DND_5E.get("Fúria", {}).get("efeitos", {}).get("resistencia_contundente"):
                    dano_final_revide = max(1, dano_final_revide // 2)
                    narrativa += f"🛡️ Fúria reduziu o dano!\n"
                    
                res.dano_recebido = dano_final_revide
                jogador.hp_atual = max(0, jogador.hp_atual - dano_final_revide)
                narrativa += f"🩸 Dano total recebido: {dano_final_revide}\n"
                
                if jogador.hp_atual <= 0:
                    efeitos_atuais.append(Status.INCONSCIENTE)
                    res.status_aplicados.append(Status.INCONSCIENTE)
                    narrativa += "\n💀 Caíste inconsciente (0 HP)!"
                    res.estado_jogador = "inconsciente"

                if random.randint(1, 100) <= 20 and Status.ENVENENADO not in efeitos_atuais and jogador.hp_atual > 0:
                    if any(n in inimigo_nome.lower() for n in ["rato", "aranha", "cobra"]):
                        efeitos_atuais.append(Status.ENVENENADO)
                        res.status_aplicados.append(Status.ENVENENADO)
                        narrativa += "🤢 Foste Envenenado!\n"

    if inimigo_primeiro:
        logica_revide_inimigo()
        if jogador.hp_atual > 0 and Status.INCONSCIENTE not in efeitos_atuais: 
            logica_ataque_jogador()
            # BUG #10 FIX: Surto de Ação só para guerreiros
            if Status.SURTO in efeitos_atuais and res.hp_alvo_restante > 0 and _cls_kw == "guerreiro":
                efeitos_atuais.remove(Status.SURTO)
                logica_ataque_jogador(is_surto=True)
    else:
        logica_ataque_jogador()
        # BUG #10 FIX: Surto de Ação só para guerreiros
        if Status.SURTO in efeitos_atuais and res.hp_alvo_restante > 0 and _cls_kw == "guerreiro":
            efeitos_atuais.remove(Status.SURTO)
            logica_ataque_jogador(is_surto=True)
        if res.hp_alvo_restante > 0: 
            logica_revide_inimigo()

    if Status.ENVENENADO in efeitos_atuais and jogador.hp_atual > 0:
        dano_veneno = random.randint(1, 4)
        jogador.hp_atual = max(0, jogador.hp_atual - dano_veneno)
        narrativa += f"\n🤢 Veneno: Sofres {dano_veneno} de dano direto!"
        if jogador.hp_atual <= 0:
            efeitos_atuais.append(Status.INCONSCIENTE)
            res.status_aplicados.append(Status.INCONSCIENTE)
            res.estado_jogador = "inconsciente"
            narrativa += "\n💀 Sucumbiste ao veneno (0 HP)!"

    if Status.ESQUIVANDO in efeitos_atuais:
        efeitos_atuais.remove(Status.ESQUIVANDO)
        narrativa += "\n🛡️ Esquiva terminou — prepara-te para o próximo turno."
    set_status_efeitos(jogador, efeitos_atuais)
    res.narrativa = narrativa.strip()
    return res

def processar_ataque_objeto(jogador, objeto) -> ResultadoAtaqueObjeto:
    atacante_status = getattr(jogador, 'status_efeitos', []) or []
    
    if getattr(objeto, 'break_threshold', 0) > 0:
        vantagem, desvantagem = calcular_vantagem_desvantagem(atacante_status, [], "melee")
        d20_val, detalhes_str = rolar_d20_combate(vantagem, desvantagem)
        forca_total = d20_val + getattr(jogador, 'mod_str', 0)
        
        if forca_total >= objeto.break_threshold:
            return ResultadoAtaqueObjeto(d20=d20_val, total_ataque=forca_total, acertou=True, critico=False, dano=objeto.hp_atual, destruido=True, hp_restante=0, quebrou_por_forca=True, detalhes_d20=detalhes_str)

    vantagem, desvantagem = calcular_vantagem_desvantagem(atacante_status, [], "melee")
    d20, detalhes_d20 = rolar_d20_combate(vantagem, desvantagem)
    total_ataque = d20 + getattr(jogador, 'modificador_ataque', 0)

    acertou = d20 == 20 or (d20 != 1 and total_ataque >= getattr(objeto, 'ca', 10))
    critico = d20 == 20
    dano = 0
    novo_hp = objeto.hp_atual

    if acertou:
        dano_dado = getattr(jogador, 'dano_dado', '1d6')
        try:
            qtd_d, faces_d, mod_d = parse_dice_string(dano_dado)
        except Exception:
            qtd_d, faces_d, mod_d = 1, 6, 0

        rolagem_dano, _ = rolar_dados(qtd_d, faces_d, 0)
        if critico: rolagem_dano += sum(rolar_dado(faces_d) for _ in range(qtd_d))
            
        dano = rolagem_dano + getattr(jogador, 'mod_dano', 0)
        arma = getattr(jogador, 'arma_equipada', '') or 'Desarmado'
        dano = calcular_dano_com_resistencias(dano, determinar_tipo_dano_arma(arma), getattr(objeto, 'resistencias', []), getattr(objeto, 'vulnerabilidades', []), [])
        novo_hp = max(0, objeto.hp_atual - dano)

    return ResultadoAtaqueObjeto(d20=d20, total_ataque=total_ataque, acertou=acertou, critico=critico, dano=dano, destruido=(novo_hp <= 0), hp_restante=novo_hp, quebrou_por_forca=False, detalhes_d20=detalhes_d20)