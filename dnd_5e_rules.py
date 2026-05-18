"""
dnd_5e_rules.py - Regras completas de D&D 5e para o sistema A Cidadela sem Sol
Implementa: perícias, condições, tipos de dano, ações de combate
"""

# =============================================================================
# PERÍCIAS OFICIAIS D&D 5E (18 perícias)
# =============================================================================
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

# Mapeamento reverso: atributo -> lista de perícias
PERICIAS_POR_ATRIBUTO = {
    "STR": ["Atletismo"],
    "DEX": ["Acrobacia", "Furtividade", "Prestidigitação"],
    "INT": ["Arcanismo", "História", "Investigação", "Natureza", "Religião"],
    "WIS": ["Adestrar Animais", "Intuição", "Medicina", "Percepção", "Sobrevivência"],
    "CHA": ["Enganação", "Intimidação", "Performance", "Persuasão"]
}

# =============================================================================
# CONDIÇÕES OFICIAIS D&D 5E
# =============================================================================
CONDICOES_DND_5E = {
    "Cego": {
        "descricao": "Não pode ver e falha automaticamente em testes de habilidade que requerem visão.",
        "efeitos": {
            "desvantagem_ataques": True,  # Desvantagem em ataques
            "vantagem_ataques_contra": True,  # Inimigos têm vantagem contra ele
            "falha_testes_visao": True
        }
    },
    "Surdo": {
        "descricao": "Não pode ouvir e falha automaticamente em testes de habilidade que requerem audição.",
        "efeitos": {
            "falha_testes_audicao": True
        }
    },
    "Paralisado": {
        "descricao": "Incapacitado, não pode se mover ou falar, falha automaticamente em testes de Força e Destreza.",
        "efeitos": {
            "incapacitado": True,
            "movimento_zero": True,
            "falha_testes_forca_destreza": True,
            "vantagem_ataques_contra": True,
            "critico_automatico_range": True  # Ataques corpo-a-corpo são críticos automáticos
        }
    },
    "Petrificado": {
        "descricao": "Transformado em substância inanimada, inconsciente, resistente a todos os danos.",
        "efeitos": {
            "incapacitado": True,
            "inconsciente": True,
            "resistencia_todos_danos": True,
            "peso_multiplicado_10": True
        }
    },
    "Invisível": {
        "descricao": "Não pode ser visto sem auxílio mágico ou sentidos especiais.",
        "efeitos": {
            "vantagem_ataques": True,
            "desvantagem_ataques_contra": True,
            "invisivel": True
        }
    },
    "Agarrado": {
        "descricao": "Velocidade reduzida a 0, não pode se beneficiar de bônus de velocidade.",
        "efeitos": {
            "velocidade_zero": True,
            "condicao_termina_se_movido": True
        }
    },
    "Restrito": {
        "descricao": "Velocidade 0, desvantagem em ataques, vantagem em ataques contra ele.",
        "efeitos": {
            "velocidade_zero": True,
            "desvantagem_ataques": True,
            "vantagem_ataques_contra": True,
            "desvantagem_testes_destreza": True
        }
    },
    "Inconsciente": {
        "descricao": "Incapacitado, cai no chão, falha automaticamente em testes de Força e Destreza.",
        "efeitos": {
            "incapacitado": True,
            "caido": True,
            "falha_testes_forca_destreza": True,
            "vantagem_ataques_contra": True,
            "critico_automatico_range": True
        }
    },
    "Morto": {
        "descricao": "O personagem faleceu. Apenas magia poderosa como Ressurreição ou Desejo pode trazê-lo de volta.",
        "efeitos": {
            "hp_zero_incuravel": True,
            "fim_jogo": True
        }
    },
    # Condições adicionais do sistema
    "Envenenado": {
        "descricao": "Desvantagem em testes de ataque e testes de habilidade.",
        "efeitos": {
            "desvantagem_ataques": True,
            "desvantagem_testes_habilidade": True
        }
    },
    "Atordoado": {
        "descricao": "Incapacitado, não pode agir, fala arrastada, falha em testes de Força e Destreza.",
        "efeitos": {
            "incapacitado": True,
            "falha_testes_forca_destreza": True,
            "vantagem_ataques_contra": True
        }
    },
    "Assustado": {
        "descricao": "Desvantagem em testes de habilidade e ataques enquanto fonte do medo estiver à vista.",
        "efeitos": {
            "desvantagem_ataques": True,
            "desvantagem_testes_habilidade": True,
            "nao_pode_aproximar": True
        }
    },
    "Caído": {
        "descricao": "No chão. Ataques corpo-a-corpo contra têm vantagem, ataques à distância contra têm desvantagem.",
        "efeitos": {
            "desvantagem_ataques_proprios": True,
            "levantar_gasta_metade_movimento": True
        }
    },
    "Esquivando": {
        "descricao": "Posição defensiva. Inimigos têm desvantagem para atacar até o próximo turno.",
        "efeitos": {
            "desvantagem_ataques_contra": True,
            "dura_ate_proximo_turno": True
        }
    },
    "Cobertura": {
        "descricao": "Protegido por obstáculo. +2 na CA contra ataques.",
        "efeitos": {
            "bonus_ca": 2,
            "cobertura_parcial": True
        }
    },
    "Ajudado": {
        "descricao": "Preparou ajuda para aliado. Próximo ataque do grupo tem vantagem.",
        "efeitos": {
            "concede_vantagem_aliado": True,
            "consumido_no_proximo_ataque": True
        }
    },
    "Fúria": {
        "descricao": "Bárbaro em fúria. +dano, resistência a dano físico, vantagem em testes de Força.",
        "efeitos": {
            "bonus_dano": 2,  # Varia por nível
            "resistencia_contundente": True,
            "resistencia_perfurante": True,
            "resistencia_cortante": True,
            "vantagem_testes_forca": True
        }
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
    "Ataque": {
        "descricao": "Realiza um ataque corpo-a-corpo ou à distância",
        "acao_principal": True
    },
    "Destruir/Arrombar": {
        "descricao": "Teste de Força para quebrar objetos ou portas",
        "acao_principal": True,
        "teste": "STR"
    },
    "Usar Objeto": {
        "descricao": "Interage com um objeto do cenário",
        "acao_principal": False,  # Pode ser ação livre ou bônus
        "limitacao": "1 por turno"
    },
    "Preparar Ação": {
        "descricao": "Prepara uma ação para ser executada como reação quando um gatilho ocorrer",
        "acao_principal": True,
        "requer_reacao": True
    },
    "Ajuda": {
        "descricao": "Concede vantagem ao próximo ataque de um aliado contra criatura próxima",
        "acao_principal": True,
        "alcance": "5 pés"
    },
    "Investida": {
        "descricao": "Move-se até metade do deslocamento e empurra alvo",
        "acao_principal": True,
        "teste": "STR (Atletismo) vs STR ou DES do alvo"
    },
    "Derrubar": {
        "descricao": "Tenta derrubar alvo no chão",
        "acao_principal": True,
        "substitui_ataque": True,
        "teste": "STR (Atletismo) vs STR ou DES do alvo"
    },
    "Desengajar": {
        "descricao": "Movimento não provoca ataques de oportunidade",
        "acao_principal": True
    },
    "Correr": {
        "descricao": "Dobra o deslocamento neste turno",
        "acao_principal": True
    },
    "Esquivar": {
        "descricao": "Inimigos têm desvantagem contra você até seu próximo turno",
        "acao_principal": True,
        "dura_ate": "proximo_turno"
    },
    "Ataque de Oportunidade": {
        "descricao": "Ataque gratuito quando inimigo sai do seu alcance",
        "reação": True,
        "gasta_reacao": True
    }
}

# =============================================================================
# SALVAS DE MORTE (Death Saving Throws)
# =============================================================================
def calcular_salvacao_morte(rolagem: int, sucessos: int = 0, falhas: int = 0) -> dict:
    """
    Calcula resultado de salvacao de morte conforme D&D 5e.
    Retorna: {sucesso, falha, estabilizou, morreu, novos_sucessos, novas_falhas}
    """
    resultado = {
        "sucesso": False,
        "falha": False,
        "estabilizou": False,
        "morreu": False,
        "novos_sucessos": sucessos,
        "novas_falhas": falhas
    }
    
    if rolagem == 20:
        # Crítico 20: recupera 1 HP imediatamente
        resultado["estabilizou"] = True
        resultado["hp_recuperado"] = 1
        return resultado
    
    if rolagem == 1:
        # Crítico 1: conta como 2 falhas
        resultado["falha"] = True
        resultado["novas_falhas"] = falhas + 2
        if resultado["novas_falhas"] >= 3:
            resultado["morreu"] = True
        return resultado
    
    if rolagem >= 10:
        resultado["sucesso"] = True
        resultado["novos_sucessos"] = sucessos + 1
        if resultado["novos_sucessos"] >= 3:
            resultado["estabilizou"] = True
    else:
        resultado["falha"] = True
        resultado["novas_falhas"] = falhas + 1
        if resultado["novas_falhas"] >= 3:
            resultado["morreu"] = True
    
    return resultado

# =============================================================================
# VULNERABILIDADES, RESISTÊNCIAS E IMUNIDADES
# =============================================================================
def aplicar_modificadores_dano(dano_base: int, tipo_dano: str, 
                                vulnerabilidades: list = None,
                                resistencias: list = None,
                                imunidades: list = None) -> int:
    """
    Aplica modificadores de dano conforme D&D 5e.
    Ordem: Imunidade > Resistência > Vulnerabilidade
    """
    if imunidades and tipo_dano in imunidades:
        return 0
    
    dano_final = dano_base
    
    if resistencias and tipo_dano in resistencias:
        dano_final = max(1, dano_final // 2)
    
    if vulnerabilidades and tipo_dano in vulnerabilidades:
        dano_final *= 2
    
    return dano_final

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
