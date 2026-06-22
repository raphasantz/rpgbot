from typing import List, Optional, Dict, Any
from sqlalchemy import String, Integer, JSON, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.mutable import MutableDict, MutableList
from database import Base

class Jogador(Base):
    __tablename__ = "jogadores"
    
    # ── MULTIPLAYER & LOCALIZAÇÃO ──
    telefone: Mapped[str] = mapped_column(String, primary_key=True)
    party_id: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True) 
    cena_atual: Mapped[str] = mapped_column(String, default="taverna") 
    cena_anterior: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    nome: Mapped[str] = mapped_column(String)
    sexo: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    classe: Mapped[str] = mapped_column(String)
    raca: Mapped[str] = mapped_column(String)
    background: Mapped[str] = mapped_column(String)
    
    # Nível e XP
    nivel: Mapped[int] = mapped_column(Integer, default=1)
    xp: Mapped[int] = mapped_column(Integer, default=0)

    # Vida
    hp_atual: Mapped[int] = mapped_column(Integer)
    hp_maximo: Mapped[int] = mapped_column(Integer)

    # Atributos brutos
    str_val: Mapped[int] = mapped_column("str", Integer)
    dex_val: Mapped[int] = mapped_column("dex", Integer)
    con_val: Mapped[int] = mapped_column("con", Integer)
    int_val: Mapped[int] = mapped_column("int", Integer)
    wis_val: Mapped[int] = mapped_column("wis", Integer)
    cha_val: Mapped[int] = mapped_column("cha", Integer)

    # Modificadores
    mod_str: Mapped[int] = mapped_column(Integer)
    mod_dex: Mapped[int] = mapped_column(Integer)
    mod_con: Mapped[int] = mapped_column(Integer)
    mod_int: Mapped[int] = mapped_column(Integer)
    mod_wis: Mapped[int] = mapped_column(Integer)
    mod_cha: Mapped[int] = mapped_column(Integer)

    # Combate e Defesa
    modificador_ataque: Mapped[int] = mapped_column(Integer)
    modificador_defesa: Mapped[int] = mapped_column(Integer)
    proficiencia: Mapped[int] = mapped_column(Integer, default=2)
    
    # Equipamento Ativo
    arma_equipada: Mapped[str] = mapped_column(String, default="Desarmado")
    armadura_equipada: Mapped[str] = mapped_column(String, default="Trajes Comuns")
    dano_dado: Mapped[str] = mapped_column(String, default="1d4")
    mod_dano: Mapped[int] = mapped_column(Integer, default=0)

    # Recursos
    gold: Mapped[int] = mapped_column(Integer, default=15)
    inventario: Mapped[list] = mapped_column(MutableList.as_mutable(JSON), default=list)
    slots_magia: Mapped[int] = mapped_column(Integer, default=0)
    slots_magia_max: Mapped[int] = mapped_column(Integer, default=0)
    descanso_curto_disponivel: Mapped[bool] = mapped_column(Boolean, default=True)

    # ── DADOS DE VIDA (Hit Dice) ──
    hit_dice_max: Mapped[int] = mapped_column(Integer, default=1)
    hit_dice_atual: Mapped[int] = mapped_column(Integer, default=1)

    # Efeitos de Status
    status_efeitos: Mapped[list] = mapped_column(MutableList.as_mutable(JSON), default=list) 
    
    # ── RESISTÊNCIAS E VULNERABILIDADES (D&D 5e) ──
    resistencias: Mapped[list] = mapped_column(MutableList.as_mutable(JSON), default=list)      
    vulnerabilidades: Mapped[list] = mapped_column(MutableList.as_mutable(JSON), default=list)  
    imunidades: Mapped[list] = mapped_column(MutableList.as_mutable(JSON), default=list)        

class Aventura(Base):
    __tablename__ = "aventuras"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    prologo: Mapped[str] = mapped_column(Text)

