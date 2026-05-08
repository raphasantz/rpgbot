"""
Módulo para gerenciar estatísticas e histórico do jogador.
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import EstatisticasJogador, HistoricoPartida, Jogador

def get_or_create_estatisticas(db: Session, telefone: str):
    """Obtém ou cria estatísticas para um jogador."""
    stats = db.query(EstatisticasJogador).filter(
        EstatisticasJogador.jogador_telefone == telefone
    ).first()

    if not stats:
        stats = EstatisticasJogador(
            jogador_telefone=telefone,
            primeira_sessao=datetime.now().isoformat(),
            ultima_sessao=datetime.now().isoformat(),
            salas_visitadas=[]
        )
        db.add(stats)
        db.commit()
    return stats

def iniciar_sessao(db: Session, telefone: str):
    """Registra o início de uma nova sessão de jogo."""
    stats = get_or_create_estatisticas(db, telefone)
    stats.ultima_sessao = datetime.now().isoformat()

    # Cria registro de partida em andamento
    partida = HistoricoPartida(
        jogador_telefone=telefone,
        data_inicio=datetime.now().isoformat(),
        resultado='em_andamento',
        sala_final='carvalhal'
    )
    db.add(partida)
    db.commit()
    return partida.id

def finalizar_sessao(db: Session, telefone: str, resultado: str, sala_final: str,
                     xp_ganho=0, ouro_ganho=0, inimigos_derrotados=0, causa_morte=None):
    """Finaliza uma sessão de jogo."""
    partida = db.query(HistoricoPartida).filter(
        HistoricoPartida.jogador_telefone == telefone,
        HistoricoPartida.resultado == 'em_andamento'
    ).order_by(HistoricoPartida.id.desc()).first()

    if partida:
        partida.data_fim = datetime.now().isoformat()
        partida.resultado = resultado
        partida.sala_final = sala_final
        partida.xp_ganho = xp_ganho
        partida.ouro_ganho = ouro_ganho
        partida.inimigos_derrotados = inimigos_derrotados
        partida.causa_morte = causa_morte
        db.commit()

def atualizar_estatistica(db: Session, telefone: str, campo: str, valor=1, increment=True):
    """Atualiza um campo específico das estatísticas."""
    stats = get_or_create_estatisticas(db, telefone)
    atual = getattr(stats, campo, 0)
    if increment:
        setattr(stats, campo, atual + valor)
    else:
        setattr(stats, campo, valor)
    db.commit()

def registrar_sala_visitada(db: Session, telefone: str, cod_sala: str):
    """Registra uma sala visitada (apenas se for nova)."""
    stats = get_or_create_estatisticas(db, telefone)
    if cod_sala not in stats.salas_visitadas:
        salas = list(stats.salas_visitadas) if stats.salas_visitadas else []
        salas.append(cod_sala)
        stats.salas_visitadas = salas
        stats.salas_desbloqueadas_count = len(salas)
        db.commit()

def registrar_combate_resultado(db: Session, telefone: str, acertou: bool,
                                 dano=0, critico=False, fumble=False, jogador_dano_recebido=0):
    """Registra o resultado de um ataque em combate."""
    stats = get_or_create_estatisticas(db, telefone)

    if acertou:
        stats.total_ataques_acertados += 1
        stats.danos_causados_total += dano
        if critico:
            stats.criticos_acertados += 1
    else:
        stats.total_ataques_errados += 1
        if fumble:
            stats.fumbles_rolados += 1

    if jogador_dano_recebido > 0:
        stats.danos_recebidos_total += jogador_dano_recebido

    db.commit()

def registrar_vitoria(db: Session, telefone: str, inimigos_quantidade: int,
                     xp_ganho: int, ouro_ganho: int):
    """Registra uma vitória em combate."""
    stats = get_or_create_estatisticas(db, telefone)
    stats.inimigos_derrotados += inimigos_quantidade
    stats.xp_ganho_total += xp_ganho
    stats.ouro_ganho_total += ouro_ganho
    db.commit()

def registrar_derrota(db: Session, telefone: str, intervencao_divina=False,
                       ouro_perdido=0):
    """Registra uma derrota em combate."""
    stats = get_or_create_estatisticas(db, telefone)
    stats.vezes_derrotado += 1
    if intervencao_divina:
        stats.intervencoes_divinas += 1
    if ouro_perdido > 0:
        stats.ouro_perdido_total += ouro_perdido
    db.commit()

def registrar_teste(db: Session, telefone: str, sucesso: bool):
    """Registra o resultado de um teste de atributo."""
    stats = get_or_create_estatisticas(db, telefone)
    stats.testes_realizados += 1
    if sucesso:
        stats.testes_sucesso += 1
    else:
        stats.testes_falha += 1
    db.commit()

def registrar_descanso_curto(db: Session, telefone: str):
    """Registra um descanso curto."""
    stats = get_or_create_estatisticas(db, telefone)
    stats.descansos_curtos += 1
    db.commit()

def calcular_taxa_sucesso(stats: EstatisticasJogador) -> float:
    """Calcula a taxa de sucesso em combate."""
    total = stats.total_ataques_acertados + stats.total_ataques_errados
    if total == 0:
        return 0.0
    return (stats.total_ataques_acertados / total) * 100

def calcular_taxa_sucesso_testes(stats: EstatisticasJogador) -> float:
    """Calcula a taxa de sucesso em testes."""
    if stats.testes_realizados == 0:
        return 0.0
    return (stats.testes_sucesso / stats.testes_realizados) * 100

def get_ultimas_partidas(db: Session, telefone: str, limite: int = 5):
    """Retorna as últimas partidas do jogador."""
    return db.query(HistoricoPartida).filter(
        HistoricoPartida.jogador_telefone == telefone,
        HistoricoPartida.resultado != 'em_andamento'
    ).order_by(HistoricoPartida.id.desc()).limit(limite).all()

def calcular_tempo_jogo_formatado(minutos: int) -> str:
    """Formata o tempo de jogo em horas e minutos."""
    horas = minutos // 60
    mins = minutos % 60
    if horas > 0:
        return f"{horas}h {mins}min"
    return f"{mins}min"

def get_rank_jogador(db: Session, telefone: str) -> dict:
    """Retorna a posição do jogador no ranking geral."""
    todos = db.query(EstatisticasJogador).order_by(
        EstatisticasJogador.xp_ganho_total.desc()
    ).all()

    for idx, s in enumerate(todos):
        if s.jogador_telefone == telefone:
            return {
                'posicao': idx + 1,
                'total_jogadores': len(todos),
                'xp_total': s.xp_ganho_total
            }
    return {'posicao': len(todos), 'total_jogadores': len(todos), 'xp_total': 0}