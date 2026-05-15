"""
Módulo para gerenciar estatísticas e histórico do jogador.
"""
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from models import EstatisticasJogador, HistoricoPartida, Jogador

async def get_or_create_estatisticas(db: AsyncSession, telefone: str):
    """Obtém ou cria estatísticas para um jogador."""
    result = await db.execute(
        select(EstatisticasJogador).filter(EstatisticasJogador.jogador_telefone == telefone)
    )
    stats = result.scalars().first()

    if not stats:
        stats = EstatisticasJogador(
            jogador_telefone=telefone,
            primeira_sessao=datetime.now().isoformat(),
            ultima_sessao=datetime.now().isoformat(),
            salas_visitadas=[]
        )
        db.add(stats)
        await db.flush()
    return stats

async def iniciar_sessao(db: AsyncSession, telefone: str):
    """Registra o início de uma nova sessão de jogo."""
    stats = await get_or_create_estatisticas(db, telefone)
    stats.ultima_sessao = datetime.now().isoformat()

    # Cria registro de partida em andamento
    partida = HistoricoPartida(
        jogador_telefone=telefone,
        data_inicio=datetime.now().isoformat(),
        resultado='em_andamento',
        sala_final='carvalhal'
    )
    db.add(partida)
    await db.flush()
    return partida.id

async def finalizar_sessao(db: AsyncSession, telefone: str, resultado: str, sala_final: str,
                     xp_ganho=0, ouro_ganho=0, inimigos_derrotados=0, causa_morte=None):
    """Finaliza uma sessão de jogo."""
    result = await db.execute(
        select(HistoricoPartida).filter(
            HistoricoPartida.jogador_telefone == telefone,
            HistoricoPartida.resultado == 'em_andamento'
        ).order_by(HistoricoPartida.id.desc())
    )
    partida = result.scalars().first()

    if partida:
        partida.data_fim = datetime.now().isoformat()
        partida.resultado = resultado
        partida.sala_final = sala_final
        partida.xp_ganho = xp_ganho
        partida.ouro_ganho = ouro_ganho
        partida.inimigos_derrotados = inimigos_derrotados
        partida.causa_morte = causa_morte
        await db.flush()

async def atualizar_estatistica(db: AsyncSession, telefone: str, campo: str, valor=1, increment=True):
    """Atualiza um campo específico das estatísticas."""
    stats = await get_or_create_estatisticas(db, telefone)
    atual = getattr(stats, campo, 0)
    if increment:
        setattr(stats, campo, atual + valor)
    else:
        setattr(stats, campo, valor)
    await db.flush()

async def registrar_sala_visitada(db: AsyncSession, telefone: str, cod_sala: str):
    """Registra uma sala visitada (apenas se for nova)."""
    stats = await get_or_create_estatisticas(db, telefone)
    if cod_sala not in stats.salas_visitadas:
        salas = list(stats.salas_visitadas) if stats.salas_visitadas else []
        salas.append(cod_sala)
        stats.salas_visitadas = salas # Reatribuição (Fase 1)
        stats.salas_desbloqueadas_count = len(salas)
        await db.flush()

async def registrar_combate_resultado(db: AsyncSession, telefone: str, acertou: bool,
                                 dano=0, critico=False, fumble=False, jogador_dano_recebido=0):
    """Registra o resultado de um ataque em combate."""
    stats = await get_or_create_estatisticas(db, telefone)

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

    await db.flush()

async def registrar_vitoria(db: AsyncSession, telefone: str, inimigos_quantidade: int,
                     xp_ganho: int, ouro_ganho: int):
    """Registra uma vitória em combate."""
    stats = await get_or_create_estatisticas(db, telefone)
    stats.inimigos_derrotados += inimigos_quantidade
    stats.xp_ganho_total += xp_ganho
    stats.ouro_ganho_total += ouro_ganho
    await db.flush()

async def registrar_derrota(db: AsyncSession, telefone: str, intervencao_divina=False,
                       ouro_perdido=0):
    """Registra uma derrota em combate."""
    stats = await get_or_create_estatisticas(db, telefone)
    stats.vezes_derrotado += 1
    if intervencao_divina:
        stats.intervencoes_divinas += 1
    if ouro_perdido > 0:
        stats.ouro_perdido_total += ouro_perdido
    await db.flush()

async def registrar_teste(db: AsyncSession, telefone: str, sucesso: bool):
    """Registra o resultado de um teste de atributo."""
    stats = await get_or_create_estatisticas(db, telefone)
    stats.testes_realizados += 1
    if sucesso:
        stats.testes_sucesso += 1
    else:
        stats.testes_falha += 1
    await db.flush()

async def registrar_descanso_curto(db: AsyncSession, telefone: str):
    """Registra um descanso curto."""
    stats = await get_or_create_estatisticas(db, telefone)
    stats.descansos_curtos += 1
    await db.flush()

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

async def get_ultimas_partidas(db: AsyncSession, telefone: str, limite: int = 5):
    """Retorna as últimas partidas do jogador."""
    result = await db.execute(
        select(HistoricoPartida).filter(
            HistoricoPartida.jogador_telefone == telefone,
            HistoricoPartida.resultado != 'em_andamento'
        ).order_by(HistoricoPartida.id.desc()).limit(limite)
    )
    return result.scalars().all()

def calcular_tempo_jogo_formatado(minutos: int) -> str:
    """Formata o tempo de jogo em horas e minutos."""
    horas = minutos // 60
    mins = minutos % 60
    if horas > 0:
        return f"{horas}h {mins}min"
    return f"{mins}min"

async def get_rank_jogador(db: AsyncSession, telefone: str) -> dict:
    """Retorna a posição do jogador no ranking geral (OTIMIZADO PARA ASYNC)."""
    # 1. Pega o XP do herói
    result_xp = await db.execute(
        select(EstatisticasJogador.xp_ganho_total).filter(EstatisticasJogador.jogador_telefone == telefone)
    )
    xp_heroi = result_xp.scalar() or 0
    
    # 2. Conta quantos jogadores tem XP estritamente maior que o dele
    result_count = await db.execute(
        select(func.count(EstatisticasJogador.jogador_telefone)).filter(
            EstatisticasJogador.xp_ganho_total > xp_heroi
        )
    )
    posicao = result_count.scalar() + 1
    
    # 3. Conta o total de jogadores
    result_total = await db.execute(select(func.count(EstatisticasJogador.jogador_telefone)))
    total_jogadores = result_total.scalar()
    
    return {
        'posicao': posicao,
        'total_jogadores': total_jogadores,
        'xp_total': xp_heroi
    }