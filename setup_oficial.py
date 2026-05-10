from database import engine, Base, get_db_session
from models import Cena, Inimigo, Encontro, Npc, Interativo

def popular_banco():
    print("🧹 Limpando o banco de dados antigo...")
    Base.metadata.drop_all(bind=engine)
    
    print("🔨 Criando novas tabelas com a arquitetura 2.0...")
    Base.metadata.create_all(bind=engine)

    with get_db_session() as db:
        print("🗺️ Criando o Mundo...")
        # ==========================================
        # 1. CENAS (SALAS)
        # ==========================================
        salas = [
            Cena(
                cod_sala="carvalhal",
                nome_sala="Vila de Carvalhal",
                descricao_visual="Uma vila rústica cercada por macieiras. Ouve-se o som de marteladas vindas da forja local. A leste, uma estrada de terra leva à ravina onde repousa a infame Cidadela Sem Sol.",
                conexoes={"leste": "cidadela_ravina"}
            ),
            Cena(
                cod_sala="cidadela_ravina",
                nome_sala="A Ravina Sombria",
                descricao_visual="Uma fenda profunda na terra. Pilares de pedra antiga despontam na escuridão. O ar é frio e cheira a mofo. Há uma porta de pedra maciça a norte.",
                conexoes={"oeste": "carvalhal", "norte": "cidadela_covil_durnn"},
                hazards=[{"tipo": "dex_save", "cd": 12, "dano": "1d4", "descricao": "Pedras soltas deslizam sob os teus pés"}]
            ),
            Cena(
                cod_sala="cidadela_covil_durnn",
                nome_sala="O Salão do Chefe Hobgoblin",
                descricao_visual="Uma câmara circular com pilares esculpidos em forma de dragão. No centro, um trono improvisado com ossos e pedaços de armadura. O ar está pesado com a presença de um mal antigo.",
                conexoes={"sul": "cidadela_ravina"}
            )
        ]
        db.add_all(salas)

        print("👹 Criando o Bestiário...")
        # ==========================================
        # 2. INIMIGOS E BOSSES
        # ==========================================
        inimigos = [
            Inimigo(
                nome="Goblin Saqueador",
                hp_max=7,
                ca=13,
                ataque="+4",
                dano="1d6+2",
                xp_recompensa=50,
                ouro_recompensa=5,
                is_boss=False
            ),
            Inimigo(
                nome="Durnn, o Senhor Hobgoblin",
                hp_max=45, # Muito HP para durar até à Fase 2
                ca=15,     # Armadura pesada
                ataque="+5",
                dano="1d8+3",
                xp_recompensa=250,
                ouro_recompensa=80,
                is_boss=True,     # A FLAG MÁGICA!
                fase_atual=1,
                loot_especial=["Poção de Cura Maior", "Espada Longa Enferrujada", "Chave do Salão"]
            )
        ]
        db.add_all(inimigos)

        print("⚔️ Posicionando Encontros...")
        # ==========================================
        # 3. ENCONTROS NAS SALAS
        # ==========================================
        encontros = [
            Encontro(
                cod_sala="cidadela_ravina",
                nome_inimigo="Goblin Saqueador",
                quantidade=2
            ),
            Encontro(
                cod_sala="cidadela_covil_durnn",
                nome_inimigo="Durnn, o Senhor Hobgoblin",
                quantidade=1,
                multiplicador_ameaca=2 # Ele conta por 2 inimigos nas rolagens de ataque
            )
        ]
        db.add_all(encontros)

        print("🧙‍♂️ Adicionando NPCs e Interativos...")
        # ==========================================
        # 4. NPCs e INTERATIVOS (Loots e Baús)
        # ==========================================
        npc_ferreiro = Npc(
            cod_sala="carvalhal",
            nome="Ferreiro de Carvalhal",
            descricao="Um anão suado com um martelo enorme.",
            dialogo_base="A estrada para a Cidadela é perigosa. Cuidado com os Goblins!",
            dialogo_item_especial="Ah, trouxeste os dentes de Goblin! Excelente!",
            item_gatilho="Dente de Goblin"
        )
        db.add(npc_ferreiro)

        bau_durnn = Interativo(
            cod_sala="cidadela_covil_durnn",
            nome="Baú de Ferro do Durnn",
            descricao="Um baú pesado trancado com um cadeado robusto.",
            tipo="bau",
            cd_teste=14,
            atributo_teste="DEX",
            recompensa=["100 Moedas de Ouro", "Anel de Proteção"],
            dano_falha=0
        )
        db.add(bau_durnn)

        db.commit()
        print("✅ Banco de Dados populado com sucesso! A aventura aguarda.")

if __name__ == "__main__":
    popular_banco()