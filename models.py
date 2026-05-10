from sqlalchemy import Column, String, Integer, JSON, Boolean, Text
from sqlalchemy.ext.mutable import MutableDict
from database import Base

class Jogador(Base):
    __tablename__ = "jogadores"
    telefone = Column(String, primary_key=True)
    
    # ── MULTIPLAYER & LOCALIZAÇÃO ──
    party_id = Column(String, index=True, nullable=True) # Ex: "XTY-9A"
    cena_atual = Column(String, default="carvalhal") # Movido da Campanha para permitir separação do grupo
    cena_anterior = Column(String, nullable=True)
    
    nome = Column(String)
    sexo = Column(String, nullable=True)
    classe = Column(String)
    raca = Column(String)
    background = Column(String)
    
    # Nível e XP
    nivel = Column(Integer, default=1)
    xp = Column(Integer, default=0)

    # Vida
    hp_atual = Column(Integer)
    hp_maximo = Column(Integer)

    # Atributos brutos
    str_val = Column('str', Integer)
    dex_val = Column('dex', Integer)
    con_val = Column('con', Integer)
    int_val = Column('int', Integer)
    wis_val = Column('wis', Integer)
    cha_val = Column('cha', Integer)

    # Modificadores
    mod_str = Column(Integer)
    mod_dex = Column(Integer)
    mod_con = Column(Integer)
    mod_int = Column(Integer)
    mod_wis = Column(Integer)
    mod_cha = Column(Integer)

    # Combate e Defesa
    modificador_ataque = Column(Integer)
    modificador_defesa = Column(Integer)
    proficiencia = Column(Integer, default=2)
    
    # Equipamento Ativo
    arma_equipada = Column(String, default="Desarmado")
    armadura_equipada = Column(String, default="Trajes Comuns")
    dano_dado = Column(String, default="1d4")
    mod_dano = Column(Integer, default=0)

    # Recursos
    gold = Column(Integer, default=15)
    inventario = Column(JSON, default=list)
    slots_magia = Column(Integer, default=0)
    slots_magia_max = Column(Integer, default=0)
    descanso_curto_disponivel = Column(Boolean, default=True)

    # ── NOVO: DADOS DE VIDA (Hit Dice) ──
    hit_dice_max = Column(Integer, default=1)
    hit_dice_atual = Column(Integer, default=1)

    # Efeitos de Status
    status_efeitos = Column(JSON, default=list) # Ex: ["Envenenado", "Atordoado", "Cobertura", "Agarrado", "Caído"]

class Aventura(Base):
    __tablename__ = "aventuras"
    id = Column(String(50), primary_key=True)
    nome = Column(String(100))
    prologo = Column(Text)

class Campanha(Base):
    __tablename__ = "campanhas"
    
    # ── MULTIPLAYER LOBBY ──
    party_id = Column(String, primary_key=True, index=True) # Identificador do grupo
    host_id = Column(String, nullable=False) # Quem manda no /reset_campanha
    aventura_ativa = Column(String, default="cidadela") # CORREÇÃO AQUI: "cidadela" para bater com o ID do banco
    
    # MutableDict: SQLAlchemy rastreia alterações profundas no JSON automaticamente
    estado_salas = Column(MutableDict.as_mutable(JSON), default=dict) 
    ultimo_evento = Column(MutableDict.as_mutable(JSON), default=dict)
    momento = Column(String, default="inicio")
    tensao = Column(Integer, default=0)
    turno_atual = Column(Integer, default=1)
    
    # ── FILA DE INICIATIVA E COMBATE ──
    em_combate = Column(Boolean, default=False)
    fila_iniciativa = Column(JSON, default=list)
    indice_turno = Column(Integer, default=0)
    
    # ── COLUNAS RESTAURADAS PARA O MAIN.PY ──
    cena_atual = Column(String, default="carvalhal")
    cena_anterior = Column(String, nullable=True)
    status = Column(String, default="exploracao")
    votos_destino = Column(JSON, default=dict) # CORREÇÃO AQUI: default=dict

    # ── NOVO: BOLSA DA PARTY ──
    # Guardará ouro acumulado e itens coletados durante a exploração
    # Exemplo: {"ouro": 150, "itens": ["Espada Longa", "Poção de Cura", "Dente de Goblin"]}
    bolsa_da_party = Column(JSON, default=lambda: {"ouro": 0, "itens": []})

class Encontro(Base):
    __tablename__ = "encontros"
    id = Column(Integer, primary_key=True)
    cod_sala = Column(String)
    nome_inimigo = Column(String)
    quantidade = Column(Integer)
    condicao_aparecimento = Column(String, default="sempre")
    ativo = Column(Boolean, default=True)
    multiplicador_ameaca = Column(Integer, default=1) # ── NOVO: Mapeamento do Multiplicador

class Inimigo(Base):
    __tablename__ = "inimigos"
    id = Column(Integer, primary_key=True)
    nome = Column(String)
    hp_max = Column(Integer)
    ca = Column(Integer)
    ataque = Column(String)
    dano = Column(String)
    imagem_url = Column(String, nullable=True)
    xp_recompensa = Column(Integer, default=50)
    ouro_recompensa = Column(Integer, default=5)
    
    # ── MECÂNICA DE BOSS E LOOT ESPECIAL ──
    is_boss = Column(Boolean, default=False)
    fase_atual = Column(Integer, default=1)
    loot_especial = Column(JSON, default=list)

