import asyncio
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class ActionResult:
    sucesso: bool
    narrativa_mecanica: str
    dados_extras: Dict[str, Any]

class ActionResolver:
    """
    O Coração do Motor D&D 5e. 
    Recebe a intenção da IA e garante que as regras, status e eventos ocorrem na ordem certa.
    """
    def __init__(self, combat_logic):
        # Injetamos o combat_logic para ele fazer a matemática pesada dos dados
        self.combat_logic = combat_logic

    async def executar(self, jogador, alvo, intencao: str, texto_jogador: str) -> ActionResult:
        """
        Pipeline estrito de execução de turno.
        Ordem: Status -> Roteamento -> Resolução -> Boss Triggers
        """
        # --- 1. FILTRO DE STATUS RESTRITIVOS (O jogador pode agir?) ---
        if jogador.status == "Atordoado":
            return ActionResult(False, "Estás atordoado! Perdes o teu turno e não consegues agir.", {})
            
        if intencao == "NAVEGAR" and jogador.status == "Agarrado":
            return ActionResult(False, "A tua velocidade é 0. Estás agarrado e não podes mover-te até te libertares!", {})

        # --- 2. ROTEAMENTO DE INTENÇÃO ---
        if intencao == "COMBATE":
            return await self._resolver_combate(jogador, alvo)
            
        elif intencao == "MANOBRA":
            return await self._resolver_manobra(jogador, alvo, texto_jogador)
            
        elif intencao == "CURAR" or intencao == "USAR_ITEM":
            return await self._resolver_cura(jogador)

        # Fallback genérico para intenções narrativas ou falhas
        return ActionResult(True, "Ação resolvida pelo ambiente.", {"intencao": intencao})

    async def _resolver_combate(self, jogador, alvo) -> ActionResult:
        # --- Lógica de Vantagem e Desvantagem do 5e ---
        tem_vantagem = False
        tem_desvantagem = False

        # Status do alvo
        if alvo.status == "Caído" or alvo.status == "Atordoado":
            tem_vantagem = True
            
        # Status do atacante
        if jogador.status == "Caído" or jogador.status == "Envenenado":
            tem_desvantagem = True

        # Prevenção de conflito (Vantagem e Desvantagem anulam-se no 5e)
        if tem_vantagem and tem_desvantagem:
            tem_vantagem = False
            tem_desvantagem = False

        # --- Matemática (Delega para o teu combat_logic) ---
        # Nota: Ajusta os parâmetros conforme a função real que tens no combat_logic.py
        resultado_ataque = await self.combat_logic.processar_ataque_fisico(
            atacante=jogador, 
            defensor=alvo, 
            vantagem=tem_vantagem, 
            desvantagem=tem_desvantagem
        )

        acertou = resultado_ataque.get("acertou", False)
        dano = resultado_ataque.get("dano", 0)
        rolagem_final = resultado_ataque.get("rolagem_final", 0)
        
        narrativa = f"🎲 Rolagem de Ataque: {rolagem_final} vs CA {alvo.ca}.\n"

        if acertou:
            narrativa += f"💥 Acerto! Causaste {dano} de dano a {alvo.nome}.\n"
            # --- DISPARO DE EVENTOS DE BOSS (Boss Phases) ---
            if getattr(alvo, 'is_boss', False):
                narrativa_boss = await self._checar_fases_boss(alvo)
                if narrativa_boss:
                    narrativa += f"\n⚠️ {narrativa_boss}"
        else:
            narrativa += f"🛡️ O teu ataque falhou ou foi bloqueado por {alvo.nome}."

        return ActionResult(True, narrativa, resultado_ataque)

    async def _resolver_manobra(self, jogador, alvo, texto: str) -> ActionResult:
        """
        Exemplo de resolução de Empurrar, Derrubar ou Agarrar
        """
        # Aqui farias um teste resistido (Atletismo vs Atletismo/Acrobacia)
        # Vamos assumir um sucesso simples para a estrutura (CD 14)
        import random
        rolagem = random.randint(1, 20) + jogador.mod_str
        
        if rolagem >= 14:
            alvo.status = "Caído"
            return ActionResult(True, f"🥋 Sucesso! Rolaste {rolagem}. {alvo.nome} foi derrubado e está agora CAÍDO (ataques contra ele têm Vantagem)!", {"status_aplicado": "Caído"})
        else:
            return ActionResult(False, f"❌ Falha! Rolaste {rolagem}. {alvo.nome} resistiu à tua manobra.", {})

    async def _checar_fases_boss(self, boss) -> str:
        """
        Sistema de Eventos Emergentes. Avalia se o Boss muda de estado.
        """
        # Fase 2: Durnn Fúria (HP cai abaixo de 50%)
        hp_metade = boss.hp_max / 2
        
        # Garante que ele tem a propriedade fase_atual (podes setar default no models.py como 1)
        fase_atual = getattr(boss, 'fase_atual', 1)

        if boss.hp <= hp_metade and fase_atual == 1:
            boss.fase_atual = 2
            boss.ca -= 2         # Fica descuidado (mais fácil de acertar)
            boss.dano_bonus += 4 # Bate mais forte
            return f"[EVENTO DE BOSS] O sangue escorre pelo rosto de {boss.nome}! Ele entra numa FÚRIA cega (A sua CA diminuiu, mas os seus golpes serão letais)!"
            
        return ""