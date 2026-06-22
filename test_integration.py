#!/usr/bin/env python3
"""
Testes de integração — Difficulty Scaling + Loot Split + XP Integral.
Valida que TODAS as mecânicas foram aplicadas corretamente no código.
"""
import ast
import re
import sys

PASS = 0
FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}")
        if detail:
            print(f"     → {detail}")


# =====================================================================
# 1. GAME_HELPERS.PY — Funções novas existem
# =====================================================================
print("\n▸ MÓDULO 1: game_helpers.py — Funções novas")
print("-" * 50)

gh = open("/home/mesanerd/game_helpers.py").read()

check("get_difficulty_factor() existe",
      "def get_difficulty_factor" in gh)

check("split_gold() existe",
      "def split_gold" in gh)

check("SCALING_TABLE definido",
      "SCALING_TABLE" in gh)

check("SCALING_TABLE tem chaves 1-5",
      all(f"{i}: 0." in gh or f"{i}: 1." in gh for i in range(1, 6)))

check("get_difficulty_factor retorna float",
      "def get_difficulty_factor(num_players: int) -> float" in gh)

check("split_gold retorna dict",
      "def split_gold(total_gold: int, num_players: int) -> dict" in gh)

check("split_gold lida com remainder",
      "remainder" in gh)

check("get_difficulty_factor lida com party=0",
      "num_players <= 0" in gh)


# =====================================================================
# 2. ACTION_RESOLVER.PY — Imports corretos
# =====================================================================
print("\n▸ MÓDULO 2: action_resolver.py — Imports")
print("-" * 50)

ar = open("/home/mesanerd/action_resolver.py").read()

check("Importa get_difficulty_factor de game_helpers",
      "get_difficulty_factor" in ar and "from game_helpers import" in ar)

check("Importa split_gold de game_helpers",
      "split_gold" in ar and "from game_helpers import" in ar)


# =====================================================================
# 3. ACTION_RESOLVER.PY — Difficulty Scaling no combate
# =====================================================================
print("\n▸ MÓDULO 3: action_resolver.py — Difficulty Scaling")
print("-" * 50)

check("Chama get_difficulty_factor no início do combate",
      "get_difficulty_factor(num_players)" in ar)

check("Query para contar jogadores vivos da party",
      "JogadorWeb.party_id == campanha.party_id" in ar
      and "hp_atual > 0" in ar)

check("Qty escalada com math.ceil",
      "qty_scaled = max(1, math.ceil(encontro.quantidade * factor))" in ar)

check("HP escalado com qty_scaled",
      "hp_grupo = math.ceil(hp_max_inimigo * qty_scaled)" in ar)

check("Scaling só aplica na primeira vez (estado check)",
      "chave_hp not in estado" in ar)


# =====================================================================
# 4. ACTION_RESOLVER.PY — Loot Split pós-combate
# =====================================================================
print("\n▸ MÓDULO 4: action_resolver.py — Loot Split")
print("-" * 50)

check("XP dado para TODOS os jogadores (loop)",
      "for j in jogadores_party:" in ar and "j.xp += xp_total" in ar)

check("Gold usa split_gold()",
      "gold_split = split_gold(ouro_total, num_players)" in ar)

check("Gold distribuído por idx no loop",
      "for idx, j in enumerate(jogadores_party):" in ar
      and "gold_split.get(idx" in ar)

check("Narrativa menciona split quando >1 jogador",
      "num_players > 1" in ar and "split entre" in ar)

check("Level-up checado para TODOS os jogadores",
      "for j in jogadores_party:" in ar and "aplicar_level_up(j)" in ar)

check("Itens ficam com executor (não splitado)",
      "adicionar_ao_inventario(jogador, loot)" in ar)


# =====================================================================
# 5. PYGAME_UI.PY — Desktop sem scaling (single-player)
# =====================================================================
print("\n▸ MÓDULO 5: pygame_ui.py — Desktop")
print("-" * 50)

pu = open("/home/mesanerd/pygame_ui.py").read()

