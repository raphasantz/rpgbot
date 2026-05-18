import random
import math
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models import Jogador, Campanha, Cena, Encontro, Inimigo, ObjetoDestrutivel, Npc, Interativo, Missao
from combat_logic import processar_ataque_fisico, processar_ataque_objeto
from ui_utils import MAGIAS_POR_CLASSE, XP_POR_NIVEL, HP_POR_CLASSE, gerar_loot_inimigo_comum, adicionar_ao_inventario, obter_inventario_limpo, BACKGROUND_SKILLS, gerar_loot_bau

@dataclass
class ActionResult:
    sucesso: bool
    tipo_acao: str  # "combate", "magia", "manobra", "navegacao", "interacao", "descanso", "outro", "status"
    narrativa_mecanica: str
    dados_extras: Dict[str, Any] = field(default_factory=dict)

class ActionResolver:
    """
    O Cérebro Determinístico do RedNerds.
    Roteia o JSON da IA, aplica regras de status e invoca o motor de dados.
    """
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def resolver_acao(self, jogador: Jogador, campanha: Campanha, cena_atual: Cena, json_ia: Dict[str, Any], texto_jogador: str) -> ActionResult:
        """
        Pipeline principal de resolução de turnos.
        """
        status_jogador = getattr(jogador, 'status_efeitos', [])

        # --- 1. FILTRO DE STATUS RESTRITIVOS GLOBAIS ---
        if "Atordoado" in status_jogador:
            return ActionResult(False, "status", "💫 Estás atordoado! Perdes o teu turno e não consegues agir.", {})
            
        intencao = json_ia.get("intencao", "OUTRO").upper()
        estilo = json_ia.get("estilo")
        alvo = json_ia.get("alvo")
        manobra = json_ia.get("manobra")
        direcao = json_ia.get("direcao")
        magia = json_ia.get("magia_usada")
        item = json_ia.get("item")

        # --- 2. ROTEAMENTO DE INTENÇÃO ---
        if intencao == "COMBATE":
            return await self._resolver_combate(jogador, campanha, cena_atual, alvo, estilo, texto_jogador)
            
        elif intencao == "MAGIA":
            return await self._resolver_magia(jogador, campanha, cena_atual, magia, alvo, texto_jogador)
            
        elif intencao == "MANOBRA":
            return await self._resolver_manobra(jogador, campanha, cena_atual, manobra, alvo, texto_jogador)
            
        elif intencao == "NAVEGAR":
            return await self._resolver_navegacao(jogador, campanha, cena_atual, direcao, texto_jogador)

        elif intencao == "INTERACAO":
            return await self._resolver_interacao(jogador, campanha, cena_atual, alvo, item, texto_jogador)

        elif intencao == "DESCANSAR":
            return await self._resolver_descanso(jogador, campanha, cena_atual, texto_jogador)

        # --- 3. INTERCEPTAÇÃO DE AÇÕES TÁTICAS E TESTES ---
        texto_low = texto_jogador.lower()
        
        # Ações Táticas Reimplantadas
        if any(p in texto_low for p in ["esquivar", "defender", "dodge", "defesa total"]):
            efeitos = list(getattr(jogador, 'status_efeitos', []))
            if "Esquivando" not in efeitos:
                efeitos.append("Esquivando")
                jogador.status_efeitos = efeitos
                return ActionResult(True, "status", "🛡️ <b>Posição Defensiva!</b> Inimigos terão desvantagem para te acertar até teu próximo turno.", {})
            return ActionResult(False, "status", "⚠️ Já estás em posição defensiva.", {})

        if intencao == "COBERTURA" or any(p in texto_low for p in ["cobertura", "esconder", "proteger"]):
            efeitos = list(getattr(jogador, 'status_efeitos', []))
            if "Cobertura" not in efeitos:
                efeitos.append("Cobertura")
                jogador.status_efeitos = efeitos
                return ActionResult(True, "status", "🧱 <b>Cobertura!</b> Protegeste-te. Ganhaste +2 de CA contra os próximos ataques.", {})
            return ActionResult(False, "status", "⚠️ Já estás protegido em cobertura.", {})

        if intencao == "AJUDAR" or any(p in texto_low for p in ["ajudar", "ajudo", "suportar"]):
            efeitos = list(getattr(jogador, 'status_efeitos', []))
            if "Ajudado" not in efeitos:
                efeitos.append("Ajudado")
                jogador.status_efeitos = efeitos
                return ActionResult(True, "status", "🤝 Posicionaste-te para dar suporte! O próximo ataque do grupo terá Vantagem.", {})

        # Testes Manuais
        if intencao in ["INTERACAO", "OUTRO", "TESTE"] and any(palavra in texto_low for palavra in ["teste", "rolar", "perceção", "percepção", "história", "arcanismo", "escutar"]):
            return await self._resolver_teste(jogador, cena_atual, texto_jogador)

        # Fallback narrativo
        return ActionResult(True, "outro", "Ação resolvida pelo ambiente ou narrativa.", {"intencao": intencao})

    # =================================================================
    # SUBMÉTODOS DE RESOLUÇÃO (CONEXÕES COM COMBAT_LOGIC E DB)
    # =================================================================

    async def _resolver_combate(self, jogador: Jogador, campanha: Campanha, cena: Cena, alvo_nome: Optional[str], estilo: Optional[str], texto: str) -> ActionResult:
        estado = dict(campanha.estado_salas or {})
        
        # 1. Encontrar Inimigo
        encontros = (await self.db.execute(select(Encontro).filter(Encontro.cod_sala == cena.cod_sala))).scalars().all()
        encontros_vivos = [e for e in encontros if not estado.get(f"derrotado_{e.id}")]
        if not encontros_vivos:
            return await self._resolver_ataque_objeto(jogador, cena, alvo_nome, texto)

        campanha.em_combate = True

        encontro = encontros_vivos[0]
        inimigo = (await self.db.execute(select(Inimigo).filter(Inimigo.nome == encontro.nome_inimigo))).scalars().first()
        if not inimigo:
            return ActionResult(False, "combate", f"O monstro {encontro.nome_inimigo} não tem ficha no bestiário!", {})

        chave_hp = f"hp_{encontro.id}"
        hp_max_inimigo = inimigo.hp_max if inimigo.hp_max is not None else 10
        hp_grupo = estado.get(chave_hp, hp_max_inimigo * encontro.quantidade)
        ca_alvo = inimigo.ca
        
        is_durnn_furia = False
        if getattr(inimigo, 'is_boss', False) and hp_grupo <= (hp_max_inimigo / 2) and hp_grupo > 0:
            is_durnn_furia = True
            ca_alvo = max(10, ca_alvo - 2)

        # Salva CA no estado para o Ataque Secundário do botão
        estado["ca_alvo"] = ca_alvo
        campanha.estado_salas = estado

        atacante_status = list(getattr(jogador, 'status_efeitos', []))
        efeitos_atuais = atacante_status
        vantagem = False
        desvantagem = False
        str_vantagem = ""

        if estilo == "furtivo" or estilo == "temerario":
            vantagem = True
            str_vantagem = "(Vantagem)"
        if "Caido" in atacante_status or "Caído" in atacante_status:
            desvantagem = True
            str_vantagem = "(Desvantagem)"
        if "Ajudado" in atacante_status:
            vantagem = True
            str_vantagem = "(Vantagem)"
            if "Ajudado" in atacante_status: atacante_status.remove("Ajudado")
            jogador.status_efeitos = atacante_status

        # --- INICIATIVA ---
        ini_jogador = random.randint(1, 20) + jogador.mod_dex
        ini_inimigo = random.randint(1, 20) + getattr(inimigo, 'mod_destreza', 0)
        narrativa = f"⚡ INICIATIVA: {jogador.nome} {ini_jogador} vs {inimigo.nome} {ini_inimigo}\n\n"
        
        inimigo_primeiro = ini_inimigo >= ini_jogador
        jogador_pode_atacar = True
        dano_causado = 0
        acertou_ataque = False
        
        # Se o inimigo venceu a iniciativa, ele ataca primeiro
        if inimigo_primeiro:
            texto_revide, dano_revide, efeitos_atuais = await self._resolver_revide_inimigo(jogador, campanha, encontro, inimigo, hp_grupo, hp_max_inimigo, efeitos_atuais, is_durnn_furia)
            narrativa += texto_revide
            if jogador.hp_atual <= 0:
                jogador_pode_atacar = False
        
        # Turno do Jogador (se não morreu no revide)
        if jogador_pode_atacar:
            # FIX 1: Passar a vantagem/desvantagem forçada pelo estilo temerário para a engine de combate
            resultado_ataque = processar_ataque_fisico(jogador=jogador, inimigo_ca=ca_alvo, defensor_status=[], tipo_ataque="melee", vantagem_extra=vantagem, desvantagem_extra=desvantagem)
            dano_extra = 0
            
            # --- REIMPLANTAÇÃO: PALAVRAS-CHAVE DE CLASSE ---
            _cls_kw = jogador.classe.lower()
            texto_low_kw = texto.lower()
            mod_keyword = {}
            keyword_feature_msg = ""
            KEYWORDS_POR_CLASSE = {
                "bárbaro": {"fúria": {}},
                "artífice": {"explosão arcana": {"bonus_dano": 4}, "infusão": {"bonus_ca": 2}},
                "guerreiro": {"estocar": {"bonus_ataque": 2}, "defesa total": {"bonus_ca": 4}},
                "paladino": {"aura": {"bonus_ca": 3}, "abjurar": {"bonus_ca": 5}},
                "monge": {"flurry": {"ataque_extra": True}, "torrente": {"ataque_extra": True}, "ki": {"bonus_ataque": 2}},
                "patrulheiro": {"marca": {"bonus_dano": 6}, "marca do caçador": {"bonus_dano": 6}},
                "bardo": {"zombaria": {"desvantagem_inimigo": True}},
            }
            kws_classe = KEYWORDS_POR_CLASSE.get(_cls_kw, {})
            for kw_texto, kw_efeitos in kws_classe.items():
                if kw_texto in texto_low_kw:
                    mod_keyword = kw_efeitos
                    # FIX 2: Adicionar "Fúria" aos status se o jogador usou a palavra-chave
                    if kw_texto == "fúria" and "Fúria" not in efeitos_atuais:
                        efeitos_atuais.append("Fúria")
                        jogador.status_efeitos = efeitos_atuais
                        
                    if kw_efeitos.get("bonus_dano"): dano_extra += kw_efeitos["bonus_dano"]
                    if kw_efeitos.get("bonus_ataque"): jogador.modificador_ataque += kw_efeitos["bonus_ataque"]
                    if kw_efeitos.get("bonus_ca"): jogador.modificador_defesa += kw_efeitos["bonus_ca"]
                    if kw_efeitos.get("desvantagem_inimigo"):
                        estado_kw = dict(campanha.estado_salas or {})
                        estado_kw["inimigo_debilidade"] = True
                        campanha.estado_salas = estado_kw
                    keyword_feature_msg = f"\n⚡ <i>{kw_texto.title()} ativado!</i>"
                    break
            # ------------------------------------------------
            
            # Formatação segura dos dados
            detalhes = resultado_ataque.detalhes_d20
            mod_calc = "?"
            try:
                if isinstance(detalhes, list):
                    dados_str = f"[{', '.join(map(str, detalhes))}]"
                    max_roll = max(detalhes) if vantagem else min(detalhes)
                elif isinstance(detalhes, int):
                    dados_str = f"[{detalhes}]"
                    max_roll = detalhes
                else:
                    dados_str = f"[{detalhes}]"
                    max_roll = int(str(detalhes).split(',')[-1].strip().replace('[','').replace(']',''))
                
                if isinstance(max_roll, int):
                    mod_calc = resultado_ataque.total_ataque - max_roll
            except Exception:
                dados_str = f"[{detalhes}]"

            mod_str = f"+{mod_calc}" if isinstance(mod_calc, int) and mod_calc >= 0 else str(mod_calc)
            str_vant = f" {str_vantagem}" if str_vantagem else ""

            if resultado_ataque.acertou:
                dano_causado = resultado_ataque.dano
                acertou_ataque = True
                
                # --- CONSUMO DE HABILIDADES (SMITE, FÚRIA, FORMA SELVAGEM) ---
                efeitos_jogador = list(getattr(jogador, 'status_efeitos', []))
                dano_habilidade = 0
                
                if "Smite" in efeitos_jogador:
                    dados_smite = min(5, 2 + (jogador.nivel // 4))
                    dano_habilidade += sum(random.randint(1, 8) for _ in range(dados_smite))
                    efeitos_jogador.remove("Smite")
                    
                if "Forma Selvagem" in efeitos_jogador:
                    dano_habilidade += sum(random.randint(1, 6) for _ in range(2))
                    efeitos_jogador.remove("Forma Selvagem")
                    
                texto_furia = ""
                if "Fúria" in efeitos_jogador:
                    bonus_furia = 2
                    if jogador.nivel >= 16: bonus_furia = 4
                    elif jogador.nivel >= 9: bonus_furia = 3
                    dano_habilidade += bonus_furia
                    # Fúria NÃO é removida aqui, só no fim do combate ou ao mover
                    texto_furia = f"\n😡 <b>Fúria Bárbaro:</b> +{bonus_furia} de dano e Resistência Ativada!"

                dano_causado += dano_habilidade + dano_extra
                jogador.status_efeitos = efeitos_jogador # Salva a limpeza dos status

                # Lógica de Furtivo
                if estilo == "furtivo" and jogador.classe.lower() == "ladino":
                    dados_furtivo = math.ceil(jogador.nivel / 2)
                    dano_extra_furtivo = sum(random.randint(1, 6) for _ in range(dados_furtivo))
                    dano_causado += dano_extra_furtivo
                else:
                    dano_extra_furtivo = 0

                # --- VULNERABILIDADE GULTHIAS (ÁRVORE) AO FOGO ---
                if alvo_nome and ("árvore" in alvo_nome.lower() or "arvore" in alvo_nome.lower() or "gulthias" in alvo_nome.lower()):
                    if any(p in texto.lower() for p in ["fogo", "ardente", "chamas", "bola"]):
                        dano_causado *= 2
                        narrativa += "🔥 VULNERÁVEL! O fogo causa o dobro do dano!\n"

                vivos_antes = math.ceil(hp_grupo / hp_max_inimigo) if hp_grupo > 0 else 0
                hp_grupo -= dano_causado
                vivos_depois = math.ceil(hp_grupo / hp_max_inimigo) if hp_grupo > 0 else 0
                mortos_turno = vivos_antes - vivos_depois

                texto_crit = "💥 CRÍTICO! Dano: " if resultado_ataque.critico else "💥 Dano: "
                texto_morte = f" (💀 {mortos_turno} eliminado{'s' if mortos_turno > 1 else ''}!)" if mortos_turno > 0 else ""

                narrativa += f"🎲 Dados: d20={dados_str}{str_vant}{mod_str}={resultado_ataque.total_ataque} vs CA {ca_alvo} ✅\n"
                narrativa += f"{texto_crit}{dano_causado}{texto_morte}\n"
                
                if dano_extra_furtivo > 0:
                    narrativa += f" (Inclui +{dano_extra_furtivo} Furtivo)\n"
                if dano_habilidade > 0:
                    narrativa += f" (+{dano_habilidade} de Habilidades)\n"
                if dano_extra > 0:
                    narrativa += f" (+{dano_extra} de Classe)\n"
                narrativa += f"{texto_furia}{keyword_feature_msg}\n"

                estado[chave_hp] = hp_grupo

                if hp_grupo <= 0:
                    estado[f"derrotado_{encontro.id}"] = True
                    campanha.em_combate = False
                    narrativa += f"\n🏆 VITÓRIA! O grupo recebe "
                    xp_total = getattr(inimigo, 'xp_recompensa', 50) * encontro.quantidade
                    ouro_total = getattr(inimigo, 'ouro_recompensa', 5) * encontro.quantidade
                    jogador.xp += xp_total
                    jogador.gold += ouro_total
                    narrativa += f"{xp_total} XP e {ouro_total} PO.\n"
                    
                    # --- GERAÇÃO DE LOOT REIMPLANTADA ---
                    loot_gerado = gerar_loot_inimigo_comum()
                    if loot_gerado:
                        itens_reais = adicionar_ao_inventario(jogador, loot_gerado)
                        if itens_reais:
                            narrativa += f"🎁 Saque: {', '.join(itens_reais)}\n"

                    # --- LEVEL UP COMPLETO REIMPLANTADO ---
                    if jogador.xp >= XP_POR_NIVEL.get(jogador.nivel + 1, 999999):
                        jogador.nivel += 1
                        jogador.hp_maximo += HP_POR_CLASSE.get(jogador.classe, 8) + jogador.mod_con
                        jogador.hp_atual = jogador.hp_maximo
                        
                        jogador.slots_magia_max += 1
                        jogador.slots_magia = jogador.slots_magia_max
                        jogador.hit_dice_max = getattr(jogador, 'hit_dice_max', 1) + 1
                        jogador.hit_dice_atual = jogador.hit_dice_max

                        nova_proficiencia = 2 + ((jogador.nivel - 1) // 4)
                        if nova_proficiencia > jogador.proficiencia:
                            jogador.proficiencia = nova_proficiencia
                            jogador.modificador_ataque = jogador.mod_dano + jogador.proficiencia
                            
                        if jogador.classe.lower() == "monge" and "Desarmado" in getattr(jogador, 'arma_equipada', ''):
                            if jogador.nivel >= 17: jogador.dano_dado = "1d10"
                            elif jogador.nivel >= 11: jogador.dano_dado = "1d8"
                            elif jogador.nivel >= 5: jogador.dano_dado = "1d6"
                            else: jogador.dano_dado = "1d4"
                            
                        narrativa += f"🌟 Subiste para o Nível {jogador.nivel}! HP, Magia e Hit Dice atualizados!\n"
                else:
                    if is_durnn_furia:
                        narrativa += "\n😡 O Boss entrou em Fúria Sanguinária!\n"
                        
                    # --- REIMPLANTAÇÃO: SURTO DE AÇÃO DO GUERREIRO ---
                    efeitos_jogador = list(getattr(jogador, 'status_efeitos', []))
                    if "Surto" in efeitos_jogador and hp_grupo > 0:
                        efeitos_jogador.remove("Surto")
                        jogador.status_efeitos = efeitos_jogador
                        
                        res_surto = processar_ataque_fisico(jogador=jogador, inimigo_ca=ca_alvo, defensor_status=[], tipo_ataque="melee")
                        dano_surto = res_surto.dano
                        
                        if res_surto.acertou:
                            vivos_antes_surto = math.ceil(hp_grupo / hp_max_inimigo) if hp_grupo > 0 else 0
                            hp_grupo -= dano_surto
                            vivos_depois_surto = math.ceil(hp_grupo / hp_max_inimigo) if hp_grupo > 0 else 0
                            mortos_surto = vivos_antes_surto - vivos_depois_surto

                            estado[chave_hp] = hp_grupo
                            texto_crit_surto = "💥 CRÍTICO! Dano: " if res_surto.critico else "💥 Dano: "
                            texto_morte_surto = f" (💀 {mortos_surto} eliminado{'s' if mortos_surto > 1 else ''}!)" if mortos_surto > 0 else ""
                            narrativa += f"\n⚔️ <b>Surto de Ação!</b> Ataque extra! ✅\n{texto_crit_surto}{dano_surto}{texto_morte_surto}\n"
                            
                            if hp_grupo <= 0:
                                estado[f"derrotado_{encontro.id}"] = True
                                campanha.em_combate = False
                                xp_total = getattr(inimigo, 'xp_recompensa', 50) * encontro.quantidade
                                ouro_total = getattr(inimigo, 'ouro_recompensa', 5) * encontro.quantidade
                                jogador.xp += xp_total
                                jogador.gold += ouro_total
                                narrativa += f"\n🏆 VITÓRIA pelo Surto! O grupo recebe {xp_total} XP e {ouro_total} PO.\n"
                        else:
                            narrativa += f"\n⚔️ <b>Surto de Ação!</b> Ataque extra falhou! ❌\n"
                    # ------------------------------------------------
            else:
                acertou_ataque = False
                narrativa += f"🎲 Dados: d20={dados_str}{str_vant}{mod_str}={resultado_ataque.total_ataque} vs CA {ca_alvo} ❌\n"
                narrativa += "💨 Ataque falhou\n"
                
            # Se o jogador atacou primeiro e o inimigo sobreviveu, o inimigo ataca agora
            if not inimigo_primeiro and campanha.em_combate and hp_grupo > 0 and jogador.hp_atual > 0:
                texto_revide, dano_revide, efeitos_atuais = await self._resolver_revide_inimigo(jogador, campanha, encontro, inimigo, hp_grupo, hp_max_inimigo, efeitos_atuais, is_durnn_furia)
                narrativa += "\n" + texto_revide

        # --- VENENO NO FIM DO TURNO ---
        if "Envenenado" in efeitos_atuais:
            dano_veneno = random.randint(1, 4)
            jogador.hp_atual = max(0, jogador.hp_atual - dano_veneno)
            narrativa += f"🤢 Veneno: Sofres {dano_veneno} de dano direto!\n"

        # Limpeza de status e estado
        if "Esquivando" in efeitos_atuais: efeitos_atuais.remove("Esquivando")
        jogador.status_efeitos = efeitos_atuais
        campanha.estado_salas = estado
        
        if jogador.hp_atual <= 0:
            narrativa += "\n💀 Caíste em combate! A Patrulha de Carvalhal resgatou-te, mas perdeste algum ouro..."
            jogador.hp_atual = jogador.hp_maximo
            jogador.gold = max(0, jogador.gold - 10)
            campanha.cena_atual = "carvalhal"
            jogador.cena_atual = "carvalhal"
            campanha.em_combate = False
            jogador.status_efeitos = [] # FIX 3: Limpar todos os status (incluindo Veneno e Fúria) ao morrer
            
        return ActionResult(True, "combate", narrativa.strip(), {"dano": dano_causado, "acertou": acertou_ataque})

    async def _resolver_revide_inimigo(self, jogador: Jogador, campanha: Campanha, encontro: Encontro, inimigo: Inimigo, hp_grupo: int, hp_max_inimigo: int, efeitos_atuais: list, is_durnn_furia: bool) -> tuple[str, int, list]:
        """Calcula e formata o revide do inimigo. Retorna (narrativa, dano_total, efeitos_atualizados)"""
        narrativa = ""
        dano_final_revide = 0
        
        if campanha.em_combate and hp_grupo > 0:
            vivos_agora = math.ceil(hp_grupo / hp_max_inimigo)
            mod_inimigo = int(str(inimigo.ataque).replace('+', '')) if '+' in str(inimigo.ataque) else 0
            
            result_vivos_count = await self.db.execute(select(func.count()).select_from(Jogador).filter(
                Jogador.party_id == campanha.party_id, Jogador.hp_atual > 0, Jogador.cena_atual == campanha.cena_atual
            ))
            jogadores_vivos = result_vivos_count.scalar()
            limite_ataques = jogadores_vivos + (getattr(encontro, 'multiplicador_ameaca', 1) or 1)
            atacantes = min(vivos_agora, limite_ataques)
            
            verbo_atacar = "ataca" if atacantes == 1 else "atacam"
            narrativa += f"⚠️ ATAQUE INIMIGO: {atacantes}x {inimigo.nome} {verbo_atacar}! (De {vivos_agora} vivos)\n"
            acertos_totais = 0
            
            for i in range(atacantes):
                d20_inimigo = random.randint(1, 20)
                if is_durnn_furia: d20_inimigo = max(d20_inimigo, random.randint(1, 20))
                
                if d20_inimigo + mod_inimigo >= jogador.modificador_defesa or d20_inimigo == 20:
                    acertos_totais += 1
                    dano_base = random.randint(1, 4)
                    if is_durnn_furia: dano_base += 2
                    if d20_inimigo == 20: dano_base *= 2
                    dano_final_revide += dano_base
                    narrativa += f"🗡️ Atk {i+1}: Hit ({dano_base} dano)\n"
                else:
                    narrativa += f"💨 Atk {i+1}: Miss\n"

            if acertos_totais > 0:
                # --- MECÂNICA DE RESISTÊNCIA DA FÚRIA DO BÁRBARO ---
                if "Fúria" in efeitos_atuais:
                    dano_original_revide = dano_final_revide
                    dano_final_revide = max(1, dano_final_revide // 2)
                    narrativa += f"🛡️ A tua Fúria reduziu o dano sofrido pela metade! (Original: {dano_original_revide})\n"
                # --------------------------------------------------

                narrativa += f"🩸 Dano total recebido: {dano_final_revide}\n\n"
            else:
                narrativa += "🛡️ Esquivaste todos os ataques!\n\n"
            
            jogador.hp_atual = max(0, jogador.hp_atual - dano_final_revide)

            # Tentativa de Envenenamento
            if random.randint(1, 100) <= 20 and "Envenenado" not in efeitos_atuais:
                if any(n in inimigo.nome.lower() for n in ["rato", "aranha", "cobra", "troll", "goblin"]):
                    efeitos_atuais.append("Envenenado")
                    narrativa += "🤢 Foste Envenenado pelo ataque inimigo!\n\n"
                    
        return narrativa, dano_final_revide, efeitos_atuais

    async def _resolver_ataque_objeto(self, jogador: Jogador, cena: Cena, alvo_nome: Optional[str], texto: str) -> ActionResult:
        objs = (await self.db.execute(select(ObjetoDestrutivel).filter(ObjetoDestrutivel.cod_sala == cena.cod_sala, ObjetoDestrutivel.ativo == True))).scalars().all()
        alvo = None
        if alvo_nome:
            for obj in objs:
                if alvo_nome.lower() in obj.nome.lower():
                    alvo = obj
                    break
        if not alvo and objs:
            alvo = objs[0]
        
        if not alvo:
            return ActionResult(False, "combate", "Não há alvos válidos para atacar aqui.", {})

        res = processar_ataque_objeto(jogador, alvo)
        if res.quebrou_por_forca:
            alvo.hp_atual = 0; alvo.ativo = False
            return ActionResult(True, "combate", f"💪 Força bruta! {alvo.nome} destruído.", {})
        elif res.acertou:
            alvo.hp_atual = res.hp_restante
            if res.destruido:
                alvo.ativo = False
                loot = getattr(alvo, 'recompensa_ao_destruir', [])
                if loot: adicionar_ao_inventario(jogador, loot)
                return ActionResult(True, "combate", f"🔨 {alvo.nome} destruído! Dano: {res.dano}", {})
            return ActionResult(True, "combate", f"💥 Acertaste {alvo.nome}. Dano: {res.dano}. HP restante: {alvo.hp_atual}/{alvo.hp_max}", {})
        else:
            return ActionResult(False, "combate", f"Errouste o golpe em {alvo.nome}.", {})

    async def _resolver_magia(self, jogador: Jogador, campanha: Campanha, cena: Cena, magia_nome: Optional[str], alvo_nome: Optional[str], texto: str) -> ActionResult:
        if jogador.slots_magia <= 0:
            return ActionResult(False, "magia", "✨ Sem Usos de Magia restantes!", {})
        
        jogador.slots_magia -= 1
        _cls = jogador.classe.lower()
        chave_classe = next((c for c in MAGIAS_POR_CLASSE.keys() if c == _cls), "default")
        magia_info = MAGIAS_POR_CLASSE[chave_classe]

        if magia_nome:
            magia_info["nome"] = magia_nome

        mod_atk_orig = jogador.modificador_ataque
        dano_dado_orig = jogador.dano_dado

        jogador.modificador_ataque = (jogador.mod_int if _cls == "mago" else jogador.mod_cha) + jogador.proficiencia
        jogador.dano_dado = magia_info.get("dano", "1d8")

        resultado = await self._resolver_combate(jogador, campanha, cena, alvo_nome, None, texto)

        jogador.modificador_ataque = mod_atk_orig
        jogador.dano_dado = dano_dado_orig

        resultado.tipo_acao = "magia"
        resultado.narrativa_mecanica = f"{magia_info.get('icone', '🔮')} {magia_info.get('nome', 'Magia')}: " + resultado.narrativa_mecanica
        return resultado

    async def _resolver_manobra(self, jogador: Jogador, campanha: Campanha, cena: Cena, manobra: Optional[str], alvo_nome: Optional[str], texto: str) -> ActionResult:
        efeitos = list(getattr(jogador, 'status_efeitos', []))
        
        if manobra and "levantar" in manobra.lower():
            if "Caído" in efeitos or "Caido" in efeitos:
                if "Caído" in efeitos: efeitos.remove("Caído")
                if "Caido" in efeitos: efeitos.remove("Caido")
                jogador.status_efeitos = efeitos
                return ActionResult(True, "manobra", "🏃 Levantaste-te! Já não estás Caído.", {})
            return ActionResult(False, "manobra", "Já estás de pé.", {})

        if "Agarrado" in efeitos:
            rolagem = random.randint(1, 20) + jogador.mod_str + jogador.proficiencia
            if rolagem >= 14:
                efeitos.remove("Agarrado")
                jogador.status_efeitos = efeitos
                return ActionResult(True, "manobra", f"🔓 Escapaste! (STR {rolagem} vs CD 14)", {})
            return ActionResult(False, "manobra", f"❌ Falhaste em libertar-te. (STR {rolagem} vs CD 14)", {})

        rolagem = random.randint(1, 20) + (jogador.mod_str if manobra in ["empurrar", "derrubar"] else jogador.mod_dex) + jogador.proficiencia
        if rolagem >= 14:
            estado = dict(campanha.estado_salas or {})
            estado["inimigo_debilidade"] = True
            campanha.estado_salas = estado
            return ActionResult(True, "manobra", f"🤸 Manobra bem sucedida! (Teste {rolagem}). O inimigo ficou vulnerável (Vantagem para o grupo).", {})
        return ActionResult(False, "manobra", f"❌ Manobra falhou. (Teste {rolagem})", {})

    async def _resolver_navegacao(self, jogador: Jogador, campanha: Campanha, cena: Cena, direcao: Optional[str], texto: str) -> ActionResult:
        efeitos = list(getattr(jogador, 'status_efeitos', []))
        if "Agarrado" in efeitos:
            return ActionResult(False, "navegacao", "⛓️ Estás Agarrado! Não podes mover-te. Usa uma MANOBRA para escapar.", {})

        # --- 1. BLOQUEIO DE COMBATE E FUGA (ATAQUE DE OPORTUNIDADE) ---
        estado_campanha = dict(campanha.estado_salas or {})
        encontros = (await self.db.execute(select(Encontro).filter(Encontro.cod_sala == cena.cod_sala))).scalars().all()
        encontros_vivos = [e for e in encontros if not estado_campanha.get(f"derrotado_{e.id}")]
        
        texto_low = texto.lower()
        is_fuga = any(p in texto_low for p in ["fugir", "fujo", "correr", "escapar", "recuar"])
        narrativa_fuga = ""

        if encontros_vivos and campanha.em_combate:
            encontro_bloqueio = encontros_vivos[0]
            if is_fuga:
                destino_fuga = campanha.cena_anterior if campanha.cena_anterior else "carvalhal"
                if campanha.cena_atual == "carvalhal":
                    return ActionResult(False, "navegacao", "🛑 Não tens para onde recuar! Terás que lutar.", {})
                
                dano_fuga = random.randint(1, 6) + 2
                rolagem_inimigo = random.randint(1, 20)
                if rolagem_inimigo + 4 >= jogador.modificador_defesa or rolagem_inimigo == 20:
                    jogador.hp_atual = max(0, jogador.hp_atual - dano_fuga)
                    narrativa_fuga = f"🩸 <b>Fuga Arriscada!</b> Ao virares as costas, {encontro_bloqueio.nome_inimigo} acertou-te um Ataque de Oportunidade! Sofreste {dano_fuga} de dano."
                    if jogador.hp_atual <= 0:
                        narrativa_fuga += "\n💀 Caíste na fuga! A Patrulha de Carvalhal resgatou-te, mas perdeste algum ouro..."
                        jogador.hp_atual = jogador.hp_maximo
                        jogador.gold = max(0, jogador.gold - 10)
                        campanha.cena_atual = "carvalhal"
                        jogador.cena_atual = "carvalhal"
                        campanha.em_combate = False
                        jogador.status_efeitos = [] # FIX 3: Limpar status
                        return ActionResult(False, "navegacao", narrativa_fuga, {"nova_cena": "carvalhal"})
                else:
                    narrativa_fuga = f"💨 <b>Fuga Ágil!</b> Conseguiste desviar-te do ataque de {encontro_bloqueio.nome_inimigo} enquanto recuavas."
                
                direcao = destino_fuga
            else:
                return ActionResult(False, "navegacao", f"🛑 <b>Caminho Bloqueado!</b> Tens de lidar com {encontro_bloqueio.nome_inimigo} primeiro ou tentar 'fugir'.", {})

        # --- 2. DESCOBERTA DA DIREÇÃO ---
        if not is_fuga:
            direcao_ia = direcao
            if not direcao_ia:
                from mapa_engine import extrair_direcao
                direcao_ia = await extrair_direcao(texto, cena.conexoes)
                if not direcao_ia or "invalido" in direcao_ia.lower():
                    return ActionResult(False, "navegacao", "Para onde desejas ir? Direção não reconhecida.", {})

            direcao_ia = direcao_ia.lower().strip()
            conexoes = cena.conexoes or {}
            alvo_sala = None
            
            # 1. Tentar correspondência exata ou parcial
            for k, v in conexoes.items():
                if direcao_ia in k.lower() or k.lower() in direcao_ia:
                    alvo_sala = v
                    break
                    
            # 2. Sinónimos caso o JSON Mode tenha generalizado (Descer -> Baixo)
            if not alvo_sala:
                sinonimos = {
                    "baixo": ["baixo", "descer", "descida", "poço", "buraco"],
                    "cima": ["cima", "subir", "subida", "escada"],
                    "dentro": ["dentro", "entrar", "porta"],
                    "fora": ["fora", "sair", "rua"]
                }
                for grupo in sinonimos.values():
                    if direcao_ia in grupo:
                        for k, v in conexoes.items():
                            if any(s in k.lower() for s in grupo):
                                alvo_sala = v
                                break
                        if alvo_sala: break

            # 3. FALLBACK DE SEGURANÇA
            if not alvo_sala:
                from mapa_engine import extrair_direcao
                dir_salvacao = await extrair_direcao(texto, cena.conexoes)
                if dir_salvacao and "invalido" not in dir_salvacao.lower():
                    for k, v in conexoes.items():
                        if dir_salvacao in k.lower():
                            alvo_sala = v
                            break

            if not alvo_sala:
                return ActionResult(False, "navegacao", f"Caminho bloqueado ou inexistente para '{texto}'.", {})
            
            direcao = direcao_ia
        else:
            alvo_sala = direcao

        if "Cobertura" in efeitos: efeitos.remove("Cobertura")
        if "Fúria" in efeitos: efeitos.remove("Fúria")
        jogador.status_efeitos = efeitos

        campanha.cena_anterior = campanha.cena_atual
        campanha.cena_atual = alvo_sala
        jogador.cena_atual = alvo_sala

        jogadores_party = (await self.db.execute(select(Jogador).filter(Jogador.party_id == campanha.party_id))).scalars().all()
        for membro in jogadores_party:
            membro.cena_atual = alvo_sala

        nova_cena = (await self.db.execute(select(Cena).filter(Cena.cod_sala == alvo_sala))).scalars().first()
        nome_sala = nova_cena.nome_sala if nova_cena else alvo_sala

        # --- 3. HAZARDS (PERIGOS DE TERRENO) ---
        narrativa_hazard = ""
        hazards = getattr(nova_cena, 'hazards', None) or []
        for hazard in hazards:
            tipo = hazard.get("tipo", "")
            cd = hazard.get("cd", 13)
            dano_str = hazard.get("dano", "1d4")
            descricao = hazard.get("descricao", "Um perigo oculto")

            try:
                partes = dano_str.split("d")
                dano_total = sum(random.randint(1, int(partes[1])) for _ in range(int(partes[0])))
            except Exception:
                dano_total = random.randint(1, 4)

            mod_jogador = jogador.mod_dex if tipo == "dex_save" else (jogador.mod_str if tipo == "str_save" else jogador.mod_con)
            rolagem = random.randint(1, 20) + mod_jogador

            if tipo == "dano_automatico":
                jogador.hp_atual = max(0, jogador.hp_atual - dano_total)
                narrativa_hazard += f"\n🔥 <b>{descricao}!</b> Sofreste {dano_total} de dano inevitável na área."
            elif rolagem >= cd:
                narrativa_hazard += f"\n✅ <b>{descricao}!</b> Desviaste com sucesso (Teste {rolagem} vs CD {cd})."
            else:
                jogador.hp_atual = max(0, jogador.hp_atual - dano_total)
                narrativa_hazard += f"\n❌ <b>{descricao}!</b> Foste atingido (Teste {rolagem} vs CD {cd}). Sofreste {dano_total} de dano!"

        texto_final = f"👣 Segues para {direcao if not is_fuga else 'uma área segura'}."
        if narrativa_fuga: texto_final = f"{narrativa_fuga}\n\n{texto_final}"
        if narrativa_hazard: texto_final = f"{texto_final}\n{narrativa_hazard}"

        if jogador.hp_atual <= 0:
            texto_final += "\n💀 Sucumbiste aos perigos! A Patrulha de Carvalhal resgatou-te, mas perdeste algum ouro..."
            jogador.hp_atual = jogador.hp_maximo
            jogador.gold = max(0, jogador.gold - 10)
            campanha.cena_atual = "carvalhal"
            jogador.cena_atual = "carvalhal"
            campanha.em_combate = False
            jogador.status_efeitos = [] # FIX 3: Limpar status
            return ActionResult(False, "navegacao", texto_final.strip(), {"nova_cena": "carvalhal"})

        return ActionResult(True, "navegacao", texto_final.strip(), {"nova_cena": alvo_sala})

    async def _resolver_interacao(self, jogador: Jogador, campanha: Campanha, cena: Cena, alvo_nome: Optional[str], item: Optional[str], texto: str) -> ActionResult:
        texto_low = texto.lower()
        
        # 1. Vasculhar Sala (Loot Fixo)
        if any(p in texto_low for p in ["vasculhar", "procurar", "sala", "chão"]) and cena.loot_fixo:
            itens_encontrados = cena.loot_fixo
            itens_reais = adicionar_ao_inventario(jogador, itens_encontrados)
            cena.loot_fixo = []
            return ActionResult(True, "interacao", f"👀 Vasculhaste a sala e encontraste: {', '.join(itens_reais)}.", {})

        # 2. Usar Item (Poções / Antídotos)
        if item and ("poção" in item.lower() or "antídoto" in item.lower() or "pocao" in item.lower()):
            inv = obter_inventario_limpo(jogador.inventario)
            item_no_inv = next((i for i in inv if item.lower() in i.lower()), None)
            if not item_no_inv:
                return ActionResult(False, "interacao", f"Não tens {item} no inventário.", {})
            
            inv.remove(item_no_inv)
            jogador.inventario = inv
            if "antídoto" in item_no_inv.lower() or "antidoto" in item_no_inv.lower():
                efeitos = list(getattr(jogador, 'status_efeitos', []))
                if "Envenenado" in efeitos: efeitos.remove("Envenenado")
                jogador.status_efeitos = efeitos
                return ActionResult(True, "interacao", f"🧪 Bebeste {item_no_inv}. Veneno neutralizado!", {})
            else:
                cura = sum(random.randint(1, 4) for _ in range(2)) + 2
                jogador.hp_atual = min(jogador.hp_maximo, jogador.hp_atual + cura)
                return ActionResult(True, "interacao", f"🧪 Bebeste {item_no_inv}. Curaste {cura} HP!", {})

        # 3. Interagir com NPCs e Sistema de Missões
        npcs = (await self.db.execute(select(Npc).filter(Npc.cod_sala == cena.cod_sala))).scalars().all()
        for npc in npcs:
            if (alvo_nome and alvo_nome.lower() in npc.nome.lower()) or (npc.nome.lower().split()[0] in texto_low):
                dialogo = npc.dialogo_base
                inv = obter_inventario_limpo(jogador.inventario)
                
                # Check Item Gatilho
                if npc.item_gatilho and any(npc.item_gatilho.lower() in i.lower() for i in inv):
                    dialogo = npc.dialogo_item_especial or npc.dialogo_base
                
                # Resolução Direta de Missão do Ferreiro
                if "ferreiro" in npc.nome.lower():
                    missao = (await self.db.execute(select(Missao).filter(Missao.jogador_telefone == jogador.telefone, Missao.npc_nome == "Ferreiro de Carvalhal"))).scalars().first()
                    qtd_dentes = sum(1 for i in inv if "Dente de Goblin" in i)
                    
                    if not missao:
                        nova_missao = Missao(
                            jogador_telefone=jogador.telefone, npc_nome="Ferreiro de Carvalhal", titulo="Lâminas e Dentes",
                            descricao="Traz-me 3 Dentes de Goblin como prova de abate.",
                            objetivo_item="Dente de Goblin", objetivo_quantidade=3, recompensa_ouro=50, recompensa_xp=150
                        )
                        self.db.add(nova_missao)
                        return ActionResult(True, "interacao", f"🔨 {npc.nome}:\n\"{dialogo}\"\n\n📜 Nova Missão: Lâminas e Dentes. (Anotado no teu /missoes)", {})
                    elif not missao.concluida and qtd_dentes >= missao.objetivo_quantidade:
                        for _ in range(missao.objetivo_quantidade):
                            item_remover = next(i for i in inv if "Dente de Goblin" in i)
                            inv.remove(item_remover)
                        jogador.inventario = inv
                        jogador.gold += missao.recompensa_ouro
                        jogador.xp += missao.recompensa_xp
                        missao.concluida = True
                        return ActionResult(True, "interacao", f"🔨 {npc.nome}:\n\"Pelos Deuses, tu conseguiste mesmo! Aqui está o pagamento.\"\n\n✅ Missão Concluída!\n🪙 +{missao.recompensa_ouro} PO\n🌟 +{missao.recompensa_xp} XP", {})

                return ActionResult(True, "interacao", f"🗣️ Falaste com {npc.nome}:\n\"{dialogo}\"", {})

        # 4. Interação com Baús / Armadilhas / Portas (Interativos)
        interativos = (await self.db.execute(select(Interativo).filter(Interativo.cod_sala == cena.cod_sala, Interativo.ativo == True))).scalars().all()
        for obj in interativos:
            if (alvo_nome and alvo_nome.lower() in obj.nome.lower()) or (obj.tipo.lower() in texto_low):
                mod = getattr(jogador, f"mod_{obj.atributo_teste.lower()}", 0)
                
                # --- PROFICIÊNCIA DE BACKGROUND REIMPLANTADA ---
                bonus_prof = 0
                pericias = BACKGROUND_SKILLS.get(jogador.background, [])
                if obj.atributo_teste == "DEX" and any(p in pericias for p in ["Furtividade", "Acrobacia"]): bonus_prof = jogador.proficiencia
                if obj.atributo_teste == "INT" and any(p in pericias for p in ["Arcanismo", "História", "Investigação"]): bonus_prof = jogador.proficiencia
                if obj.atributo_teste == "WIS" and any(p in pericias for p in ["Percepção", "Intuição", "Sobrevivência"]): bonus_prof = jogador.proficiencia
                if obj.atributo_teste == "STR" and any(p in pericias for p in ["Atletismo"]): bonus_prof = jogador.proficiencia
                if obj.atributo_teste == "CHA" and any(p in pericias for p in ["Persuasão", "Enganação", "Intimidação"]): bonus_prof = jogador.proficiencia
                
                total = random.randint(1, 20) + mod + bonus_prof
                # -----------------------------------------------
                
                if total >= obj.cd_teste:
                    obj.ativo = False
                    loot = obj.recompensa if obj.recompensa else []
                    if obj.tipo == "bau": loot = gerar_loot_bau(jogador.nivel)
                    itens_reais = adicionar_ao_inventario(jogador, loot)
                    msg_extra = f" Itens recolhidos: {', '.join(itens_reais)}" if itens_reais else ""
                    return ActionResult(True, "interacao", f"✅ Sucesso no teste de {obj.atributo_teste} ({total} vs CD {obj.cd_teste}). {obj.nome} manipulado!{msg_extra}", {})
                else:
                    dano = obj.dano_falha if obj.dano_falha > 0 else 0
                    if dano > 0: jogador.hp_atual = max(0, jogador.hp_atual - dano)
                    if obj.tipo == "armadilha": obj.ativo = False
                    
                    msg_falha = f"❌ Falha no teste ({total} vs CD {obj.cd_teste}). {obj.nome} resistiu. Dano sofrido: {dano}"
                    if jogador.hp_atual <= 0:
                        msg_falha += "\n💀 Foste nocauteado pela armadilha! A Patrulha resgatou-te, mas perdeste algum ouro..."
                        jogador.hp_atual = jogador.hp_maximo
                        jogador.gold = max(0, jogador.gold - 10)
                        campanha.cena_atual = "carvalhal"
                        jogador.cena_atual = "carvalhal"
                        campanha.em_combate = False
                        jogador.status_efeitos = [] # FIX 3: Limpar status
                        
                    return ActionResult(False, "interacao", msg_falha, {})

        return ActionResult(False, "interacao", "Não encontraste nada de útil para interagir diretamente.", {})

    async def _resolver_descanso(self, jogador: Jogador, campanha: Campanha, cena: Cena, texto: str) -> ActionResult:
        if campanha.cena_atual == "carvalhal":
            jogador.hp_atual = jogador.hp_maximo
            jogador.slots_magia = jogador.slots_magia_max
            jogador.hit_dice_atual = getattr(jogador, 'hit_dice_max', 1)
            jogador.status_efeitos = []
            return ActionResult(True, "descanso", "🛌 Descanso Longo na Vila. HP e Magia restaurados!", {})
        
        if jogador.hit_dice_atual > 0:
            jogador.hit_dice_atual -= 1
            cura = max(1, (jogador.hp_maximo // 4) + jogador.mod_con)
            jogador.hp_atual = min(jogador.hp_maximo, jogador.hp_atual + cura)
            return ActionResult(True, "descanso", f"🏕️ Descanso Curto. Curaste {cura} HP. Hit Dice: {jogador.hit_dice_atual}/{jogador.hit_dice_max}", {})
        
        return ActionResult(False, "descanso", "⚠️ Exausto! Sem Hit Dice. Regressa à Vila.", {})

    async def _resolver_teste(self, jogador: Jogador, cena: Cena, texto: str) -> ActionResult:
        from ai_engine import decidir_atributo_teste
        
        atr = await decidir_atributo_teste(texto)
        mod_base = getattr(jogador, f"mod_{atr.lower()}", 0)
        
        pericias_do_jogador = BACKGROUND_SKILLS.get(jogador.background, [])
        texto_limpo = texto.lower()
        
        usou_pericia = False
        pericia_usada = ""
        for p in pericias_do_jogador:
            if p.lower() in texto_limpo:
                usou_pericia = True
                pericia_usada = p
                break
                
        mod_final = (mod_base + jogador.proficiencia) if usou_pericia else mod_base
        msg_extra = f" (+{jogador.proficiencia} Prof. em {pericia_usada})" if usou_pericia else ""
        
        total = random.randint(1, 20) + mod_final
        
        return ActionResult(True, "outro", f"🎲 <b>Teste de {atr}:</b> Rolaste <b>{total}</b>{msg_extra}. O Mestre usará este valor para a tua observação.", {})