class Campanha(Base):
    __tablename__ = "campanhas"
    
    party_id: Mapped[str] = mapped_column(String, primary_key=True, index=True) 
    host_id: Mapped[str] = mapped_column(String, nullable=False) 
    aventura_ativa: Mapped[str] = mapped_column(String, default="cidadela") 
    
    estado_salas: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), default=dict) 
    ultimo_evento: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), default=dict)
    momento: Mapped[str] = mapped_column(String, default="inicio")
    tensao: Mapped[int] = mapped_column(Integer, default=0)
    turno_atual: Mapped[int] = mapped_column(Integer, default=1)
    
    em_combate: Mapped[bool] = mapped_column(Boolean, default=False)
    fila_iniciativa: Mapped[list] = mapped_column(MutableList.as_mutable(JSON), default=list)
    indice_turno: Mapped[int] = mapped_column(Integer, default=0)
    
    cena_atual: Mapped[str] = mapped_column(String, default="taverna")
    cena_anterior: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="exploracao")
    votos_destino: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), default=dict)

    bolsa_da_party: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), default=lambda: {"ouro": 0, "itens": []})

class Encontro(Base):
    __tablename__ = "encontros"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cod_sala: Mapped[str] = mapped_column(String)
    nome_inimigo: Mapped[str] = mapped_column(String)
    quantidade: Mapped[int] = mapped_column(Integer)
    condicao_aparecimento: Mapped[str] = mapped_column(String, default="sempre")
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    multiplicador_ameaca: Mapped[int] = mapped_column(Integer, default=1) 

class Inimigo(Base):
    __tablename__ = "inimigos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String)
    hp_max: Mapped[int] = mapped_column(Integer)
    ca: Mapped[int] = mapped_column(Integer)
    ataque: Mapped[str] = mapped_column(String)
    dano: Mapped[str] = mapped_column(String)
    imagem_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    xp_recompensa: Mapped[int] = mapped_column(Integer, default=50)
    ouro_recompensa: Mapped[int] = mapped_column(Integer, default=5)
    
    is_boss: Mapped[bool] = mapped_column(Boolean, default=False)
    fase_atual: Mapped[int] = mapped_column(Integer, default=1)
    loot_especial: Mapped[list] = mapped_column(MutableList.as_mutable(JSON), default=list)
    
    tipo_dano_padrao: Mapped[str] = mapped_column(String, default="contundente") 
    resistencias: Mapped[list] = mapped_column(MutableList.as_mutable(JSON), default=list)      
    vulnerabilidades: Mapped[list] = mapped_column(MutableList.as_mutable(JSON), default=list)  
    imunidades: Mapped[list] = mapped_column(MutableList.as_mutable(JSON), default=list)

class Cena(Base):
    __tablename__ = "cenas"
    cod_sala: Mapped[str] = mapped_column(String, primary_key=True)
    nome_sala: Mapped[str] = mapped_column(String)
    descricao_visual: Mapped[str] = mapped_column(Text)
    conexoes: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON))
    imagem_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    loot_fixo: Mapped[list] = mapped_column(MutableList.as_mutable(JSON), default=list) 
    hazards: Mapped[list] = mapped_column(MutableList.as_mutable(JSON), default=list)

class Interativo(Base):
    __tablename__ = "interativos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cod_sala: Mapped[str] = mapped_column(String) 
    nome: Mapped[str] = mapped_column(String) 
    descricao: Mapped[str] = mapped_column(Text)
    tipo: Mapped[str] = mapped_column(String) 
    cd_teste: Mapped[int] = mapped_column(Integer, default=10) 
    atributo_teste: Mapped[str] = mapped_column(String, default="DEX") 
    recompensa: Mapped[list] = mapped_column(MutableList.as_mutable(JSON), default=list) 
    dano_falha: Mapped[int] = mapped_column(Integer, default=0) 
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

class ObjetoDestrutivel(Base):
    __tablename__ = "objetos_destrutiveis"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cod_sala: Mapped[str] = mapped_column(String)                      
    nome: Mapped[str] = mapped_column(String)                          
    descricao: Mapped[str] = mapped_column(Text)
    hp_atual: Mapped[int] = mapped_column(Integer)
    hp_max: Mapped[int] = mapped_column(Integer)                        
    ca: Mapped[int] = mapped_column(Integer, default=10)                
    break_threshold: Mapped[int] = mapped_column(Integer, default=0)
    resistencias: Mapped[list] = mapped_column(MutableList.as_mutable(JSON), default=list)
    vulnerabilidades: Mapped[list] = mapped_column(MutableList.as_mutable(JSON), default=list)
    recompensa_ao_destruir: Mapped[list] = mapped_column(MutableList.as_mutable(JSON), default=list)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

