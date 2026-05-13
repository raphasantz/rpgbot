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
        status_jogador = getattr(jogador, 'status_efeitos', [])

        # --- 1. FILTRO DE STATUS RESTRITIVOS (O jogador pode agir?) ---
        if "Atordoado" in status_jogador:
            return ActionResult(False, "Estás atordoado! Perdes o teu turno e não consegues agir.", {})
            
        if intencao == "NAVEGAR" and "Agarrado" in status_jogador:
            return ActionResult(False, "A tua velocidade é 0. Estás agarrado e não podes mover-te até te libertares!", {})

        # --- 2. ROTEAMENTO DE INTENÇÃO ---
        if intencao == "COMBATE":
            return await self._resolver_combate(jogador, alvo)
            
        elif intencao == "MANOBRA":
            return await self._resolver_manobra(jogador, alvo, texto_jogador)
            
        elif intencao == "CURAR" or intencao == "USAR_ITEM":
            # Aqui depois podes adicionar a tua lógica de cura
            return ActionResult(True, "Usaste um item.", {"intencao": intencao})

        # Fallback genérico para intenções narrativas ou falhas
        return ActionResult(True, "Ação resolvida pelo ambiente.", {"intencao": intencao})

    async def _resolver_combate(self, jogador, alvo) -> ActionResult:
        # A matemática é delegada para o combat_logic (que é síncrono e já calcula vantagem/desvantagem)
        # O alvo pode ser um inimigo instanciado nos handlers. Pegamos os dados dinamicamente.
        alvo_ca = getattr(alvo, 'ca', 10)
        alvo_status = getattr(alvo, 'status_efeitos', [])

        # Retira o await, pois a função é síncrona
        resultado_ataque = self.combat_logic.processar_ataque_fisico(
            jogador=jogador, 
            inimigo_ca=alvo_ca, 
            defensor_status=alvo_status,
            tipo_ataque="melee" 
        )

        # Como retorna uma Dataclass (ResultadoAtaque), acessamos como atributos
        acertou = resultado_ataque.acertou
        dano = resultado_ataque.dano
        rolagem_final = resultado_ataque.total_ataque
        critico = resultado_ataque.critico
        detalhes = resultado_ataque.detalhes_d20
        
        narrativa = f"🎲 Rolagem de Ataque: {detalhes} + Mods = {rolagem_final} vs CA {alvo_ca}.\n"

        if acertou:
            texto_crit = "🎯 ACERTO CRÍTICO! " if critico else "💥 Acerto! "
            narrativa += f"{texto_crit}Causaste {dano} de dano a {alvo.nome}.\n"
            
            # --- DISPARO DE EVENTOS DE BOSS (Boss Phases) ---
            if getattr(alvo, 'is_boss', False):
                narrativa_boss = await self._checar_fases_boss(alvo)
                if narrativa_boss:
                    narrativa += f"\n⚠️ {narrativa_boss}"
        else:
            narrativa += f"🛡️ O teu ataque falhou ou foi bloqueado por {alvo.nome}."

        return ActionResult(True, narrativa, {"dano": dano, "acertou": acertou})

    async def _resolver_manobra(self, jogador, alvo, texto: str) -> ActionResult:
        """
        Exemplo de resolução de Empurrar, Derrubar ou Agarrar
        """
        import random
        rolagem = random.randint(1, 20) + getattr(jogador, 'mod_str', 0)
        
        if rolagem >= 14:
            # Em vez de alvo.status = "Caído", adicionamos à lista de efeitos
            alvo_status = getattr(alvo, 'status_efeitos', [])
            if "Caído" not in alvo_status:
                alvo_status.append("Caído")
            return ActionResult(True, f"🥋 Sucesso! Rolaste {rolagem}. {alvo.nome} foi derrubado e está agora CAÍDO (ataques contra ele têm Vantagem)!", {"status_aplicado": "Caído"})
        else:
            return ActionResult(False, f"❌ Falha! Rolaste {rolagem}. {alvo.nome} resistiu à tua manobra.", {})

    async def _checar_fases_boss(self, boss) -> str:
        """
        Sistema de Eventos Emergentes. Avalia se o Boss muda de estado.
        """
        hp_max = getattr(boss, 'hp_max', 1)
        hp_atual = getattr(boss, 'hp_atual', hp_max) # Pegamos o HP atual do combate
        hp_metade = hp_max / 2
        
        fase_atual = getattr(boss, 'fase_atual', 1)

        if hp_atual <= hp_metade and fase_atual == 1:
            boss.fase_atual = 2
            boss.ca -= 2         # Fica descuidado (mais fácil de acertar)
            # Aumentamos o dano base, precisaremos garantir que o handler do Inimigo lide com isto
            return f"[EVENTO DE BOSS] O sangue escorre pelo rosto de {boss.nome}! Ele entra numa FÚRIA cega (A sua CA diminuiu, mas os seus golpes serão letais)!"
            
        return ""