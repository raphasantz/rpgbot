from database import get_db_session
from models import Cena, Encontro, Inimigo, Npc, Interativo, Missao

def popular_phandelver_pt3():
    with get_db_session() as db:
        print("A iniciar mapeamento da Parte 3 de Phandelver (Ermos e Castelo Dentefino)...")

        # ==========================================
        # 1. BESTIÁRIO (Inimigos do Ato 3)
        # ==========================================
        inimigos_pt3 = [
            Inimigo(nome="Orc", hp_max=15, ca=13, ataque="+5", xp_recompensa=100, ouro_recompensa=5),
            Inimigo(nome="Ogre", hp_max=59, ca=11, ataque="+6", xp_recompensa=450, is_boss=True, ouro_recompensa=40),
            Inimigo(nome="Aranha Gigante", hp_max=26, ca=14, ataque="+5", xp_recompensa=200, ouro_recompensa=0),
            Inimigo(nome="Zumbi", hp_max=22, ca=8, ataque="+3", xp_recompensa=50, ouro_recompensa=1),
            Inimigo(nome="Mago Maligno (Hamun Kost)", hp_max=22, ca=12, ataque="+4", xp_recompensa=200, is_boss=True, ouro_recompensa=30),
            Inimigo(nome="Cultista do Dragão", hp_max=9, ca=12, ataque="+3", xp_recompensa=25, ouro_recompensa=5),
            Inimigo(nome="Dragão Verde Jovem (Venomfang)", hp_max=136, ca=18, ataque="+7", xp_recompensa=3900, is_boss=True, ouro_recompensa=500),
            Inimigo(nome="Hobgoblin", hp_max=11, ca=18, ataque="+3", xp_recompensa=100, ouro_recompensa=10),
            Inimigo(nome="Grick", hp_max=27, ca=14, ataque="+4", xp_recompensa=450, ouro_recompensa=0),
            Inimigo(nome="Urso Coruja (Owlbear)", hp_max=59, ca=13, ataque="+7", xp_recompensa=700, is_boss=True, ouro_recompensa=0),
            Inimigo(nome="Rei Grol (Bugbear)", hp_max=45, ca=16, ataque="+5", xp_recompensa=450, is_boss=True, ouro_recompensa=100),
            Inimigo(nome="Vhalak (Doppleganger)", hp_max=52, ca=14, ataque="+6", xp_recompensa=700, is_boss=True, ouro_recompensa=50)
        ]
        
        for inimigo in inimigos_pt3:
            if not db.query(Inimigo).filter(Inimigo.nome == inimigo.nome).first():
                db.add(inimigo)

        # ==========================================
        # 2. CENAS (Ermos e Castelo Dentefino)
        # ==========================================
        cenas_pt3 = [
            # --- OS ERMOS ---
            Cena(
                cod_sala="conyberry",
                nome_sala="Ruínas de Conyberry & Covil de Agatha",
                descricao_visual="A vila abandonada de Conyberry. Uma trilha na floresta leva a uma cabana tecida com galhos mortos e teias de aranha. O ar é gelado e silencioso. Este é o domínio da Banshee Agatha.",
                conexoes={"oeste": "phandalin"} # Conecta de volta à vila
            ),
            Cena(
                cod_sala="poco_coruja",
                nome_sala="Poço da Coruja Velha",
                descricao_visual="Ruínas de uma antiga torre de vigia. O cheiro de morte paira no ar. Há uma tenda vermelha montada perto de um poço escuro, e vultos cambaleantes patrulham o local.",
                conexoes={"oeste": "phandalin", "leste": "cume_wyvern"}
            ),
            Cena(
                cod_sala="cume_wyvern",
                nome_sala="Cume da Wyvern",
                descricao_visual="Uma formação rochosa escarpada. Há uma caverna cujo interior cheira a fumaça, suor e carne assada. Orcs estabeleceram um acampamento aqui.",
                conexoes={"oeste": "poco_coruja"}
            ),
            # --- ÁRVORE TROVÃO (THUNDERTREE) ---
            Cena(
                cod_sala="arvore_trovao_entrada",
                nome_sala="Ruínas de Árvore Trovão",
                descricao_visual="A antiga vila foi destruída pela erupção do Monte Hotenow. Casas de pedra sem teto estão engolidas por ervas daninhas cinzentas. Um aviso de madeira diz: 'Perigo! Homens-planta e zumbis!'",
                conexoes={"sul": "neverwinter", "leste": "arvore_trovao_boticario", "norte": "arvore_trovao_torre"}
            ),
            Cena(
                cod_sala="arvore_trovao_boticario",
                nome_sala="Antiga Loja do Boticário",
                descricao_visual="Uma casa arruinada com prateleiras apodrecidas. O teto desabou e há aranhas gigantes a tecer teias espessas entre os destroços.",
                conexoes={"oeste": "arvore_trovao_entrada"}
            ),
            Cena(
                cod_sala="arvore_trovao_torre",
                nome_sala="A Torre do Dragão",
                descricao_visual="Uma torre de pedra que milagrosamente resistiu à destruição. Um cheiro ácido de cloro e morte emana de dentro. Uma criatura colossal de escamas verdes dorme sobre um tesouro.",
                conexoes={"sul": "arvore_trovao_entrada"}
            ),
            # --- CASTELO DENTEFINO (CRAGMAW CASTLE) ---
            Cena(
                cod_sala="castelo_entrada",
                nome_sala="Castelo Dentefino (Portões)",
                descricao_visual="Um castelo em ruínas escondido na floresta. Possui sete torres danificadas. As pesadas portas de bronze estão entreabertas, revelando uma escuridão espessa no saguão.",
                conexoes={"sul": "trilha_triboar", "norte": "castelo_saguao"}
            ),
            Cena(
                cod_sala="castelo_saguao",
                nome_sala="1. Saguão do Castelo",
                descricao_visual="O salão de entrada. Há portas a norte e a leste. Entulho bloqueia a passagem oeste. Goblins montam guarda nas sombras.",
                conexoes={"sul": "castelo_entrada", "leste": "castelo_refeitorio", "norte": "castelo_santuario"}
            ),
            Cena(
                cod_sala="castelo_refeitorio",
                nome_sala="2. Refeitório Goblinóide",
                descricao_visual="O cheiro de sujeira e carne velha é avassalador. Mesas compridas estão montadas. Uma criatura medonha com tentáculos (Grick) esconde-se no teto, enquanto hobgoblins comem.",
                conexoes={"oeste": "castelo_saguao", "norte": "castelo_torre_urso"}
            ),
            Cena(
                cod_sala="castelo_torre_urso",
                nome_sala="3. Torre Destruída",
                descricao_visual="A porta desta sala está trancada por fora com uma barra pesada de madeira. Lá dentro, algo grande e furioso ruge e arranha as paredes.",
                conexoes={"sul": "castelo_refeitorio", "oeste": "castelo_santuario"}
            ),
            Cena(
                cod_sala="castelo_santuario",
                nome_sala="4. O Santuário Profanado",
                descricao_visual="Um antigo templo divino agora manchado de sangue. Estátuas sem cabeça adornam o altar. Goblins e Hobgoblins veneram divindades sombrias aqui.",
                conexoes={"sul": "castelo_saguao", "leste": "castelo_torre_urso", "norte": "castelo_aposentos"}
            ),
            Cena(
                cod_sala="castelo_aposentos",
                nome_sala="5. Aposentos do Rei Grol",
                descricao_visual="O quarto do chefe. O grande Rei Grol, um Bugbear envelhecido, discute com uma figura misteriosa (o Doppleganger). O anão Gundren Rockseeker jaz inconsciente no chão.",
                conexoes={"sul": "castelo_santuario"}
            )
        ]
        
        for cena in cenas_pt3:
            if not db.query(Cena).filter(Cena.cod_sala == cena.cod_sala).first():
                db.add(cena)

        db.flush()

        # ==========================================
        # 3. ENCONTROS E NPCS
        # ==========================================
        encontros = [
            Encontro(cod_sala="poco_coruja", nome_inimigo="Zumbi", quantidade=6),
            Encontro(cod_sala="poco_coruja", nome_inimigo="Mago Maligno (Hamun Kost)", quantidade=1),
            Encontro(cod_sala="cume_wyvern", nome_inimigo="Orc", quantidade=4),
            Encontro(cod_sala="cume_wyvern", nome_inimigo="Ogre", quantidade=1),
            Encontro(cod_sala="arvore_trovao_entrada", nome_inimigo="Zumbi", quantidade=4),
            Encontro(cod_sala="arvore_trovao_boticario", nome_inimigo="Aranha Gigante", quantidade=2),
            Encontro(cod_sala="arvore_trovao_torre", nome_inimigo="Dragão Verde Jovem (Venomfang)", quantidade=1),
            
            # Castelo Dentefino
            Encontro(cod_sala="castelo_saguao", nome_inimigo="Goblin", quantidade=3),
            Encontro(cod_sala="castelo_refeitorio", nome_inimigo="Hobgoblin", quantidade=4),
            Encontro(cod_sala="castelo_refeitorio", nome_inimigo="Grick", quantidade=1),
            Encontro(cod_sala="castelo_torre_urso", nome_inimigo="Urso Coruja (Owlbear)", quantidade=1),
            Encontro(cod_sala="castelo_santuario", nome_inimigo="Hobgoblin", quantidade=3),
            Encontro(cod_sala="castelo_aposentos", nome_inimigo="Rei Grol (Bugbear)", quantidade=1),
            Encontro(cod_sala="castelo_aposentos", nome_inimigo="Vhalak (Doppleganger)", quantidade=1)
        ]
        
        for enc in encontros:
            db.add(enc)

        npcs_ato3 = [
            Npc(
                cod_sala="conyberry",
                nome="Agatha a Banshee",
                descricao="Um espírito fantasmagórico de uma donzela élfica, assustadora mas que pode ser apaziguada com respeito (e presentes).",
                dialogo_base="Mortais tolos... O que vos traz ao meu domínio gélido? Se procuram o grimório do mago, ele foi levado. Se procuram o mapa da Caverna Onda Eco, os Goblins o têm."
            ),
            Npc(
                cod_sala="castelo_aposentos",
                nome="Gundren Rockseeker",
                descricao="O anão que vos contratou. Está muito magoado e semiconsciente.",
                dialogo_base="Pelos Deuses, vocês encontraram-me! O Rei Grol vendeu o mapa da Caverna Onda Eco para aquele monstro de oito patas, o Aranha Negra! Temos de ir para a Caverna Onda Eco, ou a Forja das Magias será perdida para sempre!"
            )
        ]

        for npc in npcs_ato3:
            db.add(npc)

        # ==========================================
        # 4. INTERATIVOS
        # ==========================================
        colar_mirna = Interativo(
            cod_sala="arvore_trovao_boticario",
            tipo="bau",
            nome="Esconderijo do Boticário",
            descricao="Uma caixa oca disfarçada num pilar.",
            atributo_teste="INT",
            cd_teste=12,
            dano_falha=0,
            recompensa=["Colar de Esmeraldas (Missão da Mirna)"]
        )
        
        tesouro_rei_grol = Interativo(
            cod_sala="castelo_aposentos",
            tipo="bau",
            nome="Baú de Grol",
            descricao="O tesouro escondido sob a cama do rei.",
            atributo_teste="DEX",
            cd_teste=15,
            dano_falha=0,
            recompensa=["220 pp", "160 PO", "3 Poções de Cura", "Mapa de Phandalin"]
        )

        db.add_all([colar_mirna, tesouro_rei_grol])

        db.commit()
        print("✅ Parte 3 de Phandelver injetada com sucesso no banco de dados!")

if __name__ == "__main__":
    popular_phandelver_pt3()