class EstatisticasJogador(Base):
    __tablename__ = "estatisticas_jogadores"
    jogador_telefone: Mapped[str] = mapped_column(String, primary_key=True)
    inimigos_derrotados: Mapped[int] = mapped_column(Integer, default=0)
    danos_causados_total: Mapped[int] = mapped_column(Integer, default=0)
    danos_recebidos_total: Mapped[int] = mapped_column(Integer, default=0)
    vezes_derrotado: Mapped[int] = mapped_column(Integer, default=0)
    total_ataques_acertados: Mapped[int] = mapped_column(Integer, default=0)
    total_ataques_errados: Mapped[int] = mapped_column(Integer, default=0)
    criticos_acertados: Mapped[int] = mapped_column(Integer, default=0)
    fumbles_rolados: Mapped[int] = mapped_column(Integer, default=0)
    salas_visitadas: Mapped[list] = mapped_column(MutableList.as_mutable(JSON), default=list)
    salas_desbloqueadas_count: Mapped[int] = mapped_column(Integer, default=0)
    xp_ganho_total: Mapped[int] = mapped_column(Integer, default=0)
    ouro_ganho_total: Mapped[int] = mapped_column(Integer, default=0)
    ouro_perdido_total: Mapped[int] = mapped_column(Integer, default=0)
    testes_realizados: Mapped[int] = mapped_column(Integer, default=0)
    testes_sucesso: Mapped[int] = mapped_column(Integer, default=0)
    testes_falha: Mapped[int] = mapped_column(Integer, default=0)
    descansos_curtos: Mapped[int] = mapped_column(Integer, default=0)
    intervencoes_divinas: Mapped[int] = mapped_column(Integer, default=0)
    primeira_sessao: Mapped[Optional[str]] = mapped_column(String)
    ultima_sessao: Mapped[Optional[str]] = mapped_column(String)
    tempo_jogo_minutos: Mapped[int] = mapped_column(Integer, default=0)

class HistoricoPartida(Base):
    __tablename__ = "historico_partidas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jogador_telefone: Mapped[str] = mapped_column(String)
    data_inicio: Mapped[str] = mapped_column(String)
    data_fim: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    resultado: Mapped[str] = mapped_column(String) 
    inimigos_derrotados: Mapped[int] = mapped_column(Integer, default=0)
    ouro_coletado: Mapped[int] = mapped_column(Integer, default=0)
    xp_ganho: Mapped[int] = mapped_column(Integer, default=0)
    sala_final: Mapped[str] = mapped_column(String)
    causa_morte: Mapped[Optional[str]] = mapped_column(String, nullable=True)

class Missao(Base):
    __tablename__ = "missoes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jogador_telefone: Mapped[str] = mapped_column(String) 
    npc_nome: Mapped[str] = mapped_column(String) 
    titulo: Mapped[str] = mapped_column(String) 
    descricao: Mapped[str] = mapped_column(Text)
    objetivo_item: Mapped[str] = mapped_column(String) 
    objetivo_quantidade: Mapped[int] = mapped_column(Integer, default=1)
    recompensa_xp: Mapped[int] = mapped_column(Integer, default=0)
    recompensa_ouro: Mapped[int] = mapped_column(Integer, default=0)
    recompensa_item: Mapped[Optional[str]] = mapped_column(String, nullable=True) 
    concluida: Mapped[bool] = mapped_column(Boolean, default=False)

class Npc(Base):
    __tablename__ = "npcs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cod_sala: Mapped[str] = mapped_column(String)
    nome: Mapped[str] = mapped_column(String)
    descricao: Mapped[str] = mapped_column(Text)
    dialogo_base: Mapped[str] = mapped_column(Text)
    dialogo_item_especial: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    item_gatilho: Mapped[Optional[str]] = mapped_column(String, nullable=True)

class EncontroAleatorio(Base):
    __tablename__ = "encontros_aleatorios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cod_sala: Mapped[str] = mapped_column(String)
    nome_inimigo: Mapped[str] = mapped_column(String)
    quantidade: Mapped[int] = mapped_column(Integer)
    chance: Mapped[int] = mapped_column(Integer, default=100)