# Melhorias D&D 5e Implementadas - A Cidadela sem Sol

## 📋 Resumo da Implementação

Foram implementadas as seguintes mecânicas oficiais do D&D 5ª Edição no sistema "A Cidadela sem Sol":

---

## ✅ 1. Sistema de Perícias Completo (18 perícias)

**Arquivo:** `ui_utils.py` e `dnd_5e_rules.py`

### Perícias por Atributo:
- **FORÇA (STR):** Atletismo
- **DESTREZA (DEX):** Acrobacia, Furtividade, Prestidigitação
- **INTELIGÊNCIA (INT):** Arcanismo, História, Investigação, Natureza, Religião
- **SABEDORIA (WIS):** Adestrar Animais, Intuição, Medicina, Percepção, Sobrevivência
- **CARISMA (CHA):** Enganação, Intimidação, Performance, Persuasão

### Uso no Código:
```python
from ui_utils import PERICIAS_DND_5E, PERICIAS_POR_ATRIBUTO

# Verificar qual atributo uma perícia usa
atributo = PERICIAS_DND_5E["Furtividade"]  # Retorna "DEX"

# Listar todas as perícias de um atributo
pericias_wis = PERICIAS_POR_ATRIBUTO["WIS"]
```

---

## ✅ 2. Condições Oficiais (17 condições)

**Arquivo:** `ui_utils.py` e `dnd_5e_rules.py`

### Condições Implementadas:
| Condição | Efeitos Principais |
|----------|-------------------|
| **Cego** | Desvantagem em ataques, inimigos têm vantagem |
| **Surdo** | Falha em testes que requerem audição |
| **Paralisado** | Incapacitado, falha em testes de FOR/DES, críticos automáticos |
| **Petrificado** | Inconsciente, resistência a todos os danos |
| **Invisível** | Vantagem em ataques, desvantagem contra |
| **Agarrado** | Velocidade zero |
| **Restrito** | Desvantagem em ataques, inimigos têm vantagem |
| **Inconsciente** | Falha em testes de FOR/DES, críticos automáticos |
| **Morto** | Fim de jogo |
| **Envenenado** | Desvantagem em ataques e testes |
| **Atordoado** | Incapacitado, falha em testes de FOR/DES |
| **Assustado** | Desvantagem em ataques e testes |
| **Caído** | Ataques corpo-a-corpo contra têm vantagem |
| **Esquivando** | Inimigos têm desvantagem até próximo turno |
| **Cobertura** | +2 na CA |
| **Ajudado** | Concede vantagem ao aliado |
| **Fúria** | +dano, resistência física, vantagem em FOR |

### Estrutura de Dados:
```python
CONDICOES_DND_5E["Cego"] = {
    "descricao": "Não pode ver...",
    "efeitos": {
        "desvantagem_ataques": True,
        "vantagem_ataques_contra": True,
        "falha_testes_visao": True
    }
}
```

---

## ✅ 3. Tipos de Dano Completos (13 tipos)

**Arquivo:** `ui_utils.py` e `dnd_5e_rules.py`

### Tipos Implementados:
| Tipo | Ícone | Descrição |
|------|-------|-----------|
| Ácido | 🧪 | Dano corrosivo |
| Fogo | 🔥 | Dano por chamas |
| Frio | ❄️ | Dano congelante |
| Elétrico | ⚡ | Dano por lightning |
| Trovejante | 🔊 | Dano sônico/trovão |
| Perfurante | 🗡️ | Dano físico perfurante |
| Cortante | ⚔️ | Dano físico cortante |
| Contundente | 👊 | Dano físico de impacto |
| Venenoso | ☠️ | Dano por toxinas |
| Radiante | ✨ | Dano divino/luz |
| Necrótico | 💀 | Dano de energia negativa |
| Força | 💫 | Dano de força pura mágica |
| Psíquico | 🧠 | Dano mental |

### Função de Aplicação de Dano:
```python
from dnd_5e_rules import aplicar_modificadores_dano

dano_final = aplicar_modificadores_dano(
    dano_base=10,
    tipo_dano="fogo",
    vulnerabilidades=["fogo"],  # Dano dobrado
    resistencias=[], 
    imunidades=[]
)  # Retorna 20
```

---

## ✅ 4. Ações de Combate (11 ações)

**Arquivo:** `ui_utils.py` e `dnd_5e_rules.py`

### Ações Principais:
- **Ataque:** Ataque corpo-a-corpo ou à distância
- **Destruir/Arrombar:** Teste de Força para objetos
- **Usar Objeto:** Interação com cenário (1/turno)
- **Preparar Ação:** Reação mediante gatilho
- **Ajuda:** Concede vantagem a aliado (alcance 5 pés)
- **Investida:** Empurrar alvo
- **Derrubar:** Derrubar alvo no chão
- **Desengajar:** Movimento sem provocar ataques de oportunidade
- **Correr:** Dobra deslocamento
- **Esquivar:** Inimigos têm desvantagem
- **Ataque de Oportunidade:** Reação quando inimigo sai do alcance

---

## ✅ 5. Sistema de Cobertura

```python
COBERTURA_BONUS = {
    "parcial": {"ca_bonus": 2, "des_bonus": 2},
    "tres_quartos": {"ca_bonus": 5, "des_bonus": 5},
    "total": {"invisivel": True}
}
```

---

## ✅ 6. Sistema de Terreno e Movimento

