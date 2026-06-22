"""
Stats Manager Sync — Estatísticas e histórico do jogador (versão síncrona para FastAPI).
Adaptado de rpg_bot/stats_manager.py para SQLAlchemy sync + modelos_web.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, func

from modelos_web import (
    EstatisticasJogador, HistoricoPartida, JogadorWeb,
    SessionLocal, get_db,
)


def get_or_create_estatisticas(db: Session, telefone: str) -> EstatisticasJogador:
    """Obtém ou cria estatísticas para um jogador."""
    stats = db.query(EstatisticasJogador).filter(
        EstatisticasJogador.jogador_telefone == telefone
    ).first()

    if not stats:
        stats = EstatisticasJogador(
            jogador_telefone=telefone,
            primeira_sessao=datetime.now().isoformat(),
            ultima_sessao=datetime.now().isoformat(),
            salas_visitadas=[],
        )
        db.add(stats)
        db.flush()
    return stats


def iniciar_sessao(db: Session, telefone: str) -> int:
    """Registra o início de uma nova sessão de jogo. Retorna ID da partida.
    Reutiliza sessão em_andamento existente se houver (evita partidas órfãs)."""
    stats = get_or_create_estatisticas(db, telefone)
    stats.ultima_sessao = datetime.now().isoformat()

    # Reutiliza sessão em_andamento existente (se houver) em vez de criar nova
    existente = db.query(HistoricoPartida).filter(
        HistoricoPartida.jogador_telefone == telefone,
        HistoricoPartida.resultado == 'em_andamento'
    ).order_by(HistoricoPartida.id.desc()).first()
    if existente:
        return existente.id

    partida = HistoricoPartida(
        jogador_telefone=telefone,
        data_inicio=datetime.now().isoformat(),
        resultado='em_andamento',
        sala_final='carvalhal'
    )
    db.add(partida)
    db.flush()
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return partida.id


def finalizar_sessao(
    db: Session, telefone: str, resultado: str, sala_final: str,
    xp_ganho: int = 0, ouro_ganho: int = 0, inimigos_derrotados: int = 0
):
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
        partida.ouro_coletado = ouro_ganho
        partida.inimigos_derrotados = inimigos_derrotados
        db.flush()
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise


def atualizar_estatistica(db: Session, telefone: str, campo: str, valor: int = 1, increment: bool = True):
    """Atualiza um campo específico das estatísticas."""
    stats = get_or_create_estatisticas(db, telefone)
    atual = getattr(stats, campo, 0)
    if increment:
        setattr(stats, campo, atual + valor)
    else:
        setattr(stats, campo, valor)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def registrar_sala_visitada(db: Session, telefone: str, cod_sala: str):
    """Registra uma sala visitada (apenas se for nova)."""
    stats = get_or_create_estatisticas(db, telefone)
    # Guard para salas_visitadas None (pode acontecer em linhas legadas)
    visitadas = stats.salas_visitadas
    if visitadas is None:
        visitadas = []
        stats.salas_visitadas = visitadas
    if cod_sala not in visitadas:
        visitadas.append(cod_sala)
        stats.salas_desbloqueadas_count = len(visitadas)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def registrar_combate_resultado(db: Session, telefone: str, acertou: bool, dano: int = 0, critico: bool = False, fumble: bool = False, jogador_dano_recebido: int = 0):
    """Registra resultado de um ataque (para precisão)."""
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
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def registrar_teste_atributo(db: Session, telefone: str, atributo: str, sucesso: bool):
    """Registra resultado de teste de atributo."""
    stats = get_or_create_estatisticas(db, telefone)
    stats.testes_realizados += 1
    if sucesso:
        stats.testes_sucesso += 1
    else:
        stats.testes_falha += 1
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_estatisticas_resumo(db: Session, telefone: str) -> Dict[str, Any]:
    """Retorna resumo das estatísticas do jogador."""
    # Usa get_or_create para evitar erro quando o jogador ainda não tem estatísticas
    stats = get_or_create_estatisticas(db, telefone)
    
    # Calcular taxas
    total_ataques = stats.total_ataques_acertados + stats.total_ataques_errados
    ataques_acertados = stats.total_ataques_acertados
    taxa_acerto = (ataques_acertados / total_ataques * 100) if total_ataques > 0 else 0

    total_testes = stats.testes_realizados
    testes_sucedidos = stats.testes_sucesso
    taxa_teste = (testes_sucedidos / total_testes * 100) if total_testes > 0 else 0
    
    # Histórico de partidas
    partidas = db.query(HistoricoPartida).filter(
        HistoricoPartida.jogador_telefone == telefone
    ).order_by(HistoricoPartida.id.desc()).limit(10).all()
    
    vitorias = sum(1 for p in partidas if p.resultado == 'vitoria')
    derrotas = sum(1 for p in partidas if p.resultado == 'derrota')
    em_andamento = sum(1 for p in partidas if p.resultado == 'em_andamento')
    
    return {
        "jogador_telefone": stats.jogador_telefone,
        "primeira_sessao": stats.primeira_sessao,
        "ultima_sessao": stats.ultima_sessao,
        "salas_visitadas_count": stats.salas_desbloqueadas_count,
        "salas_visitadas": stats.salas_visitadas,
        "total_ataques": total_ataques,
        "ataques_acertados": ataques_acertados,
        "taxa_acerto_pct": round(taxa_acerto, 1),
        "danos_causados_total": stats.danos_causados_total,
        "total_testes": total_testes,
        "testes_sucedidos": testes_sucedidos,
        "taxa_teste_pct": round(taxa_teste, 1),
        "historico_partidas": [
            {
                "id": p.id,
                "data_inicio": p.data_inicio,
                "data_fim": p.data_fim,
                "resultado": p.resultado,
                "sala_final": p.sala_final,
                "xp_ganho": p.xp_ganho,
                "ouro_coletado": p.ouro_coletado,
                "inimigos_derrotados": p.inimigos_derrotados,
            }
            for p in partidas
        ],
        "resumo_partidas": {
            "total": len(partidas),
            "vitorias": vitorias,
            "derrotas": derrotas,
            "em_andamento": em_andamento,
        }
    }