from database import get_db_session
from models import Cena, Encontro, Inimigo, Npc, Interativo

def popular_phandelver_pt4():
    with get_db_session() as db:
        print("A iniciar mapeamento da Parte 4 de Phandelver (Caverna Onda Eco)...")

        # ==========================================
        # 1. BESTIÁRIO (Inimigos do Ato 4)
        # ==========================================
        inimigos_pt4 = [
            Inimigo(nome="Bugbear", hp_max=27, ca=16, ataque="+4", xp_recompensa=200, ouro_recompensa=15),
            Inimigo(nome="Carniçal", hp_max=22, ca=12, ataque="+4", xp_recompensa=200, ouro_recompensa=5),
            Inimigo(nome="Gosma Ocre", hp_max=45, ca=8, ataque="+4", xp_recompensa=450, ouro_recompensa=0),
            Inimigo(nome="Crânio Flamejante", hp_max=40, ca=13, ataque="+5", xp_recompensa=1100, is_boss=True, ouro_recompensa=50),
            Inimigo(nome="Mormesk (Aparição)", hp_max=45, ca=13, ataque="+6", xp_recompensa=700, is_boss=True, ouro_recompensa=150),
            Inimigo(nome="Observador", hp_max=39, ca=14, ataque="+1", xp_recompensa=700, is_boss=True, ouro_recompensa=0),
            Inimigo(nome="Aranha Negra (Nezznar)", hp_max=27, ca=11, ataque="+5", xp_recompensa=450, is_boss=True, ouro_recompensa=300),
            # Inimigos que podem já existir, mas garantimos:
            Inimigo(nome="Aranha Gigante", hp_max=26, ca=14, ataque="+5", xp_recompensa=200, ouro_recompensa=0),
            Inimigo(nome="Zumbi", hp_max=22, ca=8, ataque="+3", xp_recompensa=50, ouro_recompensa=1),
            Inimigo(nome="Esqueleto", hp_max=13, ca=13, ataque="+4", xp_recompensa=50, ouro_recompensa=0)
        ]
        
        for inimigo in inimigos_pt4:
            if not db.query(Inimigo).filter(Inimigo.nome == inimigo.nome).first():
                db.add(inimigo)

        # ==========================================
        # 2. CENAS (Caverna Onda Eco)
        # ==========================================
        cenas_pt4 = [
            Cena(
                cod_sala="onda_eco_entrada",
                nome_sala="1. Entrada da Caverna Onda Eco",
                descricao_visual="Uma caverna profunda e escura, onde o som rítmico de ondas a bater (o 'Onda Eco') ecoa de longe a cada poucos minutos. Um acampamento anão em ruínas jaz perto de um poço escuro. O corpo de Tharden Rockseeker está no chão.",
                conexoes={"oeste": "phandalin", "norte": "onda_eco_tuneis"} # O caminho de volta à vila
            ),
            Cena(
                cod_sala="onda_eco_tuneis",
                nome_sala="Túneis da Mina",
                descricao_visual="Túneis labirínticos suportados por vigas de madeira apodrecidas. O som das ondas é mais forte aqui. Esqueletos de antigas batalhas forram o chão poeirento.",
                conexoes={"sul": "onda_eco_entrada", "leste": "onda_eco_grande_caverna", "norte": "onda_eco_fungos"}
            ),
            Cena(
                cod_sala="onda_eco_fungos",
                nome_sala="Caverna dos Fungos",
                descricao_visual="O ar é espesso e tóxico. Cogumelos gigantes e tapetes de musgo luminescente verde cobrem o chão e as paredes.",
                conexoes={"sul": "onda_eco_tuneis"}
            ),
            Cena(
                cod_sala="onda_eco_grande_caverna",
                nome_sala="9. A Grande Caverna",
                descricao_visual="Um salão imenso, ladeado por escarpas. Dezenas de cadáveres antigos estão espalhados pelo chão. O cheiro de morte atrai criaturas devoradoras de carne (Carniçais).",
                conexoes={"oeste": "onda_eco_tuneis", "norte": "onda_eco_fornalha", "leste": "onda_eco_piscina"}
            ),
            Cena(
                cod_sala="onda_eco_fornalha",
                nome_sala="12. Caverna da Fornalha",
                descricao_visual="Uma enorme fornalha de fundição de adamantium domina o salão. Um crânio humano flutuante, envolto em chamas verdes, patrulha a sala, acompanhado de mortos-vivos.",
                conexoes={"sul": "onda_eco_grande_caverna", "leste": "onda_eco_aposentos"}
            ),
            Cena(
                cod_sala="onda_eco_aposentos",
                nome_sala="14. Aposentos dos Magos",
                descricao_visual="O que restou dos aposentos de luxo dos magos humanos de outrora. Uma aparição sombria (Mormesk) ergue-se do chão, sussurrando maldições antigas.",
                conexoes={"oeste": "onda_eco_fornalha", "norte": "onda_eco_forja"}
            ),
            Cena(
                cod_sala="onda_eco_forja",
                nome_sala="15. A Forja das Magias",
                descricao_visual="O lendário coração da mina! Uma fornalha crepita com fogo esmeralda que não consome combustível. Um monstro flutuante com um grande olho central (Observador) guarda a sala, insano pelo tempo.",
                conexoes={"sul": "onda_eco_aposentos"}
            ),
            Cena(
                cod_sala="onda_eco_piscina",
                nome_sala="10. Piscina Escura",
                descricao_visual="Uma lagoa profunda preenche esta caverna. A água recua violentamente e depois retorna com estrondo, causando o som que dá nome à caverna.",
                conexoes={"oeste": "onda_eco_grande_caverna", "norte": "onda_eco_templo"}
            ),
            Cena(
                cod_sala="onda_eco_templo",
                nome_sala="19. Templo de Dumathoin",
                descricao_visual="O confronto final! Um templo anão impressionante com pilares esculpidos. A escuridão parece viva aqui. O Aranha Negra (Nezznar) examina a sala, ladeado por aranhas gigantes.",
                conexoes={"sul": "onda_eco_piscina"}
            )
        ]
        
        for cena in cenas_pt4:
            if not db.query(Cena).filter(Cena.cod_sala == cena.cod_sala).first():
                db.add(cena)

        db.flush()

        # ==========================================
        # 3. ENCONTROS E NPCS
        # ==========================================
        encontros = [
            Encontro(cod_sala="onda_eco_tuneis", nome_inimigo="Gosma Ocre", quantidade=1),
            Encontro(cod_sala="onda_eco_grande_caverna", nome_inimigo="Carniçal", quantidade=7),
            Encontro(cod_sala="onda_eco_fornalha", nome_inimigo="Zumbi", quantidade=8),
            Encontro(cod_sala="onda_eco_fornalha", nome_inimigo="Crânio Flamejante", quantidade=1),
            Encontro(cod_sala="onda_eco_aposentos", nome_inimigo="Mormesk (Aparição)", quantidade=1),
            Encontro(cod_sala="onda_eco_forja", nome_inimigo="Observador", quantidade=1),
            Encontro(cod_sala="onda_eco_piscina", nome_inimigo="Bugbear", quantidade=3),
            Encontro(cod_sala="onda_eco_templo", nome_inimigo="Aranha Gigante", quantidade=4),
            Encontro(cod_sala="onda_eco_templo", nome_inimigo="Bugbear", quantidade=2),
            Encontro(cod_sala="onda_eco_templo", nome_inimigo="Aranha Negra (Nezznar)", quantidade=1)
        ]
        
        for enc in encontros:
            db.add(enc)

        npcs_ato4 = [
            Npc(
                cod_sala="onda_eco_forja",
                nome="Observador Insano",
                descricao="Uma esfera com olhos, que enlouqueceu após 500 anos de espera.",
                dialogo_base="Vocês vêm roubar os itens mágicos?! A Forja é minha para proteger! Mostrem as credenciais do Pacto de Phandelver ou morram!"
            ),
            Npc(
                cod_sala="onda_eco_templo",
                nome="Nundro Rockseeker",
                descricao="O último irmão Rockseeker. Está vivo, mas cativo do Aranha Negra num canto da sala.",
                dialogo_base="Cuidado! O Drow tem truques mágicos e ilusões! Se derrotarem esse monstro, a Forja das Magias será do nosso clã e vocês serão heróis para todo o sempre!"
            )
        ]

        for npc in npcs_ato4:
            db.add(npc)

        # ==========================================
        # 4. INTERATIVOS E LOOT ÉPICO
        # ==========================================
        bau_mormesk = Interativo(
            cod_sala="onda_eco_aposentos",
            tipo="bau",
            nome="Cofre de Mormesk",
            descricao="Um cofre de ferro carbonizado guardado pelo espírito.",
            atributo_teste="DEX",
            cd_teste=15,
            dano_falha=0,
            recompensa=["1100 pc", "160 pp", "50 PO", "Cachimbo de Prata (150 PO)"]
        )
        
        tesouro_forja = Interativo(
            cod_sala="onda_eco_forja",
            tipo="bau",
            nome="Tesouros da Forja",
            descricao="Armas mágicas repousam sobre altares impecáveis.",
            atributo_teste="INT",
            cd_teste=10,
            dano_falha=0,
            recompensa=["Maça Mágica: Portadora da Luz (+1d6 Dano Radiante)", "Peitoral: Guarda do Dragão (+1 CA)"]
        )
        
        tesouro_nezznar = Interativo(
            cod_sala="onda_eco_templo",
            tipo="bau",
            nome="Espólio do Aranha Negra",
            descricao="O saco de saque que Nezznar planeava levar.",
            atributo_teste="DEX",
            cd_teste=10,
            dano_falha=0,
            recompensa=["Cajado de Vidro-Aranha (Arma Mágica)", "130 PO", "Gemas Preciosas (200 PO)", "Chave do Templo"]
        )

        db.add_all([bau_mormesk, tesouro_forja, tesouro_nezznar])

        db.commit()
        print("✅ Parte 4 de Phandelver injetada com sucesso no banco de dados!")

if __name__ == "__main__":
    popular_phandelver_pt4()