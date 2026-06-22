"""
ai_engine_rpgbot.py — SHIM de compatibilidade.

O código canônico está em ai_engine_web.py (versão mais avançada com suporte
a múltiplos NPCs na função narrar_taverna). Este arquivo apenas re-exporta
todas as funções para manter compatibilidade com imports existentes:

    from ai_engine_rpgbot import interpretar_acao_json, narrar_combate, ...

Se precisares alterar lógica de IA, edita ai_engine_web.py.
"""
from ai_engine_web import (
    client,
    _openai_available,
    CACHE_INTENCOES,
    FALLBACK_INTENCAO_JSON,
    FALLBACK_NARRACAO_COMBATE,
    FALLBACK_NARRACAO_AMBIENTE,
    FALLBACK_ATRIBUTO,
    interpretar_acao_json,
    interpretar_acao,
    narrar_combate,
    decidir_atributo_teste,
    narrar_ambiente,
    extrair_itens_da_narracao,
    sanitizar_descricao_para_dalle,
    gerar_imagem_sala,
    narrar_taverna,
    _taverna_fallback,
)

__all__ = [
    "client",
    "_openai_available",
    "CACHE_INTENCOES",
    "FALLBACK_INTENCAO_JSON",
    "FALLBACK_NARRACAO_COMBATE",
    "FALLBACK_NARRACAO_AMBIENTE",
    "FALLBACK_ATRIBUTO",
    "interpretar_acao_json",
    "interpretar_acao",
    "narrar_combate",
    "decidir_atributo_teste",
    "narrar_ambiente",
    "extrair_itens_da_narracao",
    "sanitizar_descricao_para_dalle",
    "gerar_imagem_sala",
    "narrar_taverna",
    "_taverna_fallback",
]
