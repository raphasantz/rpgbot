#!/usr/bin/env python3
"""
Seed de encontros (monstros por sala) para o MezzaRPG.
Mapeia TODAS as salas de masmorra com seus respectivos inimigos,
baseado na Cidadela Sem Sol e Phandelver.

Rode: python seed_encontros.py
"""
from modelos_web import SessionLocal, Encontro, Inimigo, Cena
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

# ════════════════════════════════════════════════════════════════════════
# MAPEAMENTO: (cod_sala, nome_inimigo_exato_do_bestiario, quantidade, is_boss)
# Baseado nas descrições das salas e na aventura oficial
# ════════════════════════════════════════════════════════════════════════

ENCONTROS = [
    # ── CIDADELA SEM SOL (cidadela_0 a cidadela_56) ──────────────────
    # Entrada e ruínas superiores
    ("cidadela_0", "Rato da Caverna", 4, False),        # Ravina escura - ratos
    ("cidadela_1", "Rato Atroz", 3, False),              # Parapeito - ratos na entrada
    # cidadela_2: Escadas sinuosas - passagem, sem combate
    ("cidadela_3", "Goblin", 3, False),                   # Pátio em ruínas
    ("cidadela_4", "Goblin Saqueador", 3, False),         # Torre em ruínas - goblins mortos
    ("cidadela_5", "Esqueleto", 2, False),                # Câmara secreta - esqueletos elfos
    # cidadela_6: Porta trancada - sem combate
    # cidadela_7: Globo musical - sem combate
    # cidadela_8: Placas de pressão (armadilha) - sem combate
    # cidadela_9: Enigma do dragão - sem combate
    ("cidadela_10", "Esqueleto", 3, False),              # Guarda de honra - guardas mortos
    # cidadela_11: Inscrições - sem combate
    ("cidadela_12", "Sacerdote do Dragão (Troll)", 1, True),  # Tumba - BOSS troll
    # cidadela_13: Câmara vazia - sem combate
    ("cidadela_14", "Mephit da Água", 1, False),         # Fonte encantada
    # cidadela_15: Meepo (NPC kobold) - sem combate direto
    ("cidadela_16", "Kobold Sentinela", 4, False),       # Kobolds sentinelas
    ("cidadela_17", "Rato Atroz", 3, False),             # Despensa do dragão - ratos
    # cidadela_18: Goblins prisioneiros - não combatem (acorrentados)
    ("cidadela_19", "Kobold Sentinela", 3, False),       # Salão dos dragões
    ("cidadela_20", "Kobold Sentinela", 4, False),       # Colônia kobold
    ("cidadela_21", "Yusdrayl", 1, True),                # Trono do dragão - BOSS Yusdrayl

    # Subterrâneos da Cidadela (áreas 22-29)
    ("cidadela_22", "Rato da Caverna", 3, False),        # Aposento vazio
    ("cidadela_23", "Esqueleto", 2, False),              # Acesso subterrâneo
    ("cidadela_24", "Esqueleto", 2, False),              # Corredor armadilhado
    # cidadela_25: Vazio - sem combate
    # cidadela_26: Fonte seca - sem combate
    ("cidadela_27", "Cultista do Dragão", 3, False),     # Santuário
    ("cidadela_28", "Rato Atroz", 4, False),             # Celas infestadas
    # cidadela_29: Armadilha desativada - sem combate

    # Território Goblin (áreas 30-41)
    ("cidadela_30", "Goblin", 3, False),                  # Parede goblin
    ("cidadela_31", "Goblin Arqueiro", 2, False),         # Corredor de estrepes
    ("cidadela_32", "Goblin Saqueador", 2, False),        # Portão goblin
    ("cidadela_33", "Hobgoblin", 2, False),               # Treinamento
    ("cidadela_34", "Durnn, Chefe Hobgoblin", 1, True),   # Salão do chefe - BOSS Durnn
    ("cidadela_35", "Goblin", 4, False),                  # Paliçada goblin
    ("cidadela_36", "Goblin Arqueiro", 3, False),         # Guarda goblin
    ("cidadela_37", "Goblin", 2, False),                  # Sala de troféus
    ("cidadela_38", "Goblin Saqueador", 3, False),        # Salão dos goblins
    ("cidadela_39", "Goblin", 2, False),                  # Despensa goblin
    # cidadela_40: Salão do fosso - armadilha, sem monstro
    ("cidadela_41", "Hobgoblin", 3, False),               # Salão principal

    # Bosque de Belak (áreas 42-56)
    ("cidadela_42", "Ramo Seco", 3, False),               # Entrada do bosque
    ("cidadela_43", "Ramo Seco", 2, False),               # Bifurcação
    ("cidadela_44", "Fungo Violeta", 2, False),           # Bosque de fungos
    ("cidadela_45", "Fungo Violeta", 1, False),           # O Cultivador
    ("cidadela_46", "Ramo Seco", 3, False),               # Caverna de caça
    ("cidadela_47", "Cultista do Dragão", 2, False),      # Laboratório
    ("cidadela_48", "Ramo Seco", 2, False),               # Galeria de mato
    ("cidadela_49", "Cultista do Dragão", 3, False),      # Aposentos
    ("cidadela_50", "Fungo Violeta", 2, False),           # Jardim sombrio
    ("cidadela_51", "Ramo Seco", 2, False),               # Gruta de ervas
    ("cidadela_52", "Fungo Violeta", 3, False),           # Caverna de esporos
    ("cidadela_53", "Cultista do Dragão", 2, False),      # Bosque adormecido
    ("cidadela_54", "Ramo Seco", 2, False),               # Bosque do crepúsculo
    ("cidadela_55", "Fungo Violeta", 1, False),           # Raízes antigas
    ("cidadela_56", "Belak, o Proscrito (Druida)", 1, True),  # BOSS FINAL: Árvore Gulthias

    # ── TRILHA TRIBOAR E ESCONDERIJO DE KLARG ────────────────────────
    ("trilha_triboar", "Goblin", 4, False),               # Emboscada na trilha
    ("esconderijo_passagem", "Goblin Arqueiro", 2, False), # Passagem dos goblins
    ("esconderijo_lobos", "Lobo", 2, False),              # Poço dos lobos
    ("esconderijo_lobos", "Ripper (Lobo do Klarg)", 1, False), # Ripper com os lobos
    ("esconderijo_covil", "Goblin Saqueador", 3, False),  # Covil dos goblins
    ("esconderijo_klarg", "Klarg", 1, True),              # BOSS: Klarg o Bugbear
    ("esconderijo_klarg", "Goblin", 2, False),            # Goblins com Klarg

    # ── PHANDALIN (vila — sem encontros hostis) ─────────────────────
    # phandalin: vila segura
    # estalagem_colina: estalagem segura
    # provisoes_barthen: loja segura
    # cambio_mineiros: troca segura

    # ── ESCONDERIJO MARCARRUBRA ──────────────────────────────────────
    ("marcarrubra_porao", "Bandido Marcarrubra", 3, False),  # Porão
    ("marcarrubra_corredor", "Bandido Marcarrubra", 2, False),# Corredor das armadilhas
    ("marcarrubra_barracas", "Bandido Marcarrubra", 4, False),# Barracas dos bandidos
    ("marcarrubra_criptas", "Zumbi", 3, False),              # Criptas Tresendar
    ("marcarrubra_prisao", "Bandido Marcarrubra", 2, False), # Celas dos escravos
    ("marcarrubra_fenda", "Nothic", 1, False),               # A Fenda - Nothic
    ("marcarrubra_glasstaff", "Iarno Albrek (Glasstaff)", 1, True), # BOSS: Glasstaff

    # ── CONYBERRY E AGATHA ──────────────────────────────────────────
    # conyberry: Agatha é NPC (não hostil)

    # ── CUME DA WYVERN ──────────────────────────────────────────────
    ("cume_wyvern", "Dragão Verde Jovem (Venomfang)", 1, True), # BOSS OPCIONAL: Dragão Verde

    # ── CASTELO DENTEFINO ───────────────────────────────────────────
    ("castelo_saguao", "Orc", 4, False),                  # Saguão do castelo
    ("castelo_refeitorio", "Orc", 3, False),              # Refeitório goblinóide
    ("castelo_refeitorio", "Ogre", 1, False),             # Ogre no refeitório
    ("castelo_torre_urso", "Urso Coruja (Owlbear)", 1, False), # Torre destruída
    ("castelo_santuario", "Cultista do Dragão", 4, False),# Santuário profanado
    ("castelo_aposentos", "Rei Grol (Bugbear)", 1, True), # BOSS: Rei Grol
    ("castelo_aposentos", "Bugbear", 2, False),           # Bugbears com Rei Grol

    # ── CAVERNA ONDA ECO (mina perdida de Phandelver) ───────────────
    ("onda_eco_fungos", "Gosma Ocre", 1, False),          # Caverna dos fungos
    ("onda_eco_fungos", "Fungo Violeta", 2, False),       # Fungos na caverna
    ("onda_eco_grande_caverna", "Aranha Gigante", 2, False), # Grande caverna
    ("onda_eco_fornalha", "Crânio Flamejante", 2, False), # Caverna da fornalha
    ("onda_eco_aposentos", "Mormesk (Aparição)", 1, False), # Aposentos dos magos
    ("onda_eco_forja", "Observador", 1, True),            # BOSS: Observador Insano
    ("onda_eco_templo", "Aranha Negra (Nezznar)", 1, True), # BOSS FINAL: Aranha Negra

    # ── ESTRADA VELHA (entre Carvalhal e Cidadela) ──────────────────
    ("estrada_velha", "Lobo", 2, False),                  # Lobos na estrada
]


