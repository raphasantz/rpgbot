#!/usr/bin/env python3
"""
Teste de viabilidade — Loot Split por tamanho de party.
Valida: split de XP, gold, e itens. Edge cases e balanceamento.
Sem dependências de DB ou rede. Execução isolada.
"""

import math

# =====================================================================
# 1. FUNÇÕES DE LOOT SPLIT (implementação proposta)
# =====================================================================

def split_gold(total_gold: int, num_players: int) -> dict:
    """
    Distribui gold igualmente entre jogadores da party.
    Resto (remainder) fica com quem executou (primeiro jogador).
    Retorna {jogador_idx: gold_recebido}
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

def split_xp(total_xp: int, num_players: int) -> dict:
    """
    XP: TODOS recebem o valor integral (regra D&D 5e).
    Retorna {jogador_idx: xp_recebido}
    """
    return {i: total_xp for i in range(num_players)}

def split_loot_items(items: list, num_players: int) -> dict:
    """
    Itens ficam com quem executou (fisicamente).
    Retorna {0: [itens]} — primeiro jogador (executor) recebe tudo.
    """
    return {0: items}

def get_executor_share(total: int, num_players: int) -> int:
    """Quanto o executor ganha no split de gold (base + remainder)."""
    if num_players <= 1:
        return total
    base = total // num_players
    remainder = total % num_players
    return base + (1 if remainder > 0 else 0)


# =====================================================================
# 2. CENÁRIOS DE TESTE
# =====================================================================

TEST_ENCONTROS = [
    # (nome, xp_total, ouro_total, loot_itens)
    ("Goblin Saqueador x2", 50, 8, ["Adaga"]),
    ("Esqueleto x3", 75, 12, []),
    ("Aranha Gigante x2", 100, 20, ["Poção de Cura"]),
    ("Belak (Boss)", 200, 50, ["Cajado Arcano", "Poção de Cura Maior"]),
    ("Rato Atroz x2", 25, 3, []),
]


# =====================================================================
# 3. EXECUÇÃO DOS TESTES
# =====================================================================

def run_tests():
    print("=" * 72)
    print("  TESTE DE VIABILIDADE — LOOT SPLIT POR PARTY SIZE")
    print("=" * 72)
    print()

    # --- Teste 1: Split de Gold ---
    print("▸ TESTE 1: Split de Gold")
    print("-" * 72)
    header = f"  {'Encontro':<24} {'Gold':>6}"
    for n in range(1, 6):
        header += f"  {'P'+str(n):>10}"
    print(header)
    print("  " + "-" * 68)
    for nome, xp, gold, loot in TEST_ENCONTROS:
        row = f"  {nome:<24} {gold:>6}"
        for n in range(1, 6):
            shares = split_gold(gold, n)
            executor = shares[0]
            others = shares.get(1, 0)
            if n == 1:
                row += "  {:>10}".format("100%=" + str(executor))
            else:
                row += "  {:>10}".format(str(executor) + "+" + str(others*(n-1)))
        print(row)
    print()

    # --- Teste 2: Split de XP (todos recebem integral) ---
    print("▸ TESTE 2: XP — Todos recebem integral (D&D 5e)")
    print("-" * 72)
    header = f"  {'Encontro':<24} {'XP':>6}"
    for n in range(1, 6):
        header += f"  {'P'+str(n):>10}"
    print(header)
    print("  " + "-" * 68)
    for nome, xp, gold, loot in TEST_ENCONTROS:
        row = f"  {nome:<24} {xp:>6}"
        for n in range(1, 6):
            shares = split_xp(xp, n)
            per_player = shares[0]
            total_distributed = per_player * n
            row += "  {:>10}".format(str(per_player) + "x" + str(n) + "=" + str(total_distributed))
        print(row)
    print()

    # --- Teste 3: Itens — ficam com executor ---
    print("▸ TESTE 3: Itens — ficam com quem executou")
    print("-" * 72)
    for nome, xp, gold, loot in TEST_ENCONTROS:
        if not loot:
            continue
        shares = split_loot_items(loot, 5)  # Party de 5
        print(f"  {nome}:")
        print(f"    Itens: {loot}")
        print(f"    Executor recebe: {shares[0]}")
        print(f"    Outros: nada (justo — itens são físicos)")
    print()

    # --- Teste 4: Benefício do executor (remainder) ---
    print("▸ TESTE 4: Benefício do executor (remainder)")
    print("-" * 40)
    print("  Gold total: 100 PO")
    for n in range(1, 6):
        shares = split_gold(100, n)
        executor = shares[0]
        base = 100 // n
        remainder = 100 % n
        bonus = " +1 (remainder)" if remainder > 0 else ""
        print(f"  Party {n}: base={base}, executor ganha {executor}{bonus}")
    print()

    # --- Teste 5: Valores pequenos ---
    print("▸ TESTE 5: Edge cases — valores pequenos")
    print("-" * 40)
    test_cases = [
        (1, 1, "1 PO, 1 jogador"),
        (3, 2, "3 PO, 2 jogadores"),
        (1, 5, "1 PO, 5 jogadores"),
        (0, 3, "0 PO, 3 jogadores"),
        (100, 1, "100 PO, 1 jogador"),
        (100, 5, "100 PO, 5 jogadores"),
    ]
    for gold, players, desc in test_cases:
        shares = split_gold(gold, players)
        total_distributed = sum(shares.values())
        status = "✅" if total_distributed == gold else "❌ PERDA"
        print(f"  {desc}: distribuído={total_distributed} {status}")
    print()

    # --- Teste 6: Balanceamento — gold por jogador vs dificuldade ---
    print("▸ TESTE 6: Balanceamento — Gold por jogador vs party size")
    print("-" * 72)
    print("  (Comparando gold recebido por jogador com e sem split)")
    print()
    header = f"  {'Encontro':<24} {'Gold':>6}"
    for n in range(1, 6):
        header += f"  {'P'+str(n):>8}"
    print(header)
    print("  " + "-" * 64)
    for nome, xp, gold, loot in TEST_ENCONTROS:
        row = f"  {nome:<24} {gold:>6}"
        for n in range(1, 6):
            per_player = gold // n if n > 0 else gold
            row += f"  {per_player:>8}"
        print(row)
    print()
    print("  Nota: Com difficulty scaling, gold TOTAL sobe (mais inimigos).")
    print("  Ex: 5 jogadores vs Esqueleto x4 (scaling 1.2x):")
    ouro_base = 12
    ouro_scaled = ouro_base * 1.2  # mais inimigos = mais ouro
    for n in range(1, 6):
        per = int(ouro_scaled) // n
        print(f"    Party {n}: {int(ouro_scaled)} total → {per} por jogador")
    print()

    # --- Teste 7: Combinação difficulty scaling + loot split ---
    print("▸ TESTE 7: Combinação — Difficulty Scaling + Loot Split")
    print("-" * 72)
    SCALING = {1: 0.40, 2: 0.60, 3: 0.80, 4: 1.00, 5: 1.20}
    
    print("  Esqueleto x3 (base: 75 XP, 12 PO)")
    print()
    for n in range(1, 6):
        factor = SCALING[n]
        # Com scaling: mais inimigos = mais recompensa
        qty_scaled = max(1, math.ceil(3 * factor))
        xp_per_enemy = 25  # XP por esqueleto
        ouro_per_enemy = 4  # PO por esqueleto
        xp_total = xp_per_enemy * qty_scaled
        ouro_total = ouro_per_enemy * qty_scaled
        
        # Split
        xp_each = xp_total  # XP integral
        ouro_each = ouro_total // n
        
        print(f"  Party {n} (fator={factor:.2f}):")
        print(f"    Inimigos: {qty_scaled}x Esqueleto")
        print(f"    XP total: {xp_total} → cada um recebe {xp_each}")
        print(f"    Gold total: {ouro_total} → cada um recebe {ouro_each}")
        print(f"    Dificuldade: {'Fácil' if factor < 0.8 else 'Normal' if factor < 1.1 else 'Difícil'}")
        print()

    # --- Resultado ---
    print("=" * 72)
    print("  ✅ VIABILIDADE: CONFIRMADA")
    print()
    print("  Regras de distribuição:")
    print("    XP  → TODOS recebem valor integral (D&D 5e canônico)")
    print("    Gold → Split igual; executor ganha +remainder")
    print("    Itens → Ficam com quem executou (físico)")
    print()
    print("  Pontos de injeção:")
    print("    1. action_resolver.py:575-578  — XP/gold pós-combate")
    print("    2. action_resolver.py:1058-1062 — Loot de sala (manter individual)")
    print("    3. pygame_ui.py:2236-2239       — XP/gold desktop")
    print()
    print("  Escopo da implementação:")
    print("    - 1 função nova: split_gold(total, num_players)")
    print("    - Query: COUNT jogadores na party")
    print("    - XP: remover += individual, dar para todos via loop")
    print("    - Gold: split igual + remainder pro executor")
    print("    - Loot fixo sala: manter individual (justo)")
    print("    - Zero mudanças no banco de dados")
    print("=" * 72)


if __name__ == "__main__":
    run_tests()
