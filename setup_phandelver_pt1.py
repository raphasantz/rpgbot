from database import get_db_session, engine, Base
from models import Cena, Encontro, Inimigo, Npc, Interativo

def popular_phandelver_pt1():
    with get_db_session() as db:
        print("A iniciar mapeamento da Parte 1 de Phandelver...")

        # ==========================================
        # 1. BESTIÁRIO (Inimigos do Ato 1)
        # ==========================================
        inimigos_pt1 = [
            Inimigo(nome="Goblin", hp_max=7, ca=15, ataque="+4", xp_recompensa=50, ouro_recompensa=2),
            Inimigo(nome="Lobo", hp_max=11, ca=13, ataque="+4", xp_recompensa=50, ouro_recompensa=0),
            Inimigo(nome="Yeemik", hp_max=12, ca=15, ataque="+4", xp_recompensa=65, is_boss=True, ouro_recompensa=10),
            Inimigo(nome="Klarg", hp_max=27, ca=16, ataque="+4", xp_recompensa=200, is_boss=True, ouro_recompensa=25),
            Inimigo(nome="Ripper (Lobo do Klarg)", hp_max=15, ca=13, ataque="+4", xp_recompensa=50)
        ]
        
        for inimigo in inimigos_pt1:
            if not db.query(Inimigo).filter(Inimigo.nome == inimigo.nome).first():
                db.add(inimigo)

        # ==========================================
        # 2. CENAS (Salas do Esconderijo)
        # ==========================================
        cenas_pt1 = [
            Cena(
                cod_sala="trilha_triboar",
                nome_sala="Trilha Triboar (A Emboscada)",
                descricao_visual="Estás numa estrada de terra batida. Dois cavalos mortos bloqueiam o caminho. Estão crivados de flechas de penas negras. A floresta ao redor é densa e esconde barrancos íngremes em ambos os lados.",
                conexoes={"norte": "esconderijo_entrada", "leste": "phandalin", "oeste": "neverwinter"},
                loot_fixo=["Estojo de Mapas Vazio"]
            ),
            Cena(
                cod_sala="esconderijo_entrada",
                nome_sala="1. Entrada da Caverna",
                descricao_visual="Seguindo os rastos dos goblins, chegas a uma grande caverna numa encosta. Um riacho raso flui de dentro da escuridão. Arbustos densos escondem os flancos da entrada.",
                conexoes={"sul": "trilha_triboar", "norte": "esconderijo_passagem"}
            ),
            Cena(
                cod_sala="esconderijo_passagem",
                nome_sala="2. Passagem dos Goblins",
                descricao_visual="O som da água ecoa pela caverna úmida. O riacho ocupa a maior parte da passagem. O chão é escorregadio e há uma armadilha armada no escuro.",
                conexoes={"sul": "esconderijo_entrada", "leste": "esconderijo_lobos", "norte": "esconderijo_ponte"}
            ),
            Cena(
                cod_sala="esconderijo_lobos",
                nome_sala="3. Poço dos Lobos",
                descricao_visual="Esta caverna tem uma fissura natural no teto. Lobos rosnantes estão acorrentados a estacas de ferro cravadas no chão. O cheiro a animal molhado e carne podre é intenso.",
                conexoes={"oeste": "esconderijo_passagem", "norte": "esconderijo_fissura"}
            ),
            Cena(
                cod_sala="esconderijo_fissura",
                nome_sala="4. Passagem Íngreme",
                descricao_visual="Uma fenda estreita no fundo do poço dos lobos leva para cima através de rochas pontiagudas, cheia de entulho. É um atalho direto para a caverna do líder.",
                conexoes={"sul": "esconderijo_lobos", "norte": "esconderijo_klarg"}
            ),
            Cena(
                cod_sala="esconderijo_ponte",
                nome_sala="5. Passagem Superior",
                descricao_visual="A passagem principal bifurca-se. O riacho corre por aqui. 6 metros acima, uma frágil ponte de madeira cruza a ravina. Uma cascata ruge mais à frente.",
                conexoes={"sul": "esconderijo_passagem", "norte": "esconderijo_fontes", "oeste": "esconderijo_covil"}
            ),
            Cena(
                cod_sala="esconderijo_covil",
                nome_sala="6. Covil dos Goblins",
                descricao_visual="Esta caverna ampla está dividida em dois níveis por uma escarpa íngreme. O chão está coberto de fogueiras apagadas, sacos de dormir sujos e restos de comida. Há um prisioneiro humano amarrado no nível superior.",
                conexoes={"leste": "esconderijo_ponte"}
            ),
            Cena(
                cod_sala="esconderijo_fontes",
                nome_sala="7. Caverna das Fontes Gêmeas",
                descricao_visual="A caverna é preenchida por duas piscinas que captam a água de uma fonte subterrânea. A água flui das piscinas formando o riacho. Há barragens rudimentares que podem ser libertadas para inundar a caverna.",
                conexoes={"sul": "esconderijo_ponte", "leste": "esconderijo_klarg"}
            ),
            Cena(
                cod_sala="esconderijo_klarg",
                nome_sala="8. Caverna de Klarg",
                descricao_visual="A caverna do líder. Fogueiras iluminam o espaço cheio de caixotes roubados e mercadorias. Um trono feito de rochas sobrepõe-se ao ambiente.",
                conexoes={"oeste": "esconderijo_fontes", "sul": "esconderijo_fissura"}
            )
        ]
        
        for cena in cenas_pt1:
            if not db.query(Cena).filter(Cena.cod_sala == cena.cod_sala).first():
                db.add(cena)

        # ==========================================
        # 3. ENCONTROS E NPCS
        # ==========================================
        db.flush() # Sincroniza para garantir que as salas existem

        encontros = [
            Encontro(cod_sala="trilha_triboar", nome_inimigo="Goblin", quantidade=4),
            Encontro(cod_sala="esconderijo_entrada", nome_inimigo="Goblin", quantidade=2), # Guardas nos arbustos
            Encontro(cod_sala="esconderijo_lobos", nome_inimigo="Lobo", quantidade=3),
            Encontro(cod_sala="esconderijo_ponte", nome_inimigo="Goblin", quantidade=1), # Vigia na ponte
            Encontro(cod_sala="esconderijo_covil", nome_inimigo="Goblin", quantidade=5),
            Encontro(cod_sala="esconderijo_covil", nome_inimigo="Yeemik", quantidade=1),
            Encontro(cod_sala="esconderijo_fontes", nome_inimigo="Goblin", quantidade=3),
            Encontro(cod_sala="esconderijo_klarg", nome_inimigo="Goblin", quantidade=2),
            Encontro(cod_sala="esconderijo_klarg", nome_inimigo="Ripper (Lobo do Klarg)", quantidade=1),
            Encontro(cod_sala="esconderijo_klarg", nome_inimigo="Klarg", quantidade=1)
        ]
        
        for enc in encontros:
            db.add(enc)

        # Sildar Hallwinter (Prisioneiro)
        sildar = Npc(
            cod_sala="esconderijo_covil",
            nome="Sildar Hallwinter",
            descricao="Um humano idoso, mas forte. Está gravemente ferido e amarrado no chão do covil.",
            dialogo_base="Gundren Rockseeker foi levado para o Castelo Dentefino! Os goblins aqui servem um Bugbear chamado Klarg. Se me soltarem e me levarem a Phandalin, prometo pagar 50 Peças de Ouro."
        )
        db.add(sildar)

        # ==========================================
        # 4. INTERATIVOS (Armadilhas e Loot do Boss)
        # ==========================================
        armadilha_laco = Interativo(
            cod_sala="esconderijo_passagem",
            tipo="armadilha",
            nome="Armadilha de Laço",
            descricao="Um cabo escondido no chão escorregadio.",
            atributo_teste="DEX",
            cd_teste=12,
            dano_falha=4,
            recompensa=[]
        )
        
        bau_klarg = Interativo(
            cod_sala="esconderijo_klarg",
            tipo="bau",
            nome="Tesouro de Klarg",
            descricao="Um baú de ferro e madeira atrás do trono.",
            atributo_teste="DEX",
            cd_teste=10,
            dano_falha=0,
            recompensa=["600 pc", "110 pp", "2 Poções de Cura", "Estatueta de Sapo de Jade (40 PO)"]
        )
        
        db.add_all([armadilha_laco, bau_klarg])
        
        db.commit()
        print("✅ Parte 1 de Phandelver injetada com sucesso no banco de dados!")

if __name__ == "__main__":
    popular_phandelver_pt1()