```python
TERRENOS = {
    "normal": {"custo_movimento": 1},
    "difícil": {"custo_movimento": 2},
    "íngreme": {"custo_movimento": 2},
    "nadando": {"custo_movimento": 2},
    "escalada": {"custo_movimento": 2}
}
```

---

## ✅ 7. Salvas de Morte (Death Saving Throws)

**Arquivo:** `dnd_5e_rules.py`

```python
from dnd_5e_rules import calcular_salvacao_morte

resultado = calcular_salvacao_morte(rolagem=15, sucessos=1, falhas=1)
# Retorna: {"sucesso": True, "novos_sucessos": 2, ...}

# Crítico 20: recupera 1 HP imediatamente
# Crítico 1: conta como 2 falhas
# 3 sucessos = estabiliza
# 3 falhas = morre
```

---

## 📁 Arquivos Criados/Modificados

### Novos Arquivos:
1. **`dnd_5e_rules.py`** - Módulo completo com todas as regras D&D 5e
   - Perícias, condições, tipos de dano
   - Ações de combate, cobertura, terreno
   - Funções utilitárias (salvas de morte, modificadores de dano)

### Arquivos Modificados:
1. **`ui_utils.py`** - Adicionado:
   - `PERICIAS_DND_5E` (18 perícias)
   - `PERICIAS_POR_ATRIBUTO` (mapeamento reverso)
   - `CONDICOES_DND_5E` (17 condições)
   - `TIPOS_DANO` (13 tipos)
   - `ACOES_COMBATE` (11 ações)
   - `COBERTURA_BONUS`
   - `TERRENOS`

---

## 🎯 Próximos Passos Sugeridos

### Alta Prioridade:
1. **Integrar perícias no sistema de testes** - Usar `PERICIAS_DND_5E` no `action_resolver.py`
2. **Aplicar condições em combate** - Usar `CONDICOES_DND_5E` no `combat_logic.py`
3. **Implementar tipos de dano nos inimigos** - Adicionar campo `tipo_dano` na tabela `Inimigo`

### Média Prioridade:
4. **Sistema de salvamento** - Implementar `calcular_salvacao_morte` quando HP chegar a 0
5. **Ações de combate no menu** - Criar botões para Investida, Derrubar, Ajuda, etc.
6. **Cobertura dinâmica** - Detectar automaticamente cobertura no ambiente

### Baixa Prioridade:
7. **Terreno e movimento** - Implementar custo de movimento por sala
8. **Resistências/imunidades** - Adicionar campos nos modelos `Inimigo` e `Jogador`
9. **Árvore de talentos** - Sistema de Feats opcionais

---

## 📊 Estatísticas da Implementação

| Categoria | Quantidade |
|-----------|------------|
| Perícias | 18 |
| Condições | 17 |
| Tipos de Dano | 13 |
| Ações de Combate | 11 |
| Tipos de Cobertura | 3 |
| Tipos de Terreno | 5 |

**Total de novas estruturas:** 67 elementos de regra D&D 5e

---

## 🔧 Como Usar nas Rotas Existentes

### Exemplo 1: Teste de Perícia
```python
from ui_utils import PERICIAS_DND_5E, PERICIAS_POR_ATRIBUTO

async def teste_pericia(jogador, pericia_nome):
    atributo = PERICIAS_DND_5E.get(pericia_nome, "STR")
    mod_atributo = getattr(jogador, f"mod_{atributo.lower()}", 0)
    
    # Verificar se o background dá proficiência
    from ui_utils import BACKGROUND_SKILLS
    pericias_bg = BACKGROUND_SKILLS.get(jogador.background, [])
    bonus_prof = jogador.proficiencia if pericia_nome in pericias_bg else 0
    
    total = rolar_d20() + mod_atributo + bonus_prof
    return total
```

### Exemplo 2: Aplicar Condição
```python
from ui_utils import CONDICOES_DND_5E

async def aplicar_condicao(jogador, condicao_nome):
    condicao = CONDICOES_DND_5E.get(condicao_nome)
    if not condicao:
        return False
    
    efeitos = list(jogador.status_efeitos)
    if condicao_nome not in efeitos:
        efeitos.append(condicao_nome)
        jogador.status_efeitos = efeitos
        return True
    return False
```

### Exemplo 3: Calcular Dano com Resistências
```python
from dnd_5e_rules import aplicar_modificadores_dano

async def causar_dano(alvo, dano_base, tipo_dano):
    # Obter resistências do alvo (precisa adicionar no modelo)
    resistencias = getattr(alvo, "resistencias", [])
    vulnerabilidades = getattr(alvo, "vulnerabilidades", [])
    imunidades = getattr(alvo, "imunidades", [])
    
    dano_final = aplicar_modificadores_dano(
        dano_base=dano_base,
        tipo_dano=tipo_dano,
        vulnerabilidades=vulnerabilidades,
        resistencias=resistencias,
        imunidades=imunidades
    )
    
    alvo.hp_atual -= dano_final
    return dano_final
```

---

## ✅ Validação

Todos os imports foram testados e validados:
```bash
✅ PERICIAS_DND_5E: 18 perícias
✅ CONDICOES_DND_5E: 17 condições  
✅ TIPOS_DANO: 13 tipos
✅ ACOES_COMBATE: 11 ações
✅ dnd_5e_rules.py: módulo completo funcional
```

---

**Implementado por:** Assistente de Código  
**Data:** 2025  
**Base:** D&D 5ª Edição (Sistema Básico + Expansões)
