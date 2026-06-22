#!/usr/bin/env python3
"""
seed_aventuras_v2.py — Seed completo das 2 aventuras (do zero, dos PDFs).
Le os arquivos extraidos e popula o banco PostgreSQL do VPS.

Uso:
    cd "E:\\DADOS\\Documents\\PYTHON PROJECTS\\mesanerd"
    .venv\\Scripts\\python.exe seed_aventuras_v2.py

AVISO: Este script LIMPA e REPOPULA as tabelas de aventura.
Nao toca em: jogadores, campanhas, estatisticas, historico, missoes.
"""
import os
import sys
import json
import psycopg2
from psycopg2.extras import execute_values

# CONEXAO COM O BANCO
DB_HOST = "216.22.5.41"
DB_PORT = 5432
DB_NAME = "rpg"
DB_USER = "rpg"
DB_PASS = os.environ.get("PGPASSWORD", "")
if not DB_PASS:
    # Tentar carregar do .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
        from urllib.parse import urlparse
        url = os.environ.get("DATABASE_URL", "")
        if url:
            DB_PASS = urlparse(url).password or ""
    except Exception:
        pass

if not DB_PASS:
    print("ERRO: Defina PGPASSWORD no ambiente antes de rodar.")
    sys.exit(1)

conn = psycopg2.connect(
    host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
    user=DB_USER, password=DB_PASS
)
conn.autocommit = False
cur = conn.cursor()

def limpar_tabelas():
    tabelas = ["encontros_aleatorios", "interativos", "encontros", "npcs", "cenas", "inimigos", "aventuras"]
    for t in tabelas:
        cur.execute(f"DELETE FROM {t}")
        print(f"  Limpeza: {t} - {cur.rowcount} registros removidos")
    conn.commit()
    print("Tabelas limpas.\n")

def inserir_aventura(id_str, nome, prologo=""):
    cur.execute("INSERT INTO aventuras (id, nome, prologo) VALUES (%s, %s, %s) ON CONFLICT (id) DO UPDATE SET nome=EXCLUDED.nome, prologo=EXCLUDED.prologo", (id_str, nome, prologo))

def inserir_cena(cod_sala, nome_sala, descricao, conexoes, imagem_url="", loot=None, hazards=None):
    cur.execute("SELECT cod_sala FROM cenas WHERE cod_sala = %s", (cod_sala,))
    exists = cur.fetchone()
    if exists:
        cur.execute("UPDATE cenas SET nome_sala=%s, descricao_visual=%s, conexoes=%s, imagem_url=%s, loot_fixo=%s, hazards=%s WHERE cod_sala=%s",
                (nome_sala, descricao, json.dumps(conexoes), imagem_url, json.dumps(loot or []), json.dumps(hazards or []), cod_sala))
    else:
        cur.execute("INSERT INTO cenas (cod_sala, nome_sala, descricao_visual, conexoes, imagem_url, loot_fixo, hazards) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (cod_sala, nome_sala, descricao, json.dumps(conexoes), imagem_url, json.dumps(loot or []), json.dumps(hazards or [])))

def inserir_encontro(cod_sala, nome_inimigo, qtd, condicao="sempre", ativo=True, mult=1):
    cur.execute("INSERT INTO encontros (cod_sala, nome_inimigo, quantidade, condicao_aparecimento, ativo, multiplicador_ameaca) VALUES (%s, %s, %s, %s, %s, %s)",
        (cod_sala, nome_inimigo, qtd, condicao, ativo, mult))

def inserir_npc(cod_sala, nome, descricao, dialogo_base="", dialogo_item="", item_gatilho=""):
    cur.execute("INSERT INTO npcs (cod_sala, nome, descricao, dialogo_base, dialogo_item_especial, item_gatilho) VALUES (%s, %s, %s, %s, %s, %s)",
        (cod_sala, nome, descricao, dialogo_base, dialogo_item, item_gatilho))

def inserir_interativo(cod_sala, nome, descricao, tipo, cd_teste=10, attr="DEX", recompensa=None, dano=0):
    cur.execute("INSERT INTO interativos (cod_sala, nome, descricao, tipo, cd_teste, atributo_teste, recompensa, dano_falha) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (cod_sala, nome, descricao, tipo, cd_teste, attr, json.dumps(recompensa or []), dano))

def inserir_inimigo(nome, hp, ca, ataque, dano, xp=50, ouro=5, is_boss=False, loot=None, resistencias=None, vulnerabilidades=None, imunidades=None):
    cur.execute("SELECT id FROM inimigos WHERE nome = %s", (nome,))
    exists = cur.fetchone()
    if exists:
        cur.execute("UPDATE inimigos SET hp_max=%s, ca=%s, ataque=%s, dano=%s, xp_recompensa=%s, ouro_recompensa=%s, is_boss=%s, loot_especial=%s WHERE nome=%s",
                (hp, ca, ataque, dano, xp, ouro, is_boss, json.dumps(loot or []), nome))
    else:
        cur.execute("INSERT INTO inimigos (nome, hp_max, ca, ataque, dano, xp_recompensa, ouro_recompensa, is_boss, loot_especial, resistencias, vulnerabilidades, imunidades) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (nome, hp, ca, ataque, dano, xp, ouro, is_boss, json.dumps(loot or []), json.dumps(resistencias or []), json.dumps(vulnerabilidades or []), json.dumps(imunidades or [])))


# INIMIGOS - Bestiario completo
def seed_inimigos():
    print("=== Inserindo inimigos ===")
    inimigos = [
        ("Rato Atroz", 5, 13, "Mordida +3", "1d4+1 contundente", 10, 1, False, None, None, None, None),
        ("Ramo Seco", 5, 13, "Golpe +4", "1d6+2 contundente", 25, 1, False, None, None, None, None),
        ("Esqueleto", 9, 13, "Espada +4", "1d6+1 cortante", 50, 2, False, None, None, None, None),
        ("Esqueleto Arqueiro", 9, 13, "Arco +4", "1d6+1 perfurante", 50, 2, False, None, None, None, None),
        ("Kobold Sentinela", 4, 15, "Lanca +4", "1d6+2 perfurante", 25, 1, False, None, None, None, None),
        ("Goblin Saqueador", 4, 15, "Espada curta +4", "1d6+2 perfurante", 50, 2, False, None, None, None, None),
        ("Goblin Guerreiro", 4, 15, "Azagaia +4", "1d6+2 perfurante", 50, 2, False, None, None, None, None),
        ("Robgoblin Guerreiro", 5, 15, "Machado +4", "1d6+2 cortante", 50, 3, False, None, None, None, None),
        ("Bugbear Jardineiro", 16, 16, "Foice +5", "2d6+3 cortante", 200, 15, False, None, None, None, None),
        ("Balsag (Bugbear)", 36, 16, "Maca +5", "2d8+4 contundente", 200, 15, True, None, None, None, None),
        ("Mephit da Agua", 15, 13, "Toque +4", "1d4+2 gelo", 100, 10, False, None, None, None, None),
        ("Quasit Jot", 18, 13, "Garras +4", "1d4+2 veneno", 100, 10, False, None, None, None, None),
        ("Sombra", 13, 12, "Tocar +4", "1d6+2 necrotico + 1d4 FOR", 100, 10, False, None, ["nao-magico"], None, None),
        ("Sacerdote-Troll", 42, 15, "Garra +7", "2d6+4 cortante", 300, 20, True, None, ["fogo"], ["fogo", "acido"], None),
        ("Durnn (Chefe Goblin)", 16, 15, "Machado +4", "1d8+2 cortante", 100, 10, True, None, None, None, None),
        ("Crenl (Cleriga)", 5, 12, "Bordao +2", "1d6 contundente", 50, 5, False, None, None, None, None),
        ("Calcryx (Filhote Dragao)", 31, 17, "Mordida +5", "1d6+3 cortante + frio", 200, 15, True, None, ["frio 20"], None, None),
        ("Kulket (Sapo Gigante)", 16, 14, "Mordida +3", "1d6+1 contundente", 50, 3, False, None, None, None, None),
        ("Belak o Proscrito", 36, 15, "Funda +3", "1d4+1 contundente", 500, 50, True, None, None, None, None),
        ("Sharwyn (Corrompida)", 7, 16, "Adaga +4", "1d4+2 perfurante", 100, 10, False, None, None, None, None),
        ("Sir Bradford (Corrompido)", 12, 16, "Espada bastarda +5", "2d8+3 cortante", 100, 10, False, None, None, None, None),
        ("Thoqqua", 16, 14, "Investida +4", "1d8+3 fogo", 200, 15, False, None, ["fogo"], None, None),
        ("Rato de Caverna", 2, 10, "Mordida +0", "1 contundente", 10, 0, False, None, None, None, None),
        ("Lobo", 11, 13, "Mordida +4", "2d4+2 cortante", 50, 3, False, None, None, None, None),
        ("Gutash (Rata Grande)", 18, 12, "Mordida +3", "1d6+1 contundente", 100, 8, False, None, None, None, None),
        ("Goblin", 7, 15, "Espada curta +4", "1d6+2 perfurante", 50, 2, False, None, None, None, None),
        ("Bugbear", 27, 16, "Mangual +5", "2d8+4 contundente", 200, 15, False, None, None, None, None),
        ("Aranha Gigante", 26, 14, "Mordida +5", "1d8+3 veneno", 200, 15, False, None, None, None, None),
        ("Bandido Marcarrubra", 16, 14, "Espada +4", "1d6+2 cortante", 100, 10, False, None, None, None, None),
        ("Ghoul", 22, 12, "Garra +2", "2d6+2 necrotico + paralisia", 200, 10, False, None, None, None, None),
        ("Nothic", 45, 15, "Garra +4", "3d6+2 necrotico", 450, 25, True, None, None, None, None),
        ("Hobgoblin", 11, 18, "Lanca +4", "1d10+2 perfurante", 100, 10, False, None, None, None, None),
        ("Grick", 27, 14, "Garra +4", "2d6+2 cortante", 450, 25, False, None, ["nao-magico"], None, None),
        ("Urso Coruja", 59, 13, "Garra +6", "2d8+4 cortante", 700, 30, False, None, None, None, None),
        ("Rei Grol (Bugbear)", 45, 16, "Mangual +6", "2d8+5 contundente", 700, 50, True, None, None, None, None),
        ("Doppelganger", 52, 14, "Garra +6", "1d6+3 contundente", 700, 30, False, None, None, None, None),
        ("Gosma Ocre", 22, 8, "Pseudopode +3", "1d6+1 acido", 100, 5, False, None, None, None, None),
        ("Stirge", 2, 14, "Probosside +5", "1d4+3 sangue", 25, 0, False, None, None, None, None),
        ("Esqueleto Armado", 13, 13, "Espada +4", "1d6+2 cortante", 50, 2, False, None, None, None, None),
        ("Aparicao Mormesk", 45, 13, "Tocar +5", "3d8+3 necrotico", 700, 30, True, None, ["nao-magico"], None, None),
        ("Espectador", 39, 15, "Raios opticos +7", "varios", 700, 40, True, None, None, None, None),
        ("Crânio em Chamas", 40, 13, "Raio de fogo +5", "3d6 fogo", 1100, 50, True, None, None, None, None),
        ("Zumbi", 22, 12, "Raia +3", "1d6+1 contundente", 50, 2, False, None, None, None, None),
        ("Zumbi das Cinzas", 22, 12, "Garra +3", "1d6+1 contundente + brisa", 50, 3, False, None, None, None, None),
        ("Ogro", 59, 11, "Clava +6", "2d8+4 contundente", 450, 30, False, None, None, None, None),
        ("Orc", 15, 13, "Machado +5", "1d12+3 cortante", 100, 10, False, None, None, None, None),
        ("Nezznar (Aranha Negra)", 27, 11, "Cajado +5", "1d6+3 veneno", 450, 50, True, None, None, None, None),
        ("Cultista", 9, 12, "Adaga +2", "1d4+1 perfurante", 25, 1, False, None, None, None, None),
        ("Venomfang (Dragao Verde)", 136, 18, "Mordida +7", "2d10+4 cortante + veneno", 3900, 200, True, None, ["veneno"], None, None),
        ("Wyvern", 136, 13, "Garras +6", "2d6+4 cortante", 500, 50, True, None, None, None, None),
        ("Basilisco", 52, 15, "Mordida +7", "2d8+5 cortante", 150, 15, False, None, None, None, None),
    ]
    for inf in inimigos:
        inserir_inimigo(*inf)
    print(f"  {len(inimigos)} inimigos inseridos\n")


# CIDADELA SEM SOL - 57 areas (0-56)
def seed_cidadela():
    print("=== Inserindo salas: Cidadela Sem Sol ===")
    salas = [
        ("cidadela_0", "Estrada Velha da Cidadela", "A Estrada Velha atravessa uma ravina estreita e profunda (~9m). Pilares quebrados com inscricoes Anas. Entrada para a Cidadela Sem Sol.", {"sul": "taverna", "baixo": "cidadela_1"}, [], ["Queda sem corda: 2d6 dano (CD 10)"]),
        ("cidadela_1", "Parapeito", "Parapeito de areia domina um golfo subterraneo. Areia, pedregulhos e ossos.", {"cima": "cidadela_0", "baixo": "cidadela_2"}, [], ["Queda do parapeito: 5d6 dano"]),
        ("cidadela_2", "Escadas Sinuosas", "Escadas de 1,5m de largura, risticas e escorregadias.", {"cima": "cidadela_1", "baixo": "cidadela_3"}, [], ["Quedas: 6d6/4d6/2d6 por lance (CD 10 Equilibrio)"]),
        ("cidadela_3", "Patio em Ruinas", "Pequeno patio cercado por alvenaria ornamental. Alcapao com fossos.", {"cima": "cidadela_1", "norte": "cidadela_4", "oeste": "cidadela_6"}, ["23 PP e 4 PO escondidos"], ["Alcapao e Fosso (CD 16 Reflexos, 1d6 dano)"]),
        ("cidadela_4", "Torre em Ruinas", "5 goblins mortos ha um mes. Porta secreta com armadilha.", {"sul": "cidadela_3", "porta_secreta": "cidadela_5", "oeste": "cidadela_6"}, ["2d10 PP total", "10 PO total"]),
        ("cidadela_5", "Pequena Camara Secreta", "Pequena camara atras de porta secreta (Procurar CD 16).", {"porta_secreta": "cidadela_4"}, ["2d10 PP", "10 PO"], ["Agulha envenenada (CD 20, 1d4 CON temporario)"]),
        ("cidadela_6", "Antiga Passagem", "Salao de 6m. Porta de pedra com dragao esculpido. Trancada magicamente.", {"leste": "cidadela_4", "porta": "cidadela_7"}, [], ["Porta trancada magicamente"]),
        ("cidadela_7", "Galeria das Notas de Forlorn", "Camara empoeirada. Dois globos de bronze sobre pedestais.", {"sul": "cidadela_6", "norte": "cidadela_8"}, [], ["Globo Musical (CD 18 Vontade)"]),
        ("cidadela_8", "Placas de Pressao", "Corredor de 12m. Placa de pressao dispara setas.", {"sul": "cidadela_7", "norte": "cidadela_9"}, [], ["Setas (CD 21 Procurar, 1d6 dano x3)"]),
        ("cidadela_9", "O Enigma do Dragao", "Camara com escultura de dragao. Boca fala o enigma. Resposta: Bruma.", {"porta_secreta": "cidadela_10"}, [], ["Enigma: so abre com resposta correta"]),
        ("cidadela_10", "Guarda de Honra", "Arcos de pedra. Tunel na parede norte. Fenda oposta. Quasit Jot espreita.", {"tunel": "cidadela_11", "fosso": "cidadela_12"}, [], ["Fosso: 1d6 + 1d4 estacas (CD 16)"]),
        ("cidadela_11", "Sala Secreta", "Pequento quarto com inscricoes. Alcapao secreto.", {"porta_secreta": "cidadela_10"}, ["Inscricao em Draconico"]),
        ("cidadela_12", "Tumba do Sacerdote do Dragao", "Camara talhada na rocha. Sarcofago de marmore. Sacerdote-Troll louco e faminto.", {"via_alcapao": "cidadela_11"}, ["Adaga obra-prima", "220 PP + 50 PO", "4 pergaminhos divinos", "Pocao de Cura"]),
        ("cidadela_13", "Camara Vazia", "Camara em ruinas com monte de escombros.", {"variavel": "conecta areas adjacentes"}, []),
        ("cidadela_14", "Fonte dAgua Encantada", "Camara de 3m. Porta de peixe draconico trancada (CD 21).", {"porta": "cidadela_14"}, ["5 safiras (5 PO cada) = 25 PO"], ["Mephit da Agua hostil"]),
        ("cidadela_15", "Fora da Gaiola (Meepo)", "Grande camara arruinada. Simbolos Draconicos. Poco no centro. Meepo adormecido.", {"conecta": "multiplas areas"}, ["Figura jade dragao (15 PO)", "4 figuras jade dragao (16 PO cada) = 64 PO"]),
        ("cidadela_16", "Kobolds Sentinelas", "Quartais e postos de guarda. Portas com armadilhas.", {"multiplas": "conexoes no mapa"}, ["2d10 PP por grupo"], ["Setas (CD 20, 1d6 x3)"]),
        ("cidadela_17", "Despensa do Dragao", "Aposento com ratos e fezes. Pequena barreira.", {"conecta": "areas adjacentes"}, []),
        ("cidadela_18", "Prisioneiros de Guerra", "Portas trancadas (CD 20). Tres goblins amarrados.", {"porta": "cidadela_18"}, ["20 PP por goblin"]),
        ("cidadela_19", "Salao dos Dragoes", "Fileira dupla de colunas de marmore com dragoes esculpidos.", {"porta": "cidadela_21"}, [], ["Reforcos: 12 kobolds em 1-2 minutos"]),
        ("cidadela_20", "Colonia Kobold", "Refugio principal dos kobolds. Porta resistente (CD 25). 24 kobolds.", {"porta": "cidadela_20"}, [], ["PJs matando kobolds incapazes: 0 XP"]),
        ("cidadela_21", "O Trono do Dragao", "Altar de pedra. Chave magica na boca do dragao (Forca CD 20). Yusdrayl e 6 sentinelas.", {"passagem": "cidadela_15, cidadela_25"}, ["Amuleto 40 PO", "Pergaminho Armadura Arcana", "Pergaminho Invisibilidade", "Chave magica"]),
        ("cidadela_22", "Despensa", "Odor de carne podre. Ganchos de ferro no teto.", {"conecta": "areas adjacentes"}, []),
        ("cidadela_23", "Acesso ao Subterraneo", "Pedras soltas abrindo tunel. Equipamentos de caça.", {"tunel": "locais alem da aventura"}, []),
        ("cidadela_24", "Passagem do Fosso", "Corredor de 6m. Portas trancadas. Fosso.", {"portas": "cidadela_24"}, [], ["Fosso (CD 16 Reflexos, 1d6 dano)"]),
        ("cidadela_25", "Desolacao", "Vazia e escura. Detritos de ratos. Lajes em pedacos.", {"porta": "cidadela_31"}, []),
        ("cidadela_26", "Fonte Seca", "Fonte ornamental seca. Escultura de dragao. Porta de pedra.", {"porta": "cidadela_27"}, ["Pocao de licores de dragao"]),
        ("cidadela_27", "Santuario", "Camara empoeirada. Tres sarcofagos na norte, dois na sul. Altar com Chama Eterna.", {"porta_especial": "cidadela_27"}, ["Apito de bronze magico", "Gems esculpidas (10 PO cada)"], ["5 Esqueletos guardam sarcofagos"]),
        ("cidadela_28", "Celas Infestadas", "Seis portas (A a F). Frestas grandes.", {"multiplas": "celas individuais"}, ["2d6 PP e 1d4 gemas de 5 PO por ninho"], ["3 Ratos Atrozes em celas B, C, D"]),
        ("cidadela_29", "Armadilhas Antigas", "Dois alcapoes abertos. Fonte seca com dragao.", {"porta": "cidadela_30"}, [], ["Armadilha Naruhune (CD 14 Fortitude, 1d4 CON temporario)"]),
        ("cidadela_30", "Mamae Rato", "Ninho enorme de ratos. Cadaveres. Porta norte.", {"norte": "cidadela_3"}, ["300 PP", "68 PO", "3 gemas 1d4x10 PO"], ["Gutash (rata grande) emboscada"]),
        ("cidadela_31", "Camara dos Estrepes", "Aposento coberto com estrepe (4 pontas). Amuraca.", {"porta_sul": "cidadela_32", "norte": "cidadela_30"}, ["15 bolas de 1kg"], ["Sino na porta (CD 21)", "Estrepe: 1d4 dano por passo"]),
        ("cidadela_32", "Portao Goblin", "Posto de guarda da tribo Durbuluk. Amuraca. Fogueira.", {"norte": "cidadela_31"}, ["2d10+2 PP por goblin"]),
        ("cidadela_33", "Sala de Pratica", "Goblins praticam tiro com azagaias. Bebem vinho.", {"conecta": "cidadela_32"}, ["Jarro de Po Anao (50 PO)", "Chave da Area 34"]),
        ("cidadela_34", "Prisao Militar Goblin", "Tres kobolds amarrados. Gnomo Erky Timbers preso.", {"porta": "cidadela_34"}, [], ["Erky Timbers: aliado, sabe sobre Belak"]),
        ("cidadela_35", "Corredor com Armadilha", "Corredor comum. Porta para Area 37 trancada (CD 18).", {"porta": "cidadela_37"}, ["Anel de ouro com safira (25 PO)"], ["Fosso (CD 16, 1d6 dano)"]),
        ("cidadela_36", "Saltadores Goblins", "Seis redes de peles. Fogo de cozinha. Armas quebradas.", {"multiplas": "conexoes"}, ["3d10+10 PP, 1d4 PO por goblin"]),
        ("cidadela_37", "Sala dos Trofeus", "Cabecas de animais empalhados. Calcryx (Filhote de Dragao Branco).", {"duas_portas": "cidadela_37"}, ["Figura jade (20 PO)", "24 PP refinada", "Pergaminho antigo (100 PO)"], ["Calcryx: sopro cone 1d4 frio"]),
        ("cidadela_38", "Passagem Goblin", "Estocar agua. 2,5 litros de oleo. Barris de puplice.", {"conecta": "areas adjacentes"}, ["2,5 litros de oleo"]),
        ("cidadela_39", "Fumaca do Dragao", "Salao com fumaca das tochas. Paredes ornamentadas.", {"conecta": "cidadela_36"}, [], ["Fumaca: quarto de camuflagem"]),
        ("cidadela_40", "Vilarejo Goblin", "Principal refugio da tribo Durbuluk (60+ anos). Fungos fosforescentes.", {"multiplas": "conexoes"}, ["2 estatuas (30 PO cada) = 60 PO", "3 aneis prata+gemas (20 PO) = 60 PO"]),
        ("cidadela_41", "Camara do Chefe Goblin", "Trono de pedra. Durnn, Crenl, goblins e 1 Ramo Seco.", {"poco": "Bosque do Crepusculo (24m abaixo)"}, ["230 PO", "2 gemas onix (30 PO)", "2 antidotos", "Pergaminho Armadura de Barkskin", "Pocao de Cura"], ["Arca envenenada (CD 18, 1d4 CON temporario)"]),
        ("cidadela_42", "Central de Adubo", "Grande variedade de vida vegetal. 2 Ramos Secos + 2 Esqueletos.", {"no_bosque": "conecta areas"}, [], ["Reforcos da Area 43 em 3 rodadas"]),
        ("cidadela_43", "O Grande Cacador", "Caverna rustica. Balsag (bugbear cacador).", {"tunel": "Subterraneo"}, ["3d20 PP e 4d10 PO por ninho de esquilo"], ["Balsag: maca de estrepe +1 1/2 MOD"]),
        ("cidadela_44", "Fenda", "Tunel interrompido por abertura geologica. Cheiro de enxofre.", {"ala_noroeste": "cidadela_47"}),
        ("cidadela_45", "Nodulo da Fenda", "Fenda se alarga. Thoqqua.", {"no_tunel": "conecta"}, ["2 Safiras (50 PO cada) = 100 PO"], ["Thoqqua: investida +2, Incinar"]),
        ("cidadela_46", "O Antigo Altar", "Mosaico de azulejos. Pedestal de metal na forma de dragao.", {"porta": "cidadela_46"}),
        ("cidadela_47", "Comunidade Goblin de Belak", "Fileira dupla de colunas. 8 goblins + 1 rato atroz.", {"multiplas": "sub-areas 47a-47f"}, ["Cataplasma (10 PO)", "Barris licor goblin (5 PO cada)"]),
        ("cidadela_48", "Galeria", "Plantas, tocos e arvores em canteiros. Bugbear jardineiro.", {"portas": "fechadas"}, ["1 dose fertilizante especial (30 PO)"], ["Bugbear: foice longa +1 1/2 MOD"]),
        ("cidadela_49", "Arvoredo (4 sub-areas)", "Quatro arvoredos. 49a: 4 goblins. 49b: Thoqqua jovem. 49c: 3 esqueletos. 49d: 1 bugbear.", {"conecta": "areas adjacentes"}, ["20 PO (safiras, 49b)"]),
        ("cidadela_50", "Templo de Ashardalon", "Blocos de granito com dragoes. Enorme estatua. Globo verde no dragao.", {"conecta": "areas"}, ["34 PO", "2 frascos fogo grego"], ["Sombra: 1d6 FOR temporario"]),
        ("cidadela_51", "Biblioteca dos Dragoes", "Prateleiras destruidas. Paginas rasgadas e queimadas.", {"portas_opostas": "conecta adjacentes"}, ["2 Pergaminhos arcanos", "Volume dragoes (150 PO)"]),
        ("cidadela_52", "Passagem Subterranea", "Degraus em ruinas. Corredor de 3m. Muito umida e destruida.", {"conecta": "niveis"}),
        ("cidadela_53", "Conhecimento da Natureza", "Cera no chao. Prateleiras rusticcas. Mesa rustica.", {"porta": "cidadela_53"}, ["2 Pergaminhos divinos", "Tomo Druida (150 PO)"]),
        ("cidadela_54", "Portao do Bosque", "Camara arqueada. 4 goblins separam galhos.", {"para_bosque": "cidadela_56"}, []),
        ("cidadela_55", "Bosque do Crepusculo", "Galhos da superficie. Arbustos doentes. 10 Ramos Secos + reforcos.", {"para_arvore": "cidadela_56", "volta": "cidadela_54"}, [], ["Ramos Secos atacam imediatamente", "Arbustos: metade deslocamento"]),
        ("cidadela_56", "A Arvore Gulthias - BOSS FINAL", "Patio com paredes de 6m. Arvore de 15m. Belak (Druida 4). Sir Bradfod e Sharwyn suplicantes. 3 Ramos Secos + Kulket.", {"ponto_final": "Fim da aventura"}, ["Varinha Construcao de Madeira (Belak)", "Espada Estilhacadora (Sir Bradfod)"], ["Boss: Belak 36 PV, Arvore 33 PV, Sir Bradfod 12 PV, Sharwyn 7 PV, Kulket 16 PV"]),
    ]
    for s in salas:
        inserir_cena(*s)
    print(f"  {len(salas)} salas da Cidadela inseridas\n")


def seed_encontros_cidadela():
    print("=== Inserindo encontros: Cidadela Sem Sol ===")
    encontros = [
        ("cidadela_0", "Ramo Seco", 2, "60% chance a noite"),
        ("cidadela_1", "Rato Atroz", 3, "sempre"),
        ("cidadela_3", "Rato Atroz", 1, "sempre"),
        ("cidadela_4", "Esqueleto", 3, "perturbar camara"),
        ("cidadela_5", "Esqueleto", 3, "perturbar altar/sarcofago"),
        ("cidadela_6", "Rato Atroz", 1, "se aproximar a 1,5m"),
        ("cidadela_10", "Quasit Jot", 1, "sempre"),
        ("cidadela_12", "Sacerdote-Troll", 1, "sempre"),
        ("cidadela_14", "Mephit da Agua", 1, "sempre"),
        ("cidadela_16", "Kobold Sentinela", 3, "sempre (por area)"),
        ("cidadela_17", "Rato de Caverna", 8, "porta abrir"),
        ("cidadela_19", "Kobold Sentinela", 3, "sempre"),
        ("cidadela_21", "Kobold Sentinela", 6, "sempre"),
        ("cidadela_27", "Esqueleto", 5, "perturbar altar"),
        ("cidadela_28", "Rato Atroz", 3, "perturbar celas B,C,D"),
        ("cidadela_30", "Rato Atroz", 3, "sempre"),
        ("cidadela_30", "Gutash (Rata Grande)", 1, "emboscada"),
        ("cidadela_32", "Goblin Saqueador", 2, "sempre"),
        ("cidadela_33", "Goblin Guerreiro", 4, "sempre"),
        ("cidadela_36", "Goblin Guerreiro", 4, "sempre"),
        ("cidadela_37", "Calcryx (Filhote Dragao)", 1, "sempre"),
        ("cidadela_40", "Goblin Saqueador", 4, "sempre"),
        ("cidadela_40", "Robgoblin Guerreiro", 3, "sempre"),
        ("cidadela_41", "Goblin Guerreiro", 4, "sempre"),
        ("cidadela_41", "Robgoblin Guerreiro", 3, "sempre"),
        ("cidadela_41", "Durnn (Chefe Goblin)", 1, "sempre"),
        ("cidadela_41", "Crenl (Cleriga)", 1, "sempre"),
        ("cidadela_41", "Ramo Seco", 1, "sempre"),
        ("cidadela_42", "Ramo Seco", 2, "sempre"),
        ("cidadela_42", "Esqueleto", 2, "sempre"),
        ("cidadela_43", "Balsag (Bugbear)", 1, "75% chance"),
        ("cidadela_43", "Rato Atroz", 2, "75% chance"),
        ("cidadela_45", "Thoqqua", 1, "sempre"),
        ("cidadela_47", "Goblin Saqueador", 8, "sempre (2 por rodada)"),
        ("cidadela_48", "Bugbear Jardineiro", 1, "sempre"),
        ("cidadela_49", "Goblin Guerreiro", 4, "49a"),
        ("cidadela_49", "Thoqqua", 1, "49b"),
        ("cidadela_49", "Esqueleto", 3, "49c"),
        ("cidadela_49", "Bugbear Jardineiro", 1, "49d"),
        ("cidadela_50", "Sombra", 1, "investigar azulejo vermelho"),
        ("cidadela_54", "Goblin Guerreiro", 4, "sempre"),
        ("cidadela_55", "Ramo Seco", 10, "sempre (1d4 a cada 15m)"),
        ("cidadela_56", "Belak o Proscrito", 1, "boss_final"),
        ("cidadela_56", "Sir Bradford (Corrompido)", 1, "boss_final"),
        ("cidadela_56", "Sharwyn (Corrompida)", 1, "boss_final"),
        ("cidadela_56", "Kulket (Sapo Gigante)", 1, "boss_final"),
        ("cidadela_56", "Ramo Seco", 3, "boss_final + 1d4/2 rodadas"),
    ]
    for e in encontros:
        inserir_encontro(*e)
    print(f"  {len(encontros)} encontros da Cidadela inseridos\n")


def seed_npcs_cidadela():
    print("=== Inserindo NPCs: Cidadela Sem Sol ===")
    npcs = [
        ("cidadela_15", "Meepo", "Kobold guardiao de dragoes. Fala Draconico, Comum e Goblin. Depressivo.", "Perdemos nosso dragao! Por favor, nos ajudem!", "Se recuperarem o dragao, aliado permanente.", "Calcryx"),
        ("cidadela_21", "Yusdrayl", "Feiticeira kobold de 3 nivel. Lider da tribo. Sabe tudo sobre Belak.", "Kobolds sao herdeiros dos dragoes.", "Se recuperarem o dragao: recompensa.", "Calcryx"),
        ("cidadela_34", "Erky Timbers", "Gnomo clerico/guerreiro. Preso ha um ano. Aliado temporario leal.", "Belak cultiva um jardim no Bosque do Crepusculo. A Arvore Gulthias.", "Pede para se unir ao grupo.", "libertacao"),
        ("cidadela_41", "Durnn (Chefe Goblin)", "Robgoblin chefe da tribo Durbuluk. 2 nivel.", "Belak queria prisioneiros humanos vivos. Matei o guerreiro por acidente.", "Anel sinete no dedo (de Talgen).", "anel_sinete"),
        ("cidadela_41", "Crenl (Cleriga)", "Cleriga goblin. 1 nivel. Conjura magias de cura.", "Nos servimos ao Protetor do Bosque.", "Pode curar aliados em combate.", None),
        ("cidadela_43", "Balsag (Bugbear)", "Bugbear cacador de 2 nivel. Gosta de cacar thoqquas.", "Preparem-se para encontrar a pantera!", "Capturou Calcryx.", "Calcryx"),
        ("cidadela_56", "Belak o Proscrito", "Druida humano de 4 nivel. Boss final. Cultiva a Arvore Gulthias.", "A arvore e a fonte de todo o poder.", "Mago: Pele de Arvore, Vinha Enredadora, Invocar Animal.", "Arvore Gulthias"),
        ("cidadela_56", "Sharwyn", "Ex-maga humana. Suplicante da Arvore Gulthias.", "...", "Usa Contra-magia contra magias dos PJs.", None),
        ("cidadela_56", "Sir Bradfod", "Ex-guerreiro humano. Suplicante da Arvore Gulthias.", "...", "Espada Estilhacadora: destroi armas adversarias.", "Espada Estilhacadora"),
    ]
    for n in npcs:
        inserir_npc(*n)
    print(f"  {len(npcs)} NPCs da Cidadela inseridos\n")


def seed_interativos_cidadela():
    print("=== Inserindo interativos: Cidadela Sem Sol ===")
    interativos = [
        ("cidadela_0", "Corda com Nos", "Corda amarrada a pilar inclinado. Permite descer sem dano.", "mecanismo", 0, "STR", []),
        ("cidadela_3", "Alcapao e Fosso", "Alcapao que abre para fossos de 1m. 1d6 dano. CD 16 Reflexos evita.", "armadilha", 16, "DEX", [], 6),
        ("cidadela_5", "Agulha Envenenada", "Sob o veneno: CD 20 detectar. 1d4 CON temporario.", "armadilha", 20, "PER", [], 4),
        ("cidadela_7", "Globo Musical", "Globo de bronze emite notas altas. CD 18 Vontade.", "armadilha", 18, "WIS", []),
        ("cidadela_8", "Placa de Pressao", "Dispara setas. CD 21 Procurar.", "armadilha", 21, "PER", [], 6),
        ("cidadela_9", "Enigma do Dragao", "Escultura fala enigma. Resposta: Bruma.", "enigma", 0, "INT", []),
        ("cidadela_10", "Fosso com Estacas", "1m profundidade. 1d6 + 1d4. CD 16 Escalar/Salto.", "armadilha", 16, "STR", [], 10),
        ("cidadela_14", "Porta de Peixe Draconico", "CD 21 Abrir Fechaduras.", "porta", 21, "DES", []),
        ("cidadela_24", "Fosso Dissuasorio", "3m profundidade. CD 16 Reflexos evita.", "armadilha", 16, "DEX", [], 6),
        ("cidadela_27", "Porta do Santuario", "So abre com Expulsar Mortos-Vivos (afeta 2 DV).", "porta", 0, "WIS", []),
        ("cidadela_29", "Armadilha Naruhune", "CD 14 Fortitude. 1d4 CON temporario.", "armadilha", 14, "CON", [], 4),
        ("cidadela_31", "Sino na Porta", "CD 21 Procurar.", "armadilha", 21, "PER", []),
        ("cidadela_31", "Estrepe no Chao", "Metade do deslocamento. 1d4 por passo.", "armadilha", 10, "DES", [], 4),
        ("cidadela_35", "Fosso Goblin", "3m. CD 16 Reflexos evita.", "armadilha", 16, "DEX", [], 6),
        ("cidadela_37", "Porta Lacrada em Osso", "Inscricao Kathundin.", "tesouro", 0, "INT", ["Pergaminho antigo (100 PO)"]),
        ("cidadela_41", "Arca com Armadilha", "Agulha envenenada: CD 18. 1d4 CON temporario.", "armadilha", 18, "CON", ["230 PO", "2 gemas onix (30 PO)", "2 antidotos", "Pergaminho Barkskin", "Pocao de Cura"], 4),
        ("cidadela_50", "Azulejo de Pedra Vermelha", "Runas Draconicas: +1d4+1 Carisma por 24 horas.", "magia", 0, "INT", ["+1d4+1 Carisma por 24h"]),
        ("cidadela_56", "Fruto da Arvore Gulthias", "Vermelho-rubi: Cur Comleta. Branco: Palavra de Matar.", "tesouro", 0, "INT", ["Fruto da Arvore Gulthias"]),
    ]
    for i in interativos:
        inserir_interativo(*i)
    print(f"  {len(interativos)} interativos da Cidadela inseridos\n")


# PHANDELVER - Localizacoes
def seed_phandalin():
    print("=== Inserindo salas: Phandalin ===")
    salas = [
        ("phandalin", "Vila de Phandalin", "Vila mineradora. 1200 habitantes. Casas e oficinas arruinadas.", {"sul": "taverna", "norte": "trilha_triboar", "oeste": "conyberry", "leste": "cidadela_0", "nordeste": "castelo_entrada", "sudoeste": "onda_eco_entrada"}, []),
        ("taverna", "Taverna do Velho Javali", "Taverneiro robusto de avental de couro. O ponto de encontro dos aventureiros. Cerveja, hidromel e ensopado. Fale com o Taverneiro para informacoes sobre as aventuras.", {"norte": "cidadela_0", "leste": "onda_eco_entrada", "sul": "estalagem_colina"}, ["Cerveja: 2 PP", "Hidromel: 2 PP", "Comida: 5 PP"]),
        ("phandalin_escritorio", "Escritorio de Edric Barthen", "Maleta de viajante. Barthen pode dar equipamento a credito (max 25 PO).", {"volta": "phandalin"}, ["Equipamento (credito 25 PO)"]),
        ("phandalin_templo", "Templo de Tyr", "Padre Haliah. Oferendas, velas, vinho.", {"volta": "phandalin"}, ["Pocao de Cura (poco)"]),
        ("phandalin_pomar", "Pomar de Sildar", "Sildar Hallwinter (18 PV, CA 18). Oferece 100 PO para recuperar suprimentos.", {"volta": "phandalin"}, ["Suprimentos recuperados"]),
        ("phandalin_ferreiro", "Ferraria de Linene", "Ferraria funcional. Armas e armaduras disponiveis.", {"volta": "phandalin"}, ["Armas e armaduras"]),
        ("estalagem_colina", "Estalagem Colina de Pedra", "Dona Linene serve comida e bebida. Camas confortaveis para descansar. Recupera HP e magias.", {"norte": "taverna"}, ["Cama: 7 PP", "Descanso: recupera HP e magias"]),
    ]
    for s in salas:
        inserir_cena(*s)
    print(f"  {len(salas)} salas de Phandalin inseridas\n")


def seed_trilha_triboar():
    print("=== Inserindo sala: Trilha Triboar ===")
    inserir_cena("trilha_triboar", "Trilha Triboar (A Emboscada)", "Trilha de terra batida. Troncos derrubados. Cavalos mortos. 4 Goblins e 1 Bugbear armam emboscada.", {"sul": "phandalin", "leste": "esconderijo_entrada"}, [], ["Emboscada: Goblins nos arbustos + Bugbear flanqueia"])
    print("  1 sala da Trilha Triboar inserida\n")


def seed_esconderijo():
    print("=== Inserindo salas: Esconderijo Dentefino (8 areas) ===")
    salas = [
        ("esconderijo_entrada", "1. Entrada da Caverna", "Caverna natural. Riacho de agua gelada. Lobos amarrados a correntes.", {"dentro": "esconderijo_passagem"}, [], ["Lobos hostis"]),
        ("esconderijo_passagem", "2. Passagem dos Goblins", "Tunel de 9m. Duas estatuas de pedra. Emboscada.", {"volta": "esconderijo_entrada", "porta": "esconderijo_lobos"}, [], ["Emboscada: 2 Goblins + Bugbear"]),
        ("esconderijo_lobos", "3. Poco dos Lobos", "Salao com teto alto. 6 lobos em jaulas. 3 Goblins + 1 Bugbear.", {"volta": "esconderijo_passagem", "portas": "esconderijo_fissura, esconderijo_ponte"}, [], ["Lobos atacam se soltos"]),
        ("esconderijo_fissura", "4. Passagem Ingrime", "Fenda angulosa. 3 Goblins descem rapidamente.", {"volta": "esconderijo_lobos", "fissura": "esconderijo_covil"}, [], ["Derrubam rochas (CD 12, 1d6)"]),
        ("esconderijo_ponte", "5. Passagem Superior", "Fenda com ponte de 15m. Goblins atiram com arcos. 4 Goblins + 1 Bugbear.", {"volta": "esconderijo_lobos", "ponte": "esconderijo_covil"}, [], ["Atiram com arcos. Quebram ponte"]),
        ("esconderijo_covil", "6. Covil dos Goblins", "Grande caverna. 6 Goblins + 1 Bugbear + 1 Grot. Sino de bronze.", {"volta": "esconderijo_lobos", "portas": "esconderijo_fontes, esconderijo_klarg"}, ["20 PO", "Adaga entalhada", "Espada Larga", "Escudo de Ferro", "Cota de Malha", "Pergaminho Cura Leve", "Bolsa com 25 PO"], ["Grot: 75% chance de falar"]),
        ("esconderijo_fontes", "7. Caverna das Fontes Gemeas", "Duas fontes com agua gelada. Teto baixo. Ratos Atrozes (2d4).", {"volta": "esconderijo_covil"}, ["1d20+10 PP em 2d8-1 sacos"], ["Ratos: atacam sem aviso"]),
        ("esconderijo_klarg", "8. Caverna de Klarg", "Caverna ampla. Klarg (Bugbear), 2 Goblins, Filhote Dragao Verde, Gosma Ocre.", {"volta": "esconderijo_covil"}, ["200 PO", "150 PO"], ["Filhote: sopro veneno (CD 13, 3d6 veneno)"]),
    ]
    for s in salas:
        inserir_cena(*s)
    print(f"  {len(salas)} salas do Esconderijo inseridas\n")


def seed_marcarrubra():
    print("=== Inserindo salas: Esconderijo Marcarrubra (12 areas) ===")
    salas = [
        ("marcarrubra_porao", "1. Porao dos Tresendar", "Porao em ruinas. Escritorio de Glasstaff. Arca com 23 PO.", {"subir": "mansao_tresendar", "escada": "marcarrubra_corredor"}, ["23 PO"]),
        ("marcarrubra_corredor", "2. Corredor das Armadilhas", "Corredor de pedra. Armadilhas: rede (CD 14) e fogo (CD 13, 2d6 fogo).", {"volta": "marcarrubra_porao", "porta": "marcarrubra_barracas"}, [], ["Rede: CD 14, 1d4+1", "Fogo: CD 13, 2d6 fogo"]),
        ("marcarrubra_barracas", "3. Barracas dos Bandidos", "Sala ampla. 4 Bandidos + 1 Hobgoblin.", {"portas": "marcarrubra_corredor, marcarrubra_criptas, marcarrubra_prisao"}, ["35 PO"], ["Alarme em 1 minuto"]),
        ("marcarrubra_criptas", "4. Criptas dos Tresendar", "4 sarcofagos. Fantasma de Nell. Ghoul nos escombros.", {"porta": "marcarrubra_barracas"}, ["Anel de Prata (25 PO)", "Gema (50 PO)", "Pocao de Cura"], ["Ghoul: paralisia"]),
        ("marcarrubra_prisao", "5. Celas dos Escravos", "Duas celas. 3 homens, 2 mulheres, 1 crianca.", {"porta": "marcarrubra_barracas"}, [], ["Escravos pedem ajuda"]),
        ("marcarrubra_saguao", "6. Sagao", "Salao principal. Mesa comprida. 4 Goblins.", {"portas": "marcarrubra_barracas, marcarrubra_torre"}, ["45 PO"], ["Alarme"]),
        ("marcarrubra_torre", "7. Torre em Ruinas", "Torre sem telhado. 2 Hobgoblins + 1 Doppelganger.", {"porta": "marcarrubra_saguao", "escada": "marcarrubra_torre_topo"}, ["15 PO"]),
        ("marcarrubra_fenda", "8. A Fenda", "Caverna natural com fenda. 2 Bandidos + 2 Arañas.", {"volta": "marcarrubra_corredor"}, ["45 PO"], ["Envenenamento"]),
        ("marcarrubra_templo", "9. Templo Profanado", "Ruinas de templo. 3 Aparicoes Mormesk. 200 PO.", {"porta": "marcarrubra_corredor"}, ["200 PO"], ["Aparicao: 3d8+3 necrotico"]),
        ("marcarrubra_estalactites", "10. Caverna das Estalactites", "Estalactites afiadas. Fissura com tesouro.", {"portas": "marcarrubra_corredor, marcarrubra_mina"}, ["20 PO", "Pocao de Cura"]),
        ("marcarrubra_mina", "11. Entrada da Mina", "Entrada da Mina de Phandelver. Equipamento de mineracao. Esqueletos.", {"volta": "marcarrubra_estalactites"}),
        ("marcarrubra_glasstaff", "12. Aposentos de Glasstaff", "Balcenao. Arca trancada (CD 20). Pergaminho Identificacao.", {"volta": "marcarrubra_corredor"}, ["Pocao de Cura", "Pocao de Cura Maior", "Pergaminho Identificacao"], ["Arca trancada (CD 20)"]),
    ]
    for s in salas:
        inserir_cena(*s)
    print(f"  {len(salas)} salas do Marcarrubra inseridas\n")


def seed_conyberry():
    print("=== Inserindo sala: Conyberry ===")
    inserir_cena("conyberry", "Ruinas de Conyberry e Covil de Agatha", "Ruinas de templo. Covil de Agatha (Fada Arquetipa). 3 Urso Coruja na floresta.", {"leste": "phandalin", "oeste": "poco_coruja"}, ["Informacoes (se persuadir Agatha)"], ["Urso Coruja: 59 PV, CA 13"])
    print("  1 sala de Conyberry inserida\n")


def seed_poco_coruja():
    print("=== Inserindo sala: Poco da Coruja Velha ===")
    inserir_cena("poco_coruja", "Poco da Coruja Velha", "Poco profundo (15m). Coruja Velha (Mormesk). Tesouro de 100 PO.", {"leste": "conyberry"}, ["100 PO"], ["Mormesk: 3d8+3 necrotico"])
    print("  1 sala do Poco da Coruja inserida\n")


def seed_cume_wyvern():
    print("=== Inserindo sala: Cume da Wyvern ===")
    inserir_cena("cume_wyvern", "Cume da Wyvern", "Rochedo elevado. Ninhos de Wyvern. 3 Urso Coruja e 1 Wyvern.", {"leste": "conyberry"}, ["Diamante (100 PO)", "Rubis (150 PO)"], ["Wyvern: fenda 4d6+2"])
    print("  1 sala do Cume da Wyvern inserida\n")


def seed_arvore_trovao():
    print("=== Inserindo salas: Arvore Trovao (5 areas) ===")
    salas = [
        ("arvore_trovao_entrada", "Entrada da Arvore Trovao", "Raizes de uma arvore gigante.", {"dentro": "arvore_trovao_boticario"}),
        ("arvore_trovao_boticario", "Antiga Loja do Boticario", "Estantes. Frascos quebrados. Equipamento de boticario.", {"volta": "arvore_trovao_entrada", "porta": "arvore_trovao_torre"}, ["Pocao de Cura", "Pergaminho Curar Ferimentos", "Balsamo"]),
        ("arvore_trovao_torre", "A Torre do Dragao", "Torre parcialmente derrubada. Escada em espiral. Tesouro.", {"escada": "arvore_trovao_boticario", "porta": "arvore_trovao_tesouro"}, ["Espada Longa +1", "Pocao de Forca", "Pedra Preciosa (100 PO)"], ["Ogro: investida +6, 2d8+4"]),
        ("arvore_trovao_tesouro", "Cofre da Torre", "Cofre. Douradas. Pergaminhos.", {"volta": "arvore_trovao_torre"}, ["500 PO", "3 Gemas (200 PO)", "Cajado da Defesa", "Pergaminho Identificacao"], ["Armadilha: flecha (CD 15, 2d6)"]),
        ("arvore_trovao_floresta", "Floresta ao Redor", "Floresta densa. Urso Coruja na copa.", {"volta": "arvore_trovao_entrada"}, [], ["Urso Coruja: 59 PV, CA 13"]),
    ]
    for s in salas:
        inserir_cena(*s)
    print(f"  {len(salas)} salas da Arvore Trovao inseridas\n")


def seed_castelo_dentefino():
    print("=== Inserindo salas: Castelo Dentefino (6 areas) ===")
    salas = [
        ("castelo_entrada", "Portoes do Castelo", "Portoes reforcados. Muralhas. Guardas goblinoides.", {"dentro": "castelo_saguao"}, [], ["Guardas: 2 Hobgoblins + 4 Goblins"]),
        ("castelo_saguao", "1. Sagao do Castelo", "Salao amplo. Fogueira. 6 Goblins + 2 Hobgoblins.", {"portas": "castelo_refeitorio, castelo_torre_urso"}, ["45 PO"], ["Alarme em 1 minuto"]),
        ("castelo_refeitorio", "2. Refeitorio Goblinoid", "Mesa comprida. 8 Goblins + 1 Bugbear.", {"portas": "castelo_saguao, castelo_santuario"}, ["25 PO"], ["Reforcos"]),
        ("castelo_torre_urso", "3. Torre do Urso", "Torre em ruinas. 2 Hobgoblins. Escada.", {"escada": "castelo_saguao", "porta": "castelo_aposentos"}, ["15 PO"]),
        ("castelo_santuario", "4. O Santuario Profanado", "Altar destruido. 3 Zumbis + 1 Zumbi das Cinzas.", {"porta": "castelo_refeitorio"}, ["Adaga +1", "Pocao de Cura"], ["Zumbi das Cinzas: brisa"]),
        ("castelo_aposentos", "5. Aposentos do Rei Grol", "Sala ampla. Arca. Rei Grol (Bugbear), Doppelganger, 2 Hobgoblins, 2 Goblins.", {"porta": "castelo_torre_urso"}, ["600 PO", "Peitoral Dragao (CA 18)"], ["Boss: Grol 45 PV, CA 16"]),
    ]
    for s in salas:
        inserir_cena(*s)
    print(f"  {len(salas)} salas do Castelo Dentefino inseridas\n")


def seed_onda_eco():
    print("=== Inserindo salas: Caverna Onda Eco (16 areas) ===")
    salas = [
        ("onda_eco_entrada", "1. Entrada da Caverna", "Entrada na rocha. Equipamento de mineracao. Duas campainhas. As Minas de Phandelver.", {"oeste": "taverna", "dentro": "onda_eco_tuneis"}, [], ["Campainhas: alarmam"]),
        ("onda_eco_tuneis", "Tuneis da Mina", "Corredores estreitos. 4 Goblins patrulham.", {"volta": "onda_eco_entrada", "portas": "onda_eco_fungos, onda_eco_grande_caverna"}, [], ["Patrulhas"]),
        ("onda_eco_fungos", "Caverna dos Fungos", "Fungos luminosos. Aranha Gigante. 2 Goblins.", {"volta": "onda_eco_tuneis"}, ["30 PO"], ["Aranha: veneno"]),
        ("onda_eco_grande_caverna", "9. A Grande Caverna", "Sala principal. 20 Goblins + 2 Hobgoblins + 1 Bugbear. Aranha Gigante.", {"portas": "onda_eco_tuneis, onda_eco_fornalha, onda_eco_piscina"}, ["150 PO"], ["Alarme: todos alertam"]),
        ("onda_eco_fornalha", "12. Caverna da Fornalha", "Fornalha de fundicao. Ferreiro.", {"porta": "onda_eco_grande_caverna", "porta_secreta": "onda_eco_aposentos"}, ["Ferramentas de fundicao"]),
        ("onda_eco_aposentos", "14. Aposentos dos Magos", "Estantes. Pergaminhos. 3 Cultistas.", {"porta": "onda_eco_fornalha", "porta": "onda_eco_forja"}, ["Pergaminho Armadilhas", "Pergaminho Identificacao", "Pergaminho Missis Magicos"], ["Cultistas: adagas + veneno"]),
        ("onda_eco_forja", "15. A Forja das Magias", "Fornalha magica. 2 Cultistas + 1 Ogro.", {"porta": "onda_eco_aposentos"}, ["Manoplas Poder Ogro", "Espada Curta +1 Hew"], ["Ogro: investida +6"]),
        ("onda_eco_piscina", "10. Piscina Escura", "Agua parada. Lixo. Tesouro escondido.", {"porta": "onda_eco_grande_caverna", "porta": "onda_eco_templo"}, ["50 PO"], ["Agua contaminada"]),
        ("onda_eco_templo", "19. Templo de Dumathoin", "Templo subterraneo. Altar. Cranio em Chamas. Estatua de Augurio.", {"porta": "onda_eco_piscina"}, ["Cranio em Chamas", "Estatua de Augurio", "Maca +1"], ["Cranio: 3d6 fogo"]),
        ("onda_eco_goblins", "Goblin Camp", "Barracas. 8 Goblins + 2 Hobgoblins.", {"portas": "onda_eco_tuneis, onda_eco_estreitas"}, ["100 PO"], ["Alarme"]),
        ("onda_eco_estreitas", "Passagens Estreitas", "Corredores apertados. Armadilhas.", {"portas": "onda_eco_goblins, onda_eco_mina_escura"}, [], ["Armadilha: rochas (CD 14, 2d6)"]),
        ("onda_eco_mina_escura", "Mina Escura", "Escuro total. 4 Goblins + 1 Bugbear.", {"porta": "onda_eco_estreitas"}, ["80 PO"]),
        ("onda_eco_coluna", "Coluna de Pedra", "Grande coluna de pedra. Passagem ao redor.", {"portas": "onda_eco_mina_escura, onda_eco_espirituais"}),
        ("onda_eco_espirituais", "Spiritus Animae", "Espiritos. 3 Esqueletos + 1 Zumbi.", {"porta": "onda_eco_coluna"}, ["45 PO"], ["Zumbi: resistencia"]),
        ("onda_eco_basilisco", "Goblin Guerreiro", "Caverna com basilisco. 4 Goblins + 1 Hobgoblin + 1 Basilisco.", {"porta": "onda_eco_espirituais"}, ["75 PO"], ["Basilisco: pedra (CD 14)"]),
        ("onda_eco_nezznar", "Aranha Negra - BOSS FINAL", "Salao do tesouro. Nezznar (Drow Mage 4). 4 Aranhas Gigantes + 2 Cultistas + 2 Zumbis.", {"ponto_final": "Fim da aventura"}, ["Cajado Aranha", "Maca +1", "Pocao Cura Maior", "Manoplas Poder Ogro", "Espada Curta +1 Hew", "Botas Correr/Saltar", "Varinha Missis Magicos", "2000 PO"], ["Boss: Nezznar 27 PV, CA 11"]),
    ]
    for s in salas:
        inserir_cena(*s)
    print(f"  {len(salas)} salas da Onda Eco inseridas\n")


# Encontros de Phandelver
def seed_encontros_phandelver():
    print("=== Inserindo encontros: Phandelver ===")
    encontros = [
        ("trilha_triboar", "Goblin", 4, "emboscada"),
        ("trilha_triboar", "Bugbear", 1, "emboscada"),
        ("esconderijo_entrada", "Lobo", 2, "sempre"),
        ("esconderijo_passagem", "Goblin", 2, "emboscada"),
        ("esconderijo_passagem", "Bugbear", 1, "emboscada"),
        ("esconderijo_lobos", "Goblin", 3, "sempre"),
        ("esconderijo_lobos", "Bugbear", 1, "sempre"),
        ("esconderijo_lobos", "Lobo", 6, "se soltarem"),
        ("esconderijo_fissura", "Goblin", 3, "sempre"),
        ("esconderijo_ponte", "Goblin", 4, "sempre"),
        ("esconderijo_ponte", "Bugbear", 1, "sempre"),
        ("esconderijo_covil", "Goblin", 6, "sempre"),
        ("esconderijo_covil", "Bugbear", 1, "sempre"),
        ("esconderijo_fontes", "Rato Atroz", 4, "perturbar"),
        ("esconderijo_klarg", "Bugbear", 1, "Klarg"),
        ("esconderijo_klarg", "Goblin", 2, "sempre"),
        ("esconderijo_klarg", "Aranha Gigante", 1, "sempre"),
        ("esconderijo_klarg", "Gosma Ocre", 1, "sempre"),
        ("marcarrubra_corredor", "Bandido Marcarrubra", 2, "emboscada"),
        ("marcarrubra_barracas", "Bandido Marcarrubra", 4, "sempre"),
        ("marcarrubra_barracas", "Hobgoblin", 1, "sempre"),
        ("marcarrubra_criptas", "Ghoul", 1, "perturbar sarcofago"),
        ("marcarrubra_saguao", "Goblin", 4, "sempre"),
        ("marcarrubra_torre", "Hobgoblin", 2, "sempre"),
        ("marcarrubra_torre", "Doppelganger", 1, "sempre"),
        ("marcarrubra_fenda", "Bandido Marcarrubra", 2, "sempre"),
        ("marcarrubra_templo", "Aparicao Mormesk", 3, "perturbar sarcofago"),
        ("marcarrubra_glasstaff", "Hobgoblin", 2, "sempre"),
        ("conyberry", "Urso Coruja", 3, "na floresta"),
        ("poco_coruja", "Aparicao Mormesk", 1, "perturbar poco"),
        ("cume_wyvern", "Wyvern", 3, "sempre"),
        ("cume_wyvern", "Wyvern", 1, "sempre"),
        ("arvore_trovao_torre", "Ogro", 1, "sempre"),
        ("arvore_trovao_floresta", "Urso Coruja", 1, "na copa"),
        ("castelo_entrada", "Hobgoblin", 2, "guardas"),
        ("castelo_entrada", "Goblin", 4, "guardas"),
        ("castelo_saguao", "Goblin", 6, "sempre"),
        ("castelo_saguao", "Hobgoblin", 2, "sempre"),
        ("castelo_refeitorio", "Goblin", 8, "sempre"),
        ("castelo_refeitorio", "Bugbear", 1, "sempre"),
        ("castelo_torre_urso", "Hobgoblin", 2, "sempre"),
        ("castelo_santuario", "Zumbi", 3, "perturbar"),
        ("castelo_santuario", "Zumbi das Cinzas", 1, "perturbar"),
        ("castelo_aposentos", "Rei Grol (Bugbear)", 1, "boss_final"),
        ("castelo_aposentos", "Doppelganger", 1, "boss_final"),
        ("castelo_aposentos", "Hobgoblin", 2, "boss_final"),
        ("castelo_aposentos", "Goblin", 2, "boss_final"),
        ("onda_eco_fungos", "Aranha Gigante", 1, "sempre"),
        ("onda_eco_grande_caverna", "Goblin", 20, "sempre"),
        ("onda_eco_grande_caverna", "Hobgoblin", 2, "sempre"),
        ("onda_eco_grande_caverna", "Bugbear", 1, "sempre"),
        ("onda_eco_aposentos", "Cultista", 3, "sempre"),
        ("onda_eco_forja", "Cultista", 2, "sempre"),
        ("onda_eco_forja", "Ogro", 1, "sempre"),
        ("onda_eco_templo", "Crânio em Chamas", 1, "sempre"),
        ("onda_eco_goblins", "Goblin", 8, "sempre"),
        ("onda_eco_goblins", "Hobgoblin", 2, "sempre"),
        ("onda_eco_espirituais", "Esqueleto Armado", 3, "perturbar"),
        ("onda_eco_espirituais", "Zumbi", 1, "perturbar"),
        ("onda_eco_basilisco", "Basilisco", 1, "sempre"),
        ("onda_eco_basilisco", "Goblin", 4, "sempre"),
        ("onda_eco_basilisco", "Hobgoblin", 1, "sempre"),
        ("onda_eco_nezznar", "Nezznar (Aranha Negra)", 1, "boss_final"),
        ("onda_eco_nezznar", "Aranha Gigante", 4, "boss_final"),
        ("onda_eco_nezznar", "Cultista", 2, "boss_final"),
        ("onda_eco_nezznar", "Zumbi", 2, "boss_final"),
    ]
    for e in encontros:
        inserir_encontro(*e)


# ═══════════════════════════════════════════════════════════════
# IMAGENS - Vincula imagens do imagens_config.py
# ═══════════════════════════════════════════════════════════════
def seed_npcs_phandelver():
    print("=== Inserindo NPCs: Phandelver ===")
    npcs = [
        ("phandalin", "Sildar Hallwinter", "Humano, Guardiao de Linha. 18 PV, CA 18. Busca Grol e Glock.", "Preciso de ajuda! Meus suprimentos foram roubados. 100 PO para quem recuperar.", "Conhece Phandalin. Pode ajudar em futuras missoes.", "suprimentos"),
        ("phandalin", "Edric Barthen", "Humano, Mercador. Carregador de suprimentos.", "Barthen e um homem justo. Sempre paga seus trabalhadores.", "Pode fornecer equipamento a credito.", None),
        ("taverna", "Taverneiro do Velho Javali", "Homem robusto de avental de couro. Dono da Taverna do Velho Javali. Sabe de tudo que acontece na regiao.", "Bem-vindos a Taverna do Velho Javali! A norte fica a Estrada Velha para a Cidadela Sem Sol. A leste, a entrada das Minas de Phandelver (Wave Echo Cave). Se precisar descansar, va a Estalagem da Colina de Pedra a sul.", "Se quiser informacoes sobre as aventuras, pergunte. Se precisar descansar, va a Estalagem.", None),
        ("phandalin", "Padre Haliah", "Humano, Clerigo de Tyr. Templo de Tyr.", "Tyr protege os justos. Posso curar seus ferimentos.", "Cura ferimentos por oracoes.", None),
        ("esconderijo_entrada", "Klarg", "Bugbear. Lider do esconderijo. Covarde.", "Eu sou Klarg! Ninguem me derrota!", "Foge se derrotado.", None),
        ("marcarrubra_glasstaff", "Glasstaff (Iarno Albrek)", "Humano, Mago corrompido. Lidera bandidos.", "Voces nao deveriam ter vindo aqui!", "Pergaminho de Cura Maior.", None),
        ("conyberry", "Agatha", "Fada Arquetipa. Conhece segredos de laminas.", "O que queres saber, mortal?", "Pode revelar informacoes sobre laminas encantadas.", None),
        ("poco_coruja", "Mormesk", "Aparicao. Ex-ladino. Guarda tesouro de 100 PO.", "Quem perturba meu descanso?", "Tesouro: 100 PO.", None),
        ("castelo_aposentos", "Rei Grol", "Bugbear. Lider do Castelo Dentefino. 45 PV, CA 16.", "Ninguem entra no meu castelo e sai vivo!", "Boss: 45 PV, CA 16.", None),
        ("onda_eco_nezznar", "Nezznar, A Aranha Negra", "Drow Mage 4 nivel. Boss final.", "Voces estao atrasados! A forja ja e minha!", "Boss: 27 PV, CA 11.", None),
    ]
    for n in npcs:
        inserir_npc(*n)
    print(f"  {len(npcs)} NPCs de Phandelver inseridos\n")


def vincular_imagens():
    """Atualiza imagem_url das cenas com os paths locais do imagens_config.py"""
    print("=== Vinculando imagens ===")
    from imagens_config import IMAGENS_CENAS
    count = 0
    for cod, url in IMAGENS_CENAS.items():
        if cod == "_default":
            continue
        cur.execute("UPDATE cenas SET imagem_url = %s WHERE cod_sala = %s", (url, cod))
        if cur.rowcount > 0:
            count += 1
    print(f"  {count} imagens vinculadas\n")


# ═══════════════════════════════════════════════════════════════
# VERIFICACAO DE INTEGRIDADE
# ═══════════════════════════════════════════════════════════════
def verificar_integridade():
    print("=== Verificacao de Integridade ===")
    erros = []
    
    # 1. Encontros sem sala correspondente
    cur.execute("""
        SELECT DISTINCT e.cod_sala 
        FROM encontros e 
        LEFT JOIN cenas c ON e.cod_sala = c.cod_sala 
        WHERE c.cod_sala IS NULL
    """)
    orfas = cur.fetchall()
    if orfas:
        erros.append(f"  ERRO: {len(orfas)} encontros apontam para salas inexistentes: {[r[0] for r in orfas]}")
    
    # 2. NPCs sem sala correspondente
    cur.execute("""
        SELECT DISTINCT n.cod_sala 
        FROM npcs n 
        LEFT JOIN cenas c ON n.cod_sala = c.cod_sala 
        WHERE c.cod_sala IS NULL
    """)
    orfas = cur.fetchall()
    if orfas:
        erros.append(f"  ERRO: {len(orfas)} NPCs apontam para salas inexistentes: {[r[0] for r in orfas]}")
    
    # 3. Inimigos referenciados mas nao existentes
    cur.execute("""
        SELECT DISTINCT e.nome_inimigo 
        FROM encontros e 
        LEFT JOIN inimigos i ON e.nome_inimigo = i.nome 
        WHERE i.nome IS NULL
    """)
    faltando = cur.fetchall()
    if faltando:
        erros.append(f"  ERRO: {len(faltando)} inimigos referenciados mas nao cadastrados: {[r[0] for r in faltando]}")
    
    # 4. Salas sem nenhum encontro
    cur.execute("""
        SELECT c.cod_sala, c.nome_sala 
        FROM cenas c 
        LEFT JOIN encontros e ON c.cod_sala = e.cod_sala 
        WHERE e.cod_sala IS NULL
    """)
    vazias = cur.fetchall()
    if vazias:
        print(f"  AVISO: {len(vazias)} salas sem encontros (pode ser normal): {[r[1] for r in vazias]}")
    
    # 5. Contagem geral
    cur.execute("SELECT COUNT(*) FROM aventuras"); n_avent = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM cenas"); n_cenas = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM inimigos"); n_inim = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM encontros"); n_enc = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM npcs"); n_npcs = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM interativos"); n_int = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM cenas WHERE imagem_url != '' AND imagem_url IS NOT NULL"); n_img = cur.fetchone()[0]
    
    print(f"\n  RESUMO:")
    print(f"    Aventuras: {n_avent}")
    print(f"    Cenas/Salas: {n_cenas}")
    print(f"    Inimigos (unicos): {n_inim}")
    print(f"    Encontros (ocorrencias): {n_enc}")
    print(f"    NPCs: {n_npcs}")
    print(f"    Interativos: {n_int}")
    print(f"    Cenas com imagem: {n_img}/{n_cenas}")
    
    if erros:
        print(f"\n  === {len(erros)} ERROS ENCONTRADOS ===")
        for e in erros:
            print(e)
        return False
    else:
        print("\n  INTEGRIDADE OK - Nenhum erro critico encontrado")
        return True


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
def main():
    print("=" * 60)
    print("  SEED COMPLETO - Aventuras MezzaRPG")
    print("  Conectando ao VPS PostgreSQL...")
    print("=" * 60 + "\n")
    
    # 1. Limpar tabelas
    limpar_tabelas()
    
    # 2. Inserir inimigos
    seed_inimigos()
    
    # 3. Cidadela Sem Sol
    seed_cidadela()
    seed_encontros_cidadela()
    seed_npcs_cidadela()
    seed_interativos_cidadela()
    
    # 4. A Mina Perdida de Phandelver
    seed_phandalin()
    seed_trilha_triboar()
    seed_esconderijo()
    seed_marcarrubra()
    seed_conyberry()
    seed_poco_coruja()
    seed_cume_wyvern()
    seed_arvore_trovao()
    seed_castelo_dentefino()
    seed_onda_eco()
    seed_encontros_phandelver()
    seed_npcs_phandelver()
    
    # 5. Vincular imagens
    vincular_imagens()
    
    # 6. Verificar integridade
    ok = verificar_integridade()
    
    # 7. Commit final
    if ok:
        conn.commit()
        print("\n" + "=" * 60)
        print("  SEED CONCLUIDO COM SUCESSO!")
        print("=" * 60)
    else:
        conn.rollback()
        print("\n  ERROS DETECTADOS - Rollback (nenhum dado alterado)")
    
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