def seed_encontros():
    db = SessionLocal()
    try:
        # Verificar quais salas existem
        salas_db = {s.cod_sala for s in db.execute(select(Cena)).scalars().all()}
        # Verificar quais inimigos existem
        inimigos_db = {i.nome for i in db.execute(select(Inimigo)).scalars().all()}

        adicionados = 0
        pulados = 0
        ja_existiam = 0

        for cod_sala, nome_inimigo, quantidade, is_boss in ENCONTROS:
            # Verificar se a sala existe
            if cod_sala not in salas_db:
                print(f"⚠️  Sala '{cod_sala}' não existe no banco — pulando")
                pulados += 1
                continue

            # Verificar se o inimigo existe no bestiário
            if nome_inimigo not in inimigos_db:
                print(f"⚠️  Inimigo '{nome_inimigo}' não existe no bestiário — pulando")
                pulados += 1
                continue

            # Verificar se o encontro já existe
            existe = db.execute(select(Encontro).filter(
                Encontro.cod_sala == cod_sala,
                Encontro.nome_inimigo == nome_inimigo,
            )).scalars().first()

            if existe:
                ja_existiam += 1
                continue

            # Marcar is_boss no inimigo se for boss
            if is_boss:
                inimigo = db.execute(select(Inimigo).filter(
                    Inimigo.nome == nome_inimigo
                )).scalars().first()
                if inimigo and not inimigo.is_boss:
                    inimigo.is_boss = True

            db.add(Encontro(
                cod_sala=cod_sala,
                nome_inimigo=nome_inimigo,
                quantidade=quantidade,
                condicao_aparecimento="sempre",
                ativo=True,
                multiplicador_ameaca=1,
            ))
            adicionados += 1
            boss_tag = " 👑 BOSS" if is_boss else ""
            print(f"  ✅ {cod_sala:25s} → {nome_inimigo} x{quantidade}{boss_tag}")

        db.commit()
        print(f"\n{'='*60}")
        print(f"🎉 Seed de encontros completo!")
        print(f"   Adicionados: {adicionados}")
        print(f"   Já existiam: {ja_existiam}")
        print(f"   Pulados:     {pulados}")
        print(f"   Total mapeado: {len(ENCONTROS)} encontros")

    except SQLAlchemyError as e:
        db.rollback()
        print(f"❌ Erro (SQLAlchemy): {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_encontros()