check("Comentário: desktop é single-player",
      "Desktop é single-player" in pu)

check("Desktop NÃO aplica difficulty scaling",
      "get_difficulty_factor" not in pu)

check("Desktop mantém HP original (sem scaling)",
      'hp_max"] * enc["quantidade"]' in pu)

check("Desktop usa 100% loot (mensagem atualizada)",
      "Recebes" in pu)


# =====================================================================
# 6. CONSISTÊNCIA — Regras D&D 5e
# =====================================================================
print("\n▸ MÓDULO 6: Consistência — Regras D&D 5e")
print("-" * 50)

check("XP NÃO é dividido (integral para todos)",
      "j.xp += xp_total" in ar)

check("Gold É dividido (split igual)",
      "gold_split = split_gold" in ar)

check("Itens ficam com quem executou (físico)",
      "adicionar_ao_inventario(jogador, loot)" in ar)

check("Loot de sala (vasculhar) mantém individual",
      "adicionar_ao_inventario(jogador, cena.loot_fixo)" in ar)


# =====================================================================
# 7. INTEGRIDADE — Nenhuma referência quebrada
# =====================================================================
print("\n▸ MÓDULO 7: Integridade — Referências")
print("-" * 50)

# Verificar que as funções são chamadas corretamente
check("split_gold recebe (total, num_players)",
      "split_gold(ouro_total, num_players)" in ar)

check("get_difficulty_factor recebe (num_players)",
      "get_difficulty_factor(num_players)" in ar)

# Verificar que math está importado
check("math importado em action_resolver.py",
      "import math" in ar)

# Verificar que func está importado (para COUNT query)
check("func importado em action_resolver.py",
      "from sqlalchemy import func" in ar or "func" in ar.split("from sqlalchemy")[1][:200] if "from sqlalchemy" in ar else False)

# Verificar que math está importado em game_helpers.py
check("math importado em game_helpers.py",
      "import math" in gh)


# =====================================================================
# 8. CENÁRIOS MATEMÁTICOS
# =====================================================================
print("\n▸ MÓDULO 8: Validação Matemática")
print("-" * 50)

# Importar as funções reais
sys.path.insert(0, "/home/mesanerd")
from game_helpers import get_difficulty_factor, split_gold

# Difficulty factors
check("Party 1 → fator 0.40",
      get_difficulty_factor(1) == 0.40)
check("Party 3 → fator 0.80",
      get_difficulty_factor(3) == 0.80)
check("Party 5 → fator 1.20",
      get_difficulty_factor(5) == 1.20)
check("Party 0 → fallback 0.40",
      get_difficulty_factor(0) == 0.40)

# Gold split
s1 = split_gold(100, 1)
check("1 jogador, 100 PO → recebe 100",
      s1[0] == 100)

s2 = split_gold(100, 2)
check("2 jogadores, 100 PO → cada um 50",
      s2[0] == 50 and s2[1] == 50)

s3 = split_gold(100, 3)
check("3 jogadores, 100 PO → 34+33+33 (remainder pro executor)",
      s3[0] == 34 and s3[1] == 33 and s3[2] == 33)

s5 = split_gold(100, 5)
check("5 jogadores, 100 PO → cada um 20",
      all(v == 20 for v in s5.values()))

# Nenhum PO perdido
for n in range(1, 11):
    shares = split_gold(100, n)
    total = sum(shares.values())
    if total != 100:
        check(f"Split {n} jogadores: total = {total} (esperado 100)", False)
        break
else:
    check("Nenhum PO perdido em splits de 1-10 jogadores", True)


# =====================================================================
# RESULTADO
# =====================================================================
print()
print("=" * 50)
total = PASS + FAIL
print(f"  RESULTADO: {PASS}/{total} testes passaram")
if FAIL == 0:
    print("  ✅ TODAS AS MECÂNICAS APLICADAS CORRETAMENTE")
else:
    print(f"  ❌ {FAIL} teste(s) falharam")
print("=" * 50)
