from database import engine, Base, get_db_session
from models import Cena, Inimigo, Encontro, Npc, Interativo

def popular_banco():
    print("🧹 Limpando a masmorra antiga...")
    Base.metadata.drop_all(bind=engine)
    
    print("🔨 Forjando A Cidadela Sem Sol Completa (Áreas 0 a 56)...")
    Base.metadata.create_all(bind=engine)

    with get_db_session() as db:
        print("🗺️ Mapeando as 56 Salas da Cidadela e do Bosque...")
        
        # Estrutura: (codigo, nome, descrição, conexoes)
        salas_dados = [
            ("carvalhal", "Vila de Carvalhal", "Vila rústica onde a aventura começa.", {"norte": "cidadela_0"}),
            ("cidadela_0", "A Ravina Escura (Área 0)", "Uma fenda profunda. Há uma corda descendo.", {"sul": "carvalhal", "descer": "cidadela_1"}),
            ("cidadela_1", "Parapeito (Área 1)", "Parapeito de areia no golfo subterrâneo.", {"subir": "cidadela_0", "descer": "cidadela_2"}),
            ("cidadela_2", "Escadas Sinuosas (Área 2)", "Lances de escadas escorregadias.", {"subir": "cidadela_1", "descer": "cidadela_3"}),
            ("cidadela_3", "Pátio em Ruínas (Área 3)", "Pátio cercado por alvenaria e entulho.", {"subir": "cidadela_2", "oeste": "cidadela_4"}),
            ("cidadela_4", "Torre em Ruínas (Área 4)", "Goblins mortos espalhados no granito rachado.", {"leste": "cidadela_3", "norte": "cidadela_15", "oeste": "cidadela_6", "segredo": "cidadela_5"}),
            ("cidadela_5", "Pequena Câmara Secreta (Área 5)", "Esqueletos de antigos arqueiros elfos.", {"segredo": "cidadela_4"}),
            ("cidadela_6", "Antiga Passagem (Área 6)", "Porta de pedra trancada em formato de dragão.", {"leste": "cidadela_4", "oeste": "cidadela_7"}),
            ("cidadela_7", "Galeria das Notas (Área 7)", "Um globo cristalino azul toca uma música ensurdecedora.", {"leste": "cidadela_6", "oeste": "cidadela_8"}),
            ("cidadela_8", "Placas de Pressão (Área 8)", "Corredor com ar rarefeito e poeira.", {"leste": "cidadela_7", "oeste": "cidadela_9"}),
            ("cidadela_9", "O Enigma do Dragão (Área 9)", "Escultura de dragão em mármore que dita enigmas.", {"leste": "cidadela_8", "oeste": "cidadela_10"}),
            ("cidadela_10", "Guarda de Honra (Área 10)", "Poço escuro e cheio de estacas separa o portal.", {"leste": "cidadela_9", "pular": "cidadela_12", "segredo": "cidadela_11"}),
            ("cidadela_11", "Sala Secreta (Área 11)", "Inscrições sobre o enterro do Sacerdote do Dragão.", {"norte": "cidadela_10", "descer": "cidadela_12"}),
            ("cidadela_12", "Tumba do Sacerdote (Área 12)", "Luz verde ilumina o sarcófago de mármore maciço.", {"pular": "cidadela_10", "subir": "cidadela_11"}),
            ("cidadela_13", "Câmara Vazia (Área 13)", "Câmara vazia repleta de escombros.", {"oeste": "cidadela_15"}),
            ("cidadela_14", "Fonte Encantada (Área 14)", "Um barril de água magicamente preso na sala.", {"leste": "cidadela_15"}),
            ("cidadela_15", "Fora da Gaiola (Área 15)", "Onde o kobold chora ao lado da jaula vazia do dragão.", {"sul": "cidadela_4", "norte": "cidadela_16", "leste": "cidadela_13", "oeste": "cidadela_14"}),
            ("cidadela_16", "Kobolds Sentinelas (Área 16)", "Alojamento das sentinelas de Yusdrayl.", {"sul": "cidadela_15", "norte": "cidadela_19", "leste": "cidadela_17", "oeste": "cidadela_18"}),
            ("cidadela_17", "Despensa do Dragão (Área 17)", "Ratos espremidos em um cercado quebrado.", {"oeste": "cidadela_16"}),
            ("cidadela_18", "Prisioneiros de Guerra (Área 18)", "Goblins acorrentados ao chão implorando ajuda.", {"leste": "cidadela_16", "norte": "cidadela_19"}),
            ("cidadela_19", "Salão dos Dragões (Área 19)", "Colunas enormes esculpidas com dragões entrelaçados.", {"sul": "cidadela_16", "sul_oeste": "cidadela_18", "norte": "cidadela_20", "oeste": "cidadela_24"}),
            ("cidadela_20", "Colônia Kobold (Área 20)", "Kobolds trabalhando e curtindo couro.", {"sul": "cidadela_19", "norte": "cidadela_21", "leste": "cidadela_22", "oeste": "cidadela_23"}),
            ("cidadela_21", "O Trono do Dragão (Área 21)", "A líder Yusdrayl observa a sala do seu trono esculpido.", {"sul": "cidadela_20"}),
            ("cidadela_22", "Aposento Vazio (Área 22)", "Restos de uma vida antiga.", {"oeste": "cidadela_20"}),
            ("cidadela_23", "Acesso Subterrâneo (Área 23)", "Um buraco escuro que leva ao submundo.", {"leste": "cidadela_20"}),
            ("cidadela_24", "Corredor Armadilhado (Área 24)", "Território de divisa entre Goblins e Kobolds.", {"leste": "cidadela_19", "norte": "cidadela_30", "sul_leste": "cidadela_25", "sul_oeste": "cidadela_26", "norte_oeste": "cidadela_28", "oeste": "cidadela_29"}),
            ("cidadela_25", "Vazio (Área 25)", "Poeira e ecos.", {"norte_oeste": "cidadela_24"}),
            ("cidadela_26", "Fonte Seca (Área 26)", "A água há muito secou.", {"norte_leste": "cidadela_24", "oeste": "cidadela_27"}),
            ("cidadela_27", "Santuário (Área 27)", "Restos de adoração de elfos passados.", {"leste": "cidadela_26"}),
            ("cidadela_28", "Celas Infestadas (Área 28)", "Fedor horrível exala do chão.", {"sul_leste": "cidadela_24"}),
            ("cidadela_29", "Armadilha Desativada (Área 29)", "Um fosso inutilizado.", {"leste": "cidadela_24"}),
            ("cidadela_30", "Parede Goblin (Área 30)", "Barricadas e sujeira anunciam o domínio dos goblins.", {"sul": "cidadela_24", "norte": "cidadela_32", "oeste": "cidadela_31"}),
            ("cidadela_31", "Corredor de Estrepes (Área 31)", "Cuidado onde pisa. Estrepes por toda parte.", {"leste": "cidadela_30"}),
            ("cidadela_32", "Portão Goblin (Área 32)", "Goblins brutamontes bloqueiam o corredor de ossos.", {"sul": "cidadela_30", "oeste": "cidadela_34", "norte": "cidadela_33"}),
            ("cidadela_33", "Treinamento (Área 33)", "Alvos esburacados usados por arqueiros goblins.", {"sul": "cidadela_32"}),
            ("cidadela_34", "Salão do Chefe (Área 34)", "Durnn repousa aqui. O chão é coberto de troféus e sujeira.", {"leste": "cidadela_32", "norte": "cidadela_35", "sul": "cidadela_37", "descer": "cidadela_41"}),
            ("cidadela_35", "Paliçada Goblin (Área 35)", "Prisioneiros como o gnomo Erky amarrados nas grades.", {"sul": "cidadela_34", "norte": "cidadela_36"}),
            ("cidadela_36", "Guarda Goblin (Área 36)", "Salas de repouso dos guardas de Durnn.", {"sul": "cidadela_35"}),
            ("cidadela_37", "Sala de Troféus (Área 37)", "O filhote de dragão branco devora ovelhas no gelo.", {"norte": "cidadela_34", "oeste": "cidadela_38"}),
            ("cidadela_38", "Salão dos Goblins (Área 38)", "Uma baderna sem fim de restos e goblins dormindo.", {"leste": "cidadela_37", "norte": "cidadela_39", "oeste": "cidadela_40"}),
            ("cidadela_39", "Despensa Goblin (Área 39)", "Carne e cogumelos apodrecendo.", {"sul": "cidadela_38"}),
            ("cidadela_40", "Salão do Fosso (Área 40)", "Um poço escuro ameaça qualquer passo em falso.", {"leste": "cidadela_38"}),
            ("cidadela_41", "Salão Principal (Área 41)", "Grandes escadarias descem em direção às raízes da terra.", {"subir": "cidadela_34", "descer": "cidadela_42"}),
            ("cidadela_42", "Entrada do Bosque (Área 42)", "Fungos luminescentes tomam conta das pedras.", {"subir": "cidadela_41", "norte": "cidadela_43"}),
            ("cidadela_43", "Bifurcação (Área 43)", "Raízes grossas da Árvore Gulthias cruzam o chão.", {"sul": "cidadela_42", "norte": "cidadela_44"}),
            ("cidadela_44", "Bosque de Fungos (Área 44)", "Fungos gigantes que atacam qualquer movimento.", {"sul": "cidadela_43", "norte": "cidadela_45"}),
            ("cidadela_45", "O Cultivador (Área 45)", "O Acampamento profano onde o Bugbear supervisiona o mato.", {"sul": "cidadela_44", "leste": "cidadela_47", "norte": "cidadela_46"}),
            ("cidadela_46", "Caverna de Caça (Área 46)", "Restos de lobos e ossos quebrados.", {"sul": "cidadela_45"}),
            ("cidadela_47", "Laboratório (Área 47)", "O laboratório alquímico onde Belak conduz experiências.", {"oeste": "cidadela_45", "norte": "cidadela_48"}),
            ("cidadela_48", "Galeria de Mato (Área 48)", "Corredor sufocante. Ramos Secos se movem nas sombras.", {"sul": "cidadela_47", "norte": "cidadela_50", "oeste": "cidadela_49"}),
            ("cidadela_49", "Aposentos (Área 49)", "Câmaras antigas dominadas pelo mato.", {"leste": "cidadela_48"}),
            ("cidadela_50", "Jardim Sombrio (Área 50)", "Plantas venenosas cultivadas cuidadosamente pelo druida.", {"sul": "cidadela_48", "norte": "cidadela_54", "leste": "cidadela_51", "oeste": "cidadela_52", "norte_leste": "cidadela_53"}),
            ("cidadela_51", "Gruta de Ervas (Área 51)", "Ervas curativas misturadas com toxinas letais.", {"oeste": "cidadela_50"}),
            ("cidadela_52", "Caverna de Esporos (Área 52)", "Esporos mortais flutuam em uma névoa amarela.", {"leste": "cidadela_50"}),
            ("cidadela_53", "Bosque Adormecido (Área 53)", "Corpos servindo como fertilizantes para as raízes.", {"sul_oeste": "cidadela_50"}),
            ("cidadela_54", "Bosque do Crepúsculo (Área 54)", "O coração do jardim. A luz avermelhada não tem fonte visível.", {"sul": "cidadela_50", "norte": "cidadela_56", "oeste": "cidadela_55"}),
            ("cidadela_55", "Raízes Antigas (Área 55)", "Raízes grossas da árvore mãe pulsam com energia negra.", {"leste": "cidadela_54"}),
            ("cidadela_56", "A Árvore Gulthias (Área 56)", "A macabra árvore e o Druida Belak aguardam pelo fim.", {"sul": "cidadela_54"})
        ]

        for cod, nome, desc, con in salas_dados:
            db.add(Cena(cod_sala=cod, nome_sala=nome, descricao_visual=desc, conexoes=con))

        print("👹 Criando o Bestiário Completo...")
        inimigos_dados = [
            ("Rato Atroz", 6, 15, "+4", "1d4", 50, 0, False, 1, []),
            ("Esqueleto", 9, 13, "+1", "1d4", 50, 10, False, 1, []),
            ("Rato da Caverna", 2, 12, "+0", "1d2", 10, 0, False, 1, []),
            ("Mephit da Água", 15, 15, "+5", "1d4+2", 100, 25, False, 1, []),
            ("Kobold Sentinela", 4, 15, "+1", "1d6-1", 25, 2, False, 1, []),
            ("Goblin Saqueador", 7, 13, "+4", "1d6+2", 50, 5, False, 1, []),
            ("Goblin Arqueiro", 7, 13, "+4", "1d4", 50, 5, False, 1, []),
            ("Fungo Violeta", 15, 13, "+3", "1d6", 80, 0, False, 1, []),
            ("Ramo Seco", 5, 13, "+2", "1d4", 30, 0, False, 1, []),
            ("Jot (Quasit)", 18, 18, "+8", "1d3-1", 200, 50, True, 1, []),
            ("Sacerdote do Dragão (Troll)", 42, 16, "+9", "1d6+4", 400, 150, True, 1, ["Adaga Obra-Prima", "2x Bracelete de Dragão"]),
            ("Calcryx (Filhote de Dragão Branco)", 35, 15, "+6", "1d6+2", 300, 150, True, 1, ["Dente de Dragão de Gelo", "Escama de Calcryx"]),
            ("Durnn, Chefe Hobgoblin", 45, 15, "+5", "1d8+3", 250, 80, True, 1, ["Chave do Salão", "Espada Larga Enferrujada"]),
            ("Balsag, O Bugbear", 35, 15, "+5", "2d4+2", 200, 50, True, 1, ["Machado Gasto"]),
            ("Belak, o Proscrito (Druida)", 50, 14, "+6", "1d8+2", 500, 200, True, 1, ["Fruto da Árvore Gulthias", "Cajado Mágico Corrompido"])
        ]

        for nome, hp, ca, atk, dano, xp, ouro, boss, fase, loot in inimigos_dados:
            db.add(Inimigo(nome=nome, hp_max=hp, ca=ca, ataque=atk, dano=dano, xp_recompensa=xp, ouro_recompensa=ouro, is_boss=boss, fase_atual=fase, loot_especial=loot))

        print("⚔️ Espalhando os Encontros...")
        encontros_dados = [
            ("cidadela_1", "Rato Atroz", 3, 1),
            ("cidadela_3", "Rato Atroz", 1, 1),
            ("cidadela_5", "Esqueleto", 3, 1),
            ("cidadela_10", "Jot (Quasit)", 1, 1),
            ("cidadela_12", "Sacerdote do Dragão (Troll)", 1, 2),
            ("cidadela_14", "Mephit da Água", 1, 1),
            ("cidadela_16", "Kobold Sentinela", 3, 1),
            ("cidadela_17", "Rato da Caverna", 8, 1),
            ("cidadela_19", "Kobold Sentinela", 3, 1),
            ("cidadela_24", "Goblin Saqueador", 2, 1),
            ("cidadela_32", "Goblin Saqueador", 4, 1),
            ("cidadela_34", "Durnn, Chefe Hobgoblin", 1, 2),
            ("cidadela_37", "Calcryx (Filhote de Dragão Branco)", 1, 2),
            ("cidadela_44", "Fungo Violeta", 2, 1),
            ("cidadela_45", "Balsag, O Bugbear", 1, 1),
            ("cidadela_48", "Ramo Seco", 4, 1),
            ("cidadela_54", "Ramo Seco", 3, 1),
            ("cidadela_56", "Belak, o Proscrito (Druida)", 1, 3)
        ]
        
        for sala, inimigo, qtd, mult in encontros_dados:
            db.add(Encontro(cod_sala=sala, nome_inimigo=inimigo, quantidade=qtd, multiplicador_ameaca=mult))

        print("🧙‍♂️ Adicionando NPCs Oficiais...")
        npcs = [
            Npc(cod_sala="cidadela_15", nome="Meepo", descricao="O kobold encolhido chora copiosamente.", dialogo_base="Nós perdemos nosso dragão. Goblins o roubaram!", item_gatilho="Promessa"),
            Npc(cod_sala="cidadela_21", nome="Yusdrayl", descricao="Líder kobold imponente no trono.", dialogo_base="Tragam o filhote de volta e terão passagem garantida.", item_gatilho="Dente de Dragão de Gelo"),
            Npc(cod_sala="cidadela_35", nome="Erky Timbers", descricao="Gnomo clérigo espancado na prisão.", dialogo_base="Obrigado pela salvação. Durnn me manteve preso por meses!", item_gatilho="Chave do Salão")
        ]
        db.add_all(npcs)

        print("🗝️ Inserindo Armadilhas e Tesouros...")
        interativos = [
            Interativo(cod_sala="cidadela_3", nome="Alçapão Oculto", descricao="Fosso disfarçado.", tipo="armadilha", cd_teste=16, dano_falha=6),
            Interativo(cod_sala="cidadela_8", nome="Seta de Parede", descricao="Corda fina.", tipo="armadilha", cd_teste=21, dano_falha=4),
            Interativo(cod_sala="cidadela_12", nome="Sarcófago de Mármore", descricao="Seis trincos.", tipo="bau", cd_teste=21, atributo_teste="STR", recompensa=["220 PP", "50 PO"]),
            Interativo(cod_sala="cidadela_34", nome="Cofre do Durnn", descricao="Baú de ferro.", tipo="bau", cd_teste=14, recompensa=["Ouro", "Anel de Proteção"]),
            Interativo(cod_sala="cidadela_56", nome="A Árvore Gulthias", descricao="Raízes sangrentas cravadas no solo.", tipo="segredo", cd_teste=20, recompensa=["O Segredo da Maldição Resolvido"])
        ]
        db.add_all(interativos)

        db.commit()
        print("✅ TODAS as 56 salas da Cidadela Sem Sol estão prontas e conectadas! O épico renasceu.")

if __name__ == "__main__":
    popular_banco()