class Cena(Base):
    __tablename__ = "cenas"
    cod_sala = Column(String, primary_key=True)
    nome_sala = Column(String)
    descricao_visual = Column(Text)
    conexoes = Column(JSON)
    imagem_url = Column(String, nullable=True)
    loot_fixo = Column(JSON, default=list) # Itens soltos na sala
    # Perigos passivos de terreno. Exemplo:
    # [{"tipo": "dex_save", "cd": 13, "dano": "2d4", "descricao": "Campo de estrepes"}]
    hazards = Column(JSON, default=list)

class Interativo(Base):
    """Representa baús, armadilhas, portas trancadas ou segredos na sala."""
    __tablename__ = "interativos"
    id = Column(Integer, primary_key=True)
    cod_sala = Column(String) # Vinculado à Cena
    nome = Column(String) 
    descricao = Column(Text)
    tipo = Column(String) # bau, armadilha, porta, segredo, alavanca
    cd_teste = Column(Integer, default=10) 
    atributo_teste = Column(String, default="DEX") 
    recompensa = Column(JSON, default=list) 
    dano_falha = Column(Integer, default=0) 
    ativo = Column(Boolean, default=True)


class ObjetoDestrutivel(Base):
    """Objetos de cenário que possuem HP e podem ser destruídos fisicamente.
    Exemplos: jaulas, fechaduras, estátuas, globos de cristal, portas."""
    __tablename__ = "objetos_destrutiveis"
    id = Column(Integer, primary_key=True)
    cod_sala = Column(String)                       # Vinculado à Cena
    nome = Column(String)                           # Ex: "Fechadura de Ferro"
    descricao = Column(Text)
    hp_atual = Column(Integer)
    hp_max = Column(Integer)                        # Ex: 5 (Globo), 20 (Fechadura)
    ca = Column(Integer, default=10)                # Classe de Armadura do objeto
    # Força mínima para arrombar sem rolagem de ataque (0 = requer ataque normal)
    break_threshold = Column(Integer, default=0)
    # Ex: ["fogo", "acido"] — imune a esses tipos de dano
    resistencias = Column(JSON, default=list)
    # Ex: ["contundente"] — recebe dano dobrado
    vulnerabilidades = Column(JSON, default=list)
    # Itens/eventos liberados ao destruir o objeto
    recompensa_ao_destruir = Column(JSON, default=list)
    ativo = Column(Boolean, default=True)


class EstatisticasJogador(Base):
    __tablename__ = "estatisticas_jogadores"
    jogador_telefone = Column(String, primary_key=True)
    inimigos_derrotados = Column(Integer, default=0)
    danos_causados_total = Column(Integer, default=0)
    danos_recebidos_total = Column(Integer, default=0)
    vezes_derrotado = Column(Integer, default=0)
    
    # Precisão e Rolagens
    total_ataques_acertados = Column(Integer, default=0)
    total_ataques_errados = Column(Integer, default=0)
    criticos_acertados = Column(Integer, default=0)
    fumbles_rolados = Column(Integer, default=0)

    # Contadores de progresso
    salas_visitadas = Column(JSON, default=list)
    salas_desbloqueadas_count = Column(Integer, default=0)
    xp_ganho_total = Column(Integer, default=0)
    ouro_ganho_total = Column(Integer, default=0)
    ouro_perdido_total = Column(Integer, default=0)

    # Contadores de ações
    testes_realizados = Column(Integer, default=0)
    testes_sucesso = Column(Integer, default=0)
    testes_falha = Column(Integer, default=0)
    descansos_curtos = Column(Integer, default=0)
    intervencoes_divinas = Column(Integer, default=0)

    # Rastreamento de tempo
    primeira_sessao = Column(String)
    ultima_sessao = Column(String)
    tempo_jogo_minutos = Column(Integer, default=0)

class HistoricoPartida(Base):
    __tablename__ = "historico_partidas"
    id = Column(Integer, primary_key=True)
    jogador_telefone = Column(String)
    data_inicio = Column(String)
    data_fim = Column(String, nullable=True)
    resultado = Column(String) 
    inimigos_derrotados = Column(Integer, default=0)
    ouro_coletado = Column(Integer, default=0)
    xp_ganho = Column(Integer, default=0)
    sala_final = Column(String)

class Missao(Base):
    __tablename__ = "missoes"
    id = Column(Integer, primary_key=True)
    jogador_telefone = Column(String) 
    npc_nome = Column(String) 
    titulo = Column(String) 
    descricao = Column(Text)
    objetivo_item = Column(String) 
    objetivo_quantidade = Column(Integer, default=1)
    recompensa_xp = Column(Integer, default=0)
    recompensa_ouro = Column(Integer, default=0)
    recompensa_item = Column(String, nullable=True) 
    concluida = Column(Boolean, default=False)

# ─── NOVOS MODELOS: NPCs DINÂMICOS E ENCONTROS ALEATÓRIOS ───

class Npc(Base):
    __tablename__ = "npcs"
    id = Column(Integer, primary_key=True)
    cod_sala = Column(String)
    nome = Column(String)
    descricao = Column(Text)
    # Diálogo padrão quando o jogador fala com o NPC
    dialogo_base = Column(Text)
    # Diálogo especial se o jogador tiver um item específico no inventário
    dialogo_item_especial = Column(Text, nullable=True)
    # Nome do item que ativa o diálogo especial
    item_gatilho = Column(String, nullable=True)

class EncontroAleatorio(Base):
    __tablename__ = "encontros_aleatorios"
    id = Column(Integer, primary_key=True)
    cod_sala = Column(String)
    nome_inimigo = Column(String)
    quantidade = Column(Integer)
    # Chance de 1 a 100. Ex: 15 = 15% de acontecer.
    chance = Column(Integer, default=100)