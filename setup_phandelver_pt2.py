from database import get_db_session
from models import Cena, Encontro, Inimigo, Npc, Interativo, Missao

def popular_phandelver_pt2():
    with get_db_session() as db:
        print("A iniciar mapeamento da Parte 2 de Phandelver (Phandalin & Marcarrubras)...")

        # ==========================================
        # 1. BESTIÁRIO (Inimigos do Ato 2)
        # ==========================================
        inimigos_pt2 = [
            Inimigo(nome="Bandido Marcarrubra", hp_max=16, ca=14, ataque="+4", xp_recompensa=100, ouro_recompensa=10),
            Inimigo(nome="Esqueleto", hp_max=13, ca=13, ataque="+4", xp_recompensa=50, ouro_recompensa=0),
            Inimigo(nome="Nothic", hp_max=45, ca=15, ataque="+4", xp_recompensa=450, is_boss=True, ouro_recompensa=50),
            Inimigo(nome="Iarno Albrek (Glasstaff)", hp_max=22, ca=15, ataque="+4", xp_recompensa=200, is_boss=True, ouro_recompensa=100)
        ]
        
        for inimigo in inimigos_pt2:
            if not db.query(Inimigo).filter(Inimigo.nome == inimigo.nome).first():
                db.add(inimigo)

        # ==========================================
        # 2. CENAS (Vila de Phandalin e Mansão Tresendar)
        # ==========================================
        cenas_pt2 = [
            # --- A VILA ---
            Cena(
                cod_sala="phandalin", # O hub central (já conectado na Trilha Triboar)
                nome_sala="Vila de Phandalin",
                descricao_visual="Uma vila rústica construída sobre ruínas antigas. Estradas de terra lamacentas separam casas de madeira e pedra. Os moradores olham para ti com desconfiança. No topo da colina a leste, erguem-se as ruínas da Mansão Tresendar.",
                conexoes={
                    "norte": "provisoes_barthen", 
                    "sul": "gigante_adormecido", 
                    "leste": "mansao_tresendar", 
                    "oeste": "trilha_triboar",
                    "estalagem": "estalagem_colina",
                    "cambio": "cambio_mineiros"
                }
            ),
            Cena(
                cod_sala="estalagem_colina",
                nome_sala="Estalagem Colina de Pedra",
                descricao_visual="Uma estalagem acolhedora de pedra e madeira. O cheiro de ensopado e cerveja quente enche o ar. É um bom lugar para descansar e ouvir os rumores da cidade.",
                conexoes={"sair": "phandalin"}
            ),
            Cena(
                cod_sala="provisoes_barthen",
                nome_sala="Provisões de Barthen",
                descricao_visual="O maior posto de comércio de Phandalin. As prateleiras estão cheias de equipamento de aventura, rações e ferramentas de mineração.",
                conexoes={"sair": "phandalin"}
            ),
            Cena(
                cod_sala="cambio_mineiros",
                nome_sala="Câmbio dos Mineiros de Phandalin",
                descricao_visual="Um posto comercial bem vigiado onde os mineiros vêm pesar a sua prata e ouro. Atrás do balcão está Halia Thornton.",
                conexoes={"sair": "phandalin"}
            ),
            Cena(
                cod_sala="gigante_adormecido",
                nome_sala="Taverna Gigante Adormecido",
                descricao_visual="Uma espelunca em ruínas, frequentada pela pior escória da vila. Um grupo de rufiões com mantos vermelhos está a beber e a arranjar confusão na porta.",
                conexoes={"norte": "phandalin"}
            ),
            
            # --- O ESCONDERIJO MARCARRUBRA ---
            Cena(
                cod_sala="mansao_tresendar",
                nome_sala="Ruínas de Tresendar",
                descricao_visual="As fundações de pedra de uma antiga mansão destruída. Ao vasculhar os destroços, encontras uma escada de pedra oculta que desce para as trevas do porão.",
                conexoes={"oeste": "phandalin", "descer": "marcarrubra_porao"}
            ),
            Cena(
                cod_sala="marcarrubra_porao",
                nome_sala="1. Porão (Esconderijo Marcarrubra)",
                descricao_visual="O porão da antiga mansão. O cheiro a cerveja velha e sangue seco é forte. Existem cisternas de água e grandes barris.",
                conexoes={"subir": "mansao_tresendar", "norte": "marcarrubra_corredor", "leste": "marcarrubra_fenda"}
            ),
            Cena(
                cod_sala="marcarrubra_corredor",
                nome_sala="2. Corredor das Armadilhas",
                descricao_visual="Um longo corredor estreito, poeirento. Há sinais de que as pedras do chão no centro do corredor estão soltas.",
                conexoes={"sul": "marcarrubra_porao", "norte": "marcarrubra_barracas"}
            ),
            Cena(
                cod_sala="marcarrubra_barracas",
                nome_sala="3. Barracas dos Bandidos",
                descricao_visual="Um quarto com várias camas desarrumadas. Rufiões de manto vermelho estão sentados a jogar dados em cima de barris.",
                conexoes={"sul": "marcarrubra_corredor", "leste": "marcarrubra_criptas"}
            ),
            Cena(
                cod_sala="marcarrubra_criptas",
                nome_sala="4. Criptas Tresendar",
                descricao_visual="A temperatura cai drasticamente. Sarcófagos de pedra alinham-se nas paredes. Um frio sobrenatural permeia o ar, e ossos mexem-se nas sombras.",
                conexoes={"oeste": "marcarrubra_barracas", "sul": "marcarrubra_prisao"}
            ),
            Cena(
                cod_sala="marcarrubra_prisao",
                nome_sala="5. Celas dos Escravos",
                descricao_visual="Celas de ferro sujas. Há prisioneiros civis de Phandalin aqui, aterrorizados pelos guardas com mantos vermelhos.",
                conexoes={"norte": "marcarrubra_criptas"}
            ),
            Cena(
                cod_sala="marcarrubra_fenda",
                nome_sala="8. A Fenda",
                descricao_visual="Uma enorme fissura natural divide a caverna, exalando um cheiro a carne podre. Das sombras da ravina, um olho gigante e grotesco pisca. É um Nothic.",
                conexoes={"oeste": "marcarrubra_porao", "norte": "marcarrubra_glasstaff"}
            ),
            Cena(
                cod_sala="marcarrubra_glasstaff",
                nome_sala="12. Aposentos de Glasstaff",
                descricao_visual="Um laboratório e quarto luxuoso no meio da masmorra. O líder dos bandidos, usando um cajado de vidro brilhante, prepara-se para lançar magias.",
                conexoes={"sul": "marcarrubra_fenda"}
            )
        ]
        
        for cena in cenas_pt2:
            if not db.query(Cena).filter(Cena.cod_sala == cena.cod_sala).first():
                db.add(cena)

        db.flush()

        # ==========================================
        # 3. ENCONTROS E NPCS
        # ==========================================
        encontros = [
            Encontro(cod_sala="gigante_adormecido", nome_inimigo="Bandido Marcarrubra", quantidade=4),
            Encontro(cod_sala="marcarrubra_barracas", nome_inimigo="Bandido Marcarrubra", quantidade=3),
            Encontro(cod_sala="marcarrubra_criptas", nome_inimigo="Esqueleto", quantidade=3),
            Encontro(cod_sala="marcarrubra_prisao", nome_inimigo="Bandido Marcarrubra", quantidade=2),
            Encontro(cod_sala="marcarrubra_fenda", nome_inimigo="Nothic", quantidade=1),
            Encontro(cod_sala="marcarrubra_glasstaff", nome_inimigo="Iarno Albrek (Glasstaff)", quantidade=1)
        ]
        
        for enc in encontros:
            db.add(enc)

        npcs_vila = [
            Npc(
                cod_sala="provisoes_barthen",
                nome="Elmar Barthen",
                descricao="Um lojista magro e calvo.",
                dialogo_base="O Gundren não chegou com vocês? Isso é mau... Os bandidos Marcarrubra têm causado terror, mas a Tribo Cragmaw na floresta é um problema pior. Se encontrares Gundren e os mantimentos dele, pago-te bem."
            ),
            Npc(
                cod_sala="cambio_mineiros",
                nome="Halia Thornton",
                descricao="Uma mulher astuta que controla a economia local.",
                dialogo_base="Aquele lixo de Phandalin tem medo dos Marcarrubras. Eu não. O líder deles, Glasstaff, está a arruinar os negócios. Mata-o, traz-me as suas correspondências e dou-te 100 peças de ouro."
            ),
            Npc(
                cod_sala="marcarrubra_prisao",
                nome="Mirna Dendrar",
                descricao="Uma civil de Phandalin, presa com a sua família.",
                dialogo_base="Obrigado por nos salvares! Eles mataram o meu marido... Não tenho dinheiro, mas se fores às Ruínas de Árvore Trovão, há um colar de esmeraldas escondido na antiga loja do boticário. É teu se o encontrares!"
            )
        ]

        for npc in npcs_vila:
            db.add(npc)

        # ==========================================
        # 4. INTERATIVOS E ARMADILHAS
        # ==========================================
        armadilha_fosso = Interativo(
            cod_sala="marcarrubra_corredor",
            tipo="armadilha",
            nome="Fosso Escondido",
            descricao="O chão falso desaba para um fosso com 6 metros de profundidade.",
            atributo_teste="DEX",
            cd_teste=15,
            dano_falha=6,  # Queda de 6 metros
            recompensa=[]
        )
        
        tesouro_nothic = Interativo(
            cod_sala="marcarrubra_fenda",
            tipo="bau",
            nome="Espólio do Nothic",
            descricao="Um baú de madeira apodrecido no fundo da ravina, cheio do que ele roubou das vítimas.",
            atributo_teste="STR",
            cd_teste=10,
            dano_falha=0,
            recompensa=["160 pc", "90 pp", "1 Poção de Cura", "Scroll: Augúrio"]
        )
        
        bau_glasstaff = Interativo(
            cod_sala="marcarrubra_glasstaff",
            tipo="bau",
            nome="Baú de Glasstaff",
            descricao="Baú de carvalho aos pés da cama do mago.",
            atributo_teste="INT", # Tem que ser desarmado para não acionar magia? No original é só locked
            cd_teste=12,
            dano_falha=0,
            recompensa=["130 PO", "Scroll: Mísseis Mágicos", "Scroll: Enfeitiçar Pessoa"]
        )

        db.add_all([armadilha_fosso, tesouro_nothic, bau_glasstaff])

        db.commit()
        print("✅ Parte 2 de Phandelver injetada com sucesso no banco de dados!")

if __name__ == "__main__":
    popular_phandelver_pt2()