"""
AI Engine Web — Narração e Interpretação para MezzaRPG Web.
Adaptado do rpg_bot/ai_engine.py para FastAPI assíncrono.
Mantém todas as funções de narração: combate, ambiente, extração de intenção, DALL-E.
"""
import os
import json
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv

import logging
logger = logging.getLogger("mezzarpg.ai")

try:
    from cachetools import TTLCache
    CACHE_INTENCOES = TTLCache(maxsize=1000, ttl=3600)
    CACHE_IMAGENS_SALA = TTLCache(maxsize=100, ttl=86400)
except ImportError:
    from collections import OrderedDict

    import time as _time

    class _BoundedCache(OrderedDict):
        """Cache fallback com limite de tamanho E TTL (evita memory leak e stale data)."""
        def __init__(self, maxsize=1000, ttl=3600, *args, **kwargs):
            self._maxsize = maxsize
            self._ttl = ttl
            self._timestamps: dict = {}
            super().__init__(*args, **kwargs)

        def _is_expired(self, key) -> bool:
            ts = self._timestamps.get(key)
            return ts is not None and (_time.time() - ts) > self._ttl

        def __setitem__(self, key, value):
            if key not in self:
                while len(self) >= self._maxsize:
                    oldest_key, _ = self.popitem(last=False)
                    self._timestamps.pop(oldest_key, None)
            self._timestamps[key] = _time.time()
            super().__setitem__(key, value)

        def __getitem__(self, key):
            if self._is_expired(key):
                del self[key]
                raise KeyError(key)
            return super().__getitem__(key)

        def __contains__(self, key):
            if self._is_expired(key):
                del self[key]
                return False
            return super().__contains__(key)

        def __delitem__(self, key):
            self._timestamps.pop(key, None)
            super().__delitem__(key)

    CACHE_INTENCOES = _BoundedCache(maxsize=1000, ttl=3600)
    CACHE_IMAGENS_SALA = _BoundedCache(maxsize=100, ttl=86400)

# Carrega as variáveis de ambiente
load_dotenv()

# Cliente assíncrono — não bloqueia o event loop do FastAPI
_openai_key = os.getenv("OPENAI_API_KEY")
client = AsyncOpenAI(api_key=_openai_key) if _openai_key else None

def _openai_available() -> bool:
    """Verifica se o cliente OpenAI está configurado."""
    return client is not None

# Fallbacks para quando a IA falhar
FALLBACK_INTENCAO_JSON = {
    "intencao": "OUTRO", "alvo": None, "estilo": None,
    "magia_usada": None, "manobra": None, "item": None, "direcao": None
}

FALLBACK_NARRACAO_COMBATE = "Você avança e executa sua ação contra o inimigo."
FALLBACK_NARRACAO_AMBIENTE = "Você observa o ambiente ao seu redor, mas nada fora do comum chama sua atenção."
FALLBACK_ATRIBUTO = "STR"


# =============================================================================
# SANITIZAÇÃO DE SAÍDA DA IA — Anti XSS
# =============================================================================
# As respostas da IA são renderizadas no frontend via x-html (innerHTML).
# Embora a IA seja instruída a não outputar HTML, LLMs são não-determinísticos
# e podem ser manipulados via prompt injection. Esta função escapa todo HTML
# e re-abre apenas um whitelist mínimo de tags que o sistema usa intencionalmente
# em narrativa_mecanica (<b>, <i>, <strong>, <br>).

def _sanitize_ai_html(text: str) -> str:
    """Escapa todo HTML e re-abre apenas tags seguras do whitelist."""
    if not text or not isinstance(text, str):
        return text or ""
    from html import escape
    escaped = escape(text, quote=False)
    # Re-abre apenas tags que o sistema usa intencionalmente
    for tag in ("b", "i", "strong", "br"):
        escaped = escaped.replace(f"&lt;{tag}&gt;", f"<{tag}>")
        escaped = escaped.replace(f"&lt;{tag}/&gt;", f"<{tag}>")
        escaped = escaped.replace(f"&lt;{tag} /&gt;", f"<{tag}>")
    escaped = escaped.replace("&lt;/b&gt;", "</b>")
    escaped = escaped.replace("&lt;/i&gt;", "</i>")
    escaped = escaped.replace("&lt;/strong&gt;", "</strong>")
    return escaped

async def interpretar_acao_json(texto_jogador: str, contexto_sala: str = "Nenhum") -> Dict[str, Any]:
    """
    Envia a ação do jogador para o GPT-4o-mini e retorna um JSON estruturado com a intenção e parâmetros mecânicos.
    Usa o response_format nativo para garantir um JSON válido.
    """
    acao_limpa = (texto_jogador or '').strip().lower()
    chave_cache = f"json_{acao_limpa}|{contexto_sala}"
    
    if chave_cache in CACHE_INTENCOES:
        logger.debug("[CACHE HIT] Intenção JSON recuperada do cache")
        return CACHE_INTENCOES[chave_cache]

    if not _openai_available():
        return dict(FALLBACK_INTENCAO_JSON)

    system_prompt = (
        "És um motor de extração de intenções estrito para um RPG de texto baseado em D&D 5e.\n"
        "A tua ÚNICA função é ler a entrada do jogador e extrair a intenção mecânica num formato JSON pré-definido.\n\n"
        "REGRAS ABSOLUTAS:\n"
        "1. NUNCA narres ou decidas o resultado da ação (sucesso/falha). Não escrevas 'Você consegue' ou 'Você falha'.\n"
        "2. Extraia APENAS os dados mecânicos solicitados.\n"
        "3. Se o jogador descrever algo épico, traduza para a intenção mais próxima (ex: 'decapitar' -> COMBATE, estilo 'agressivo').\n"
        "4. Responda APENAS com o objeto JSON válido.\n\n"
        "ESQUEMA JSON EXIGIDO:\n"
        "{\n"
        '  "intencao": "COMBATE | MAGIA | MANOBRA | NAVEGAR | INTERACAO | DESCANSAR | OUTRO",\n'
        '  "alvo": "Nome do inimigo, objeto ou NPC visado (string ou null)",\n'
        '  "estilo": "furtivo | temerario | agressivo | defesa | null",\n'
        '  "magia_usada": "Nome exato da magia se intencao for MAGIA (string ou null)",\n'
        '  "manobra": "empurrar | agarrar | derrubar | desarmar | levantar | null",\n'
        '  "item": "Nome do item a ser usado/pegado (string ou null)",\n'
        '  "direcao": "norte | sul | leste | oeste | dentro | fora | cima | baixo | subir | descer | null"\n'
        "}\n\n"
        "MAPEAMENTO DE INTENÇÕES:\n"
        "- COMBATE: Atacar fisicamente, golpear, atirar.\n"
        "- MAGIA: Lançar um feitiço específico ofensivo, defensivo ou de utilidade.\n"
        "- MANOBRA: Ações de combate não letais (empurrar, agarrar, derrubar, desarmar).\n"
        "- NAVEGAR: Mover-se para outra sala, fugir, andar, subir, descer.\n"
        "- INTERACAO: Examinar, abrir baús, desarmar armadilhas, falar com NPCs, pegar itens.\n"
        "- DESCANSAR: Dormir, montar acampamento, curar feridas, descanso curto/longo.\n"
        "- OUTRO: Qualquer ação livre, conversa, observation que não se encaixe acima.\n\n"
        f"Entrada do Jogador: '{texto_jogador}'\n"
        f"Contexto da Sala: {contexto_sala}"
    )

    fallback_json = {
        "intencao": "OUTRO", "alvo": None, "estilo": None, 
        "magia_usada": None, "manobra": None, "item": None, "direcao": None
    }

    conteudo = ""
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}],
            temperature=0,
            response_format={"type": "json_object"},
            timeout=10.0
        )
        
        conteudo = response.choices[0].message.content.strip()
        dados_json = json.loads(conteudo)
        
        # Validação e Sanitização Estrita
        INTENCOES_VALIDAS = {"COMBATE", "MAGIA", "MANOBRA", "NAVEGAR", "INTERACAO", "DESCANSAR", "OUTRO"}
        intencao = dados_json.get("intencao", "OUTRO").upper()
        
        if intencao not in INTENCOES_VALIDAS:
            logger.warning("[IA JSON] Intenção inválida '%s'. Fallback para OUTRO.", intencao)
            intencao = "OUTRO"
            
        direcao_raw = dados_json.get("direcao")
        direcao = str(direcao_raw).lower() if direcao_raw else None
        resultado = {
            "intencao": intencao,
            "alvo": dados_json.get("alvo"),
            "estilo": dados_json.get("estilo"),
            "magia_usada": dados_json.get("magia_usada"),
            "manobra": dados_json.get("manobra"),
            "item": dados_json.get("item"),
            "direcao": direcao
        }
        
        CACHE_INTENCOES[chave_cache] = resultado
        logger.debug("[IA JSON PROCESSADO] %s", resultado)
        return resultado
        
    except json.JSONDecodeError as e:
        logger.error("[IA JSON] Falha ao parsear JSON: %s — Resposta: %s", e, conteudo)
        return FALLBACK_INTENCAO_JSON
    except Exception as e:
        logger.error("[IA JSON] Erro crítico: %s", e)
        return FALLBACK_INTENCAO_JSON


async def interpretar_acao(acao_jogador: str, interativos_disponiveis: str = "Nenhum") -> str:
    """
    [LEGADO] Envia a ação do jogador para o GPT-4o-mini e retorna a intenção classificada como string.
    """
    acao_limpa = (acao_jogador or '').strip().lower()
    chave_cache = f"{acao_limpa}|{interativos_disponiveis}"

    if chave_cache in CACHE_INTENCOES:
        logger.debug("[CACHE HIT] Intenção recuperada do cache")
        return CACHE_INTENCOES[chave_cache]

    if not _openai_available():
        return "NARRATIVA"

    system_prompt = (
        "És um motor de interpretação estrito para um RPG de texto.\n"
        "A tua ÚNICA função é ler a entrada do jogador e devolver UMA ÚNICA PALAVRA da lista de categorias abaixo.\n\n"
        "REGRAS ABSOLUTAS:\n"
        "1. NÃO narres. NÃO descrevas o que aconteceu.\n"
        "2. NÃO decidas se a ação teve sucesso ou falhou. O motor Python fará os testes de dados.\n"
        "3. Se o jogador descrever algo impossível ou épico (ex: 'dou um salto mortal e decapito o dragão'), responde APENAS a intenção mecânica (COMBATE).\n"
        "4. Responde APENAS com a palavra da categoria em MAIÚSCULAS, sem pontuação extra.\n\n"
        "CATEGORIAS PERMITIDAS:\n"
        "- COMBATE: Atacar fisicamente, golpear inimigos ou objetos destrutíveis.\n"
        "- MAGIA: Lançar um feitiço específico ofensivo ou defensivo.\n"
        "- MANOBRA: Empurrar, agarrar, derrubar, desarmar ou levantar do chão.\n"
        "- NAVEGAR: Andar para outra direção ou lugar (Norte, Sul, Leste, Oeste, Entrar, Sair).\n"
        "- NAVEGAR_FURTIVO: Andar de forma sorrateira ou escondida para outra sala.\n"
        "- INTERACAO_OBJETO: Examinar, ler, abrir baús, destrancar portas, desarmar armadilhas EXCLUSIVAMENTE com os objetos reais.\n"
        "- PEGAR: Coletar ouro, armas ou itens visíveis.\n"
        "- USAR_ITEM: Beber poções, usar objeto do inventário, neutralizar venenos.\n"
        "- COBERTURA: Esconder-se atrás de mesas, colunas ou paredes na mesma sala.\n"
        "- AJUDAR: Dar assistência a um aliado na mesma sala.\n"
        "- DESCANSO: Dormir, montar acampamento, recuperar fôlego fora de combate.\n"
        "- TESTE: Tentar perceber algo oculto, rolar percepção, história, intuição.\n"
        "- NARRATIVA: Falar com NPCs, gritar, observar a sala ou qualquer ação livre que não se encaixe acima.\n\n"
        f"Entrada do Jogador: '{acao_jogador}'\n"
        f"Contexto (Objetos na sala): {interativos_disponiveis}"
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}],
            temperature=0,
            timeout=10.0,
        )
        intencao = response.choices[0].message.content.strip().upper()

        INTENCOES_VALIDAS = {
            "COMBATE", "MAGIA", "NAVEGAR", "TESTE", "NARRATIVA",
            "PEGAR", "USAR_ITEM", "DESCANSO", "NAVEGAR_FURTIVO",
            "INTERACAO_OBJETO", "COBERTURA", "MANOBRA", "AJUDAR"
        }

        if intencao not in INTENCOES_VALIDAS:
            logger.warning("[IA FALHOU] Intenção inválida: %s. Fallback para NARRATIVA.", intencao)
            intencao = "NARRATIVA"

        CACHE_INTENCOES[chave_cache] = intencao
        logger.debug("[IA PROCESSOU] Nova intenção aprendida: %s", intencao)
        return intencao

    except Exception as e:
        logger.error("[IA] Erro ao interpretar ação: %s", e)
        return "NARRATIVA"


async def narrar_combate(jogador_nome: str, acao_jogador: str, resultado_dados: Any, descricao_sala: str) -> str:
    """
    Gera uma narração cinematográfica para um round de combate.
    """
    if not _openai_available():
        return FALLBACK_NARRACAO_COMBATE
    prompt = (
        f"Você é um Mestre de Dungeons & Dragons experiente e visceral.\n\n"
        f"SALA: {descricao_sala}\n"
        f"HERÓI: {jogador_nome}\n"
        f"AÇÃO: {acao_jogador}\n"
        f"DADOS DO SISTEMA: {resultado_dados}\n\n"
        "Narração curta (máximo 3 frases), focada no impacto do golpe e na reação do inimigo."
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Você é o narrador oficial da Cidadela Sem Sol."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            timeout=10.0,
        )
        return _sanitize_ai_html(response.choices[0].message.content)
    except Exception as e:
        logger.error("[IA NARRAÇÃO COMBATE] Erro: %s", e)
        return FALLBACK_NARRACAO_COMBATE


async def decidir_atributo_teste(acao_jogador: str) -> str:
    """
    Define qual atributo de D&D (STR, DEX, etc) deve ser usado para uma ação de TESTE.
    """
    if not _openai_available():
        return FALLBACK_ATRIBUTO
    ATRIBUTOS_VALIDOS = {"STR", "DEX", "CON", "INT", "WIS", "CHA"}
    prompt = (
        f"Dada a ação: '{acao_jogador}', qual atributo de D&D 5e é o mais apropriado?\n"
        "Responda apenas com a sigla: STR, DEX, CON, INT, WIS ou CHA."
    )
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            timeout=10.0
        )
        atr = response.choices[0].message.content.strip().upper()
        if atr not in ATRIBUTOS_VALIDOS:
            logger.warning("[IA] Atributo inválido '%s'. Fallback: INT.", atr)
            return "INT"
        return atr
    except Exception as e:
        logger.error("[IA ATRIBUTO] Erro: %s", e)
        return FALLBACK_ATRIBUTO


async def narrar_ambiente(jogador_nome: str, acao_jogador: str, descricao_sala: str) -> str:
    """
    Gera uma narração imersiva para interações gerais com o ambiente.
    """
    if not _openai_available():
        return FALLBACK_NARRACAO_AMBIENTE
    prompt = (
        f"Você é um Mestre de RPG (Dungeon Master) detalhista e imersivo.\n\n"
        f"CENÁRIO ATUAL: {descricao_sala}\n"
        f"HERÓI: {jogador_nome}\n"
        f"AÇÃO DO HERÓI: {acao_jogador}\n\n"
        "REGRAS ESTRITAS DE NARRAÇÃO:\n"
        "- Descreva o que o herói vê, ouve ou sente ao fazer essa ação no cenário.\n"
        "- Mantenha o clima de D&D de fantasia sombria.\n"
        "- NUNCA tome o controle do herói. Não mova o personagem para outras salas ou tavernas.\n"
        "- Se o jogador não disse explicitamente que andou, ele continua parado no mesmo lugar.\n"
        "- Limite-se a descrever a reação do cenário à ação EXATA do jogador.\n"
        "- REGRA ABSOLUTA DE INVENTÁRIO: NUNCA crie, invente ou narre que o jogador encontrou itens físicos (armas, poções, chaves, dentes, ouro, saques). Descreva APENAS a atmosfera da busca ou a interação com o que já foi fornecido no CENÁRIO ATUAL. As recompensas são injetadas pelo sistema, não por si.\n"
        "- Responda em no máximo 2 parágrafos curtos."
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Você é o narrador oficial da Cidadela Sem Sol."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            timeout=10.0,
        )
        return _sanitize_ai_html(response.choices[0].message.content)
    except Exception as e:
        logger.error("[IA NARRAÇÃO AMBIENTE] Erro: %s", e)
        return FALLBACK_NARRACAO_AMBIENTE


async def extrair_itens_da_narracao(narracao: str) -> List[str]:
    """
    Analisa a narração e extrai itens úteis de forma estruturada.
    Usa response_format json_object para garantir JSON válido e evitar JSONDecodeError.
    """
    if not _openai_available():
        return []
    prompt = (
        "Leia a seguinte narração de RPG e identifique APENAS equipamentos, armas, "
        "poções, ouro ou itens de valor que o jogador explicitamente encontrou e pegou para si.\n"
        "NÃO inclua itens do cenário (ex: 'mesa', 'tocha presa na parede', 'ossos secos').\n"
        "Retorne o resultado EXCLUSIVAMENTE como um objeto JSON com a chave 'itens' contendo uma lista de strings.\n"
        'Exemplo: {"itens": ["Poção de Cura", "Espada Longa"]}\n'
        'Se nenhum item útil foi coletado, retorne: {"itens": []}\n\n'
        f"Narração: {narracao}"
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"},
            timeout=10.0
        )

        conteudo = response.choices[0].message.content.strip()
        dados_json = json.loads(conteudo)
        itens = dados_json.get("itens", [])

        if isinstance(itens, list):
            return itens
        return []

    except Exception as e:
        logger.error("[IA LOOT] Erro ao extrair saque: %s", e)
        return []


async def sanitizar_descricao_para_dalle(descricao_sala: str) -> str:
    """
    Campanha para reescrever a descrição da sala removendo conteúdo
    que viola as políticas do DALL-E (gore, violência explícita, ossos, sangue).
    """
    if not _openai_available():
        return descricao_sala
    prompt = (
        f"Reescreva a seguinte descrição de cenário de fantasia para ser adequada para geração de imagem. "
        f"Remova qualquer menção a: sangue, cadáveres, ossos humanos, gore, violência explícita, morte. "
        f"Substitua por elements atmosféricos equivalentes (ex: 'ossos' → 'pedras antigas', 'sangue' → 'marcas escuras'). "
        f"Mantenha o tom sombrio e de fantasia medieval. Responda apenas com a descrição reescrita, sem comentários.\n\n"
        f"Descrição original: {descricao_sala}"
    )
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            timeout=10.0,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("[FILTRO DALLE] Erro ao sanitizar: %s", e)
        return descricao_sala


async def gerar_imagem_sala(nome_sala: str, descricao_sala: str) -> Optional[str]:
    """
    Gera uma imagem da sala usando DALL-E 3 com Fallback para DALL-E 2.
    Retorna a URL da imagem ou None em caso de erro.
    Usa cache (TTL 24h) para evitar regenerar imagens da mesma sala.
    """
    if not _openai_available():
        return None
    # Cache: se a sala já teve imagem gerada, reutiliza a URL (TTL 24h)
    chave_cache = (nome_sala or "").strip().lower()
    if chave_cache and chave_cache in CACHE_IMAGENS_SALA:
        logger.debug("[CACHE IMAGEM] URL reutilizada para %s", nome_sala)
        return CACHE_IMAGENS_SALA[chave_cache]
    descricao_limpa = await sanitizar_descricao_para_dalle(descricao_sala)

    # Prompt reescrito para ser extremamente "Family Friendly" e evitar o bloqueio 400 da OpenAI
    prompt_imagem = (
        f"A beautiful and atmospheric fantasy digital illustration of a location named '{nome_sala}'. "
        f"Visual elements: {descricao_limpa[:300]}. "
        f"Style: concept art, highly detailed, safe for work, no violence, no gore, peaceful fantasy setting."
    )

    try:
        logger.info("[DALL-E] Gerando imagem para %s no DALL-E 3...", nome_sala)
        response = await client.images.generate(
            model="dall-e-3",
            prompt=prompt_imagem,
            size="1024x1024",
            quality="standard",
            n=1,
            timeout=30.0,
        )
        url = response.data[0].url
        if chave_cache:
            CACHE_IMAGENS_SALA[chave_cache] = url
        logger.info("[DALL-E 3] Imagem gerada com sucesso")
        return url
    except Exception as e:
        logger.warning("[DALL-E 3] Falhou: %s. Tentando DALL-E 2...", e)
        try:
            # Fallback para o DALL-E 2 (não aceita o parâmetro quality, por isso foi removido)
            response = await client.images.generate(
                model="dall-e-2",
                prompt=prompt_imagem[:900],
                size="1024x1024",
                n=1,
                timeout=30.0,
            )
            url = response.data[0].url
            if chave_cache:
                CACHE_IMAGENS_SALA[chave_cache] = url
            logger.info("[DALL-E 2] Imagem gerada via fallback")
            return url
        except Exception as e2:
            logger.error("[DALL-E] Falha total na geração de imagem: %s", e2)
            return None


# =====================================================================
# GERAÇÃO DE IMAGENS CRÍTICAS (FAL.ai)
# =====================================================================

from pathlib import Path
import hashlib

# Cache de imagens críticas (evita regenerar a mesma cena)
CACHE_IMAGENS_CRITICAS: Dict[str, str] = {}
STATIC_CRITICAS = Path(__file__).parent / "app" / "static" / "imagens" / "criticas"
STATIC_CRITICAS.mkdir(parents=True, exist_ok=True)


def _gerar_prompt_critico(contexto: Dict[str, Any]) -> str:
    """Gera um prompt detalhado para FAL.ai baseado no contexto crítico."""
    tipo = contexto.get("tipo", "critico_acerto")
    atacante = contexto.get("atacante", "Guerreiro")
    classe = contexto.get("classe", "Guerreiro")
    arma = contexto.get("arma", "espada")
    alvo = contexto.get("alvo", "monstro")

    if tipo == "critico_acerto":
        prompt = (
            f"Epic fantasy digital painting, dramatic critical hit scene. "
            f"A {classe} named {atacante} wielding a {arma} delivers a devastating blow to a {alvo}. "
            f"Dynamic action pose, magical energy爆发, dramatic lighting, "
            f"particles and sparks flying, intense battle atmosphere. "
            f"Style: cinematic concept art, highly detailed, vibrant colors, "
            f"fantasy RPG aesthetic, 4K quality."
        )
    else:  # critico_falha
        prompt = (
            f"Comedic fantasy digital painting, epic fail moment. "
            f"A {classe} named {atacante} with a {arma} trips and falls dramatically while fighting a {alvo}. "
            f"Slapstick comedy pose, weapon flying through the air, "
            f"clumsy movement, exaggerated expressions, humorous atmosphere. "
            f"Style: cartoon-ish fantasy art, expressive, colorful, "
            f"funny RPG moment, 4K quality."
        )

    return prompt


def _salvar_imagem_critica(contexto: Dict[str, Any], image_data: bytes) -> str:
    """Salva a imagem crítica e retorna a URL local."""
    # Gera um hash único baseado no contexto
    context_str = f"{contexto.get('tipo')}_{contexto.get('atacante')}_{contexto.get('alvo')}"
    file_hash = hashlib.md5(context_str.encode()).hexdigest()[:8]
    filename = f"crit_{contexto.get('tipo')}_{file_hash}.jpg"
    filepath = STATIC_CRITICAS / filename

    with open(filepath, "wb") as f:
        f.write(image_data)

    return f"/static/imagens/criticas/{filename}"


async def gerar_imagem_critica(contexto: Dict[str, Any]) -> Optional[str]:
    """
    Gera uma imagem dramática para acerto/falha crítica usando FAL.ai.
    Retorna a URL da imagem ou None em caso de erro.
    """
    # Cache check
    cache_key = f"{contexto.get('tipo')}_{contexto.get('atacante')}_{contexto.get('alvo')}"
    if cache_key in CACHE_IMAGENS_CRITICAS:
        logger.debug("[CACHE CRITICO] URL reutilizada para %s", contexto.get('atacante'))
        return CACHE_IMAGENS_CRITICAS[cache_key]

    # Importa fal_client apenas quando necessário (evita erro se não instalado)
    try:
        import fal_client
    except ImportError:
        logger.warning("[FAL.AI] fal_client não instalado. Instale com: pip install fal-client")
        return None

    prompt = _gerar_prompt_critico(contexto)

    try:
        logger.info("[FAL.AI] Gerando imagem crítica para %s...", contexto.get('atacante'))

        # BUG #5 FIX: Usar asyncio.to_thread para NÃO bloquear o event loop do FastAPI
        import asyncio
        result = await asyncio.to_thread(
            fal_client.subscribe, "fal-ai/flux/schnell",
            **{
                "arguments": {
                    "prompt": prompt,
                    "image_size": "landscape_16_9",
                    "num_images": 1,
                    "enable_safety_checker": True,
                },
            },
        )

        if result and "images" in result and len(result["images"]) > 0:
            image_url = result["images"][0].get("url")
            if image_url:
                # Baixa e salva localmente
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get(image_url, timeout=30.0)
                    if response.status_code == 200:
                        local_url = _salvar_imagem_critica(contexto, response.content)
                        CACHE_IMAGENS_CRITICAS[cache_key] = local_url
                        logger.info("[FAL.AI] Imagem crítica gerada: %s", local_url)
                        return local_url

        logger.warning("[FAL.AI] Resposta inválida: %s", result)
        return None

    except Exception as e:
        logger.error("[FAL.AI] Erro ao gerar imagem crítica: %s", e)
        return None


# =====================================================================
# NARRAÇÃO DE TAVERNA (Taverneiro do Velho Javali)
# =====================================================================

async def narrar_taverna(
    jogador_nome: str,
    mensagem: str,
    historia_taverna: str,
    npc_nome: str = "O Taverneiro",
    npc_descricao: str = "",
    npc_dialogo_base: str = "",
) -> str:
    """
    Gera uma resposta de um NPC para conversa livre.
    Mantém personalidade do NPC, oferece interação imersiva, não move o jogador.
    Se npc_descricao e npc_dialogo_base forem fornecidos (do banco), usa-os
    como contexto para personalizar a resposta.
    """
    if not _openai_available():
        return _taverna_fallback(jogador_nome, mensagem)

    # Determinar personalidade do NPC baseado no nome
    npc_nome_lower = npc_nome.lower()

    if "taverneiro" in npc_nome_lower or "javali" in npc_nome_lower:
        system_prompt = (
            "Você é o **Taverneiro do Velho Javali**, na Vila de Carvalhal.\n\n"
            "PERSONALIDADE:\n"
            "- Rústico, calejado, visto de tudo. Voz rouca, humor seco.\n"
            "- Sabe dos boatos da região, mas não é fofoqueiro barato.\n"
            "- Respeita aventureiros, mas não baba ovo.\n"
            "- Serve cerveja, hidromel, ensopado. Aluga quartos (5 PO/noite).\n\n"
            "CONHECIMENTO (rumores que pode soltar se perguntarem):\n"
            "- NORTE (Estrada Velha → Cidadela Sem Sol): 'Kobolds tomaram a cidadela. Um dragãozinho foi roubado. O sacerdote Belak cultua uma árvore má lá embaixo.'\n"
            "- LESTE (Trilha Triboar → Phandalin/Minas): 'Gundren Rockseeker partiu com mapa novo pros lados da Trilha Triboar. Não voltou. Goblins tão emboscando caravanas. Phandalin precisa de braços.'\n"
            "- TAVERNA: 'Cerveja 2 PO, hidromel 5 PO, ensopado 3 PO, quarto 5 PO/noite.'\n\n"
            "REGRAS ABSOLUTAS:\n"
            "1. NUNCA mova o jogador.\n"
            "2. NUNCA diga 'você vai para...' ou 'você entra na...'.\n"
            "3. Responda como o taverneiro falando COM o jogador.\n"
            "4. Se pedir aventura, descreva os rumores como fofoca de balcão.\n"
            "5. Máximo 3 parágrafos curtos. Português do Brasil.\n"
            "6. Pode oferecer serviços (bebida, quarto, rumores por moeda).\n"
        )
    elif "estranho" in npc_nome_lower or "capuz" in npc_nome_lower:
        system_prompt = (
            "Você é um **Estranho de Capuz**, um viajante misterioso na taverna.\n\n"
            "PERSONALIDADE:\n"
            "- Misterioso, fala em enigmas e referências obscuras.\n"
            "- Nunca revela seu verdadeiro nome ou propósito.\n"
            "- Parece saber mais do que mostra. Olhar penetrante.\n"
            "- Fuma um cigarro de ervas estranhas.\n\n"
            "CONHECIMENTO:\n"
            "- Sabe coisas sombrias sobre a floresta e criaturas que habitam.\n"
            "- Faz referências a 'sinais' e 'profecias'.\n"
            "- Às vezes alerta sobre perigos, mas de forma críptica.\n\n"
            "REGRAS ABSOLUTAS:\n"
            "1. NUNCA mova o jogador.\n"
            "2. NUNCA se identifique completamente.\n"
            "3. Fale de forma enigmática e misteriosa.\n"
            "4. Máximo 3 parágrafos curtos. Português do Brasil.\n"
            "5. Pode dar dicas sobre a floresta e perigos, mas de forma indireta.\n"
        )
    else:
        # NPC genérico — usa dados do banco se disponíveis
        contexto_banco = ""
        if npc_descricao or npc_dialogo_base:
            contexto_banco = (
                f"DADOS DO NPC DO BANCO:\n"
                f"- Descrição física: {npc_descricao}\n"
                f"- Fala inicial conhecida: '{npc_dialogo_base}'\n\n"
                f"Use estas informações para dar personalidade ao NPC.\n"
                f"Mantenha consistência com a descrição e o tom da fala inicial.\n\n"
            )
        system_prompt = (
            f"{contexto_banco}"
            f"Você é **{npc_nome}**, um personagem em um mundo de fantasia medieval (D&D 5e).\n\n"
            "PERSONALIDADE:\n"
            "- Tem uma personalidade única e interessante baseada na descrição acima.\n"
            "- Reage de forma realista ao que o jogador diz.\n"
            "- Pode oferecer informações, serviços ou apenas conversar.\n"
            "- Fica na sala onde está — não segue o jogador.\n\n"
            "REGRAS ABSOLUTAS:\n"
            "1. NUNCA mova o jogador.\n"
            "2. NUNCA diga 'você vai para...' ou 'você entra na...'.\n"
            "3. Responda como o NPC falando COM o jogador.\n"
            "4. Máximo 3 parágrafos curtos. Português do Brasil.\n"
        )

    prompt = (
        f"{system_prompt}\n\n"
        f"HERÓI: {jogador_nome}\n"
        f"DIZ: '{mensagem}'\n\n"
        f"Responda COMO {npc_nome.upper()}:"
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"Você é {npc_nome}."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            timeout=10.0,
        )
        return _sanitize_ai_html(response.choices[0].message.content.strip())
    except Exception as e:
        logger.error("[IA NPC] Erro: %s", e)
        return _taverna_fallback(jogador_nome, mensagem)


def _taverna_fallback(jogador_nome: str, mensagem: str) -> str:
    """Resposta local do taverneiro quando OpenAI não está disponível."""
    import random as _random
    msg = mensagem.lower()

    # Aventura / rumores
    if any(p in msg for p in ["aventura", "rumor", "missao", "missão", "o que tem", "onde ir", "procurando"]):
        return (
            f"O taverneiro limpa um copo e te olha nos olhos. 'Aventuras, {jogador_nome}? "
            "Temos duas estradas saindo daqui...'\n\n"
            "Ele aponta pro norte. 'Pela **Estrada Velha** vai dar na **Cidadela Sem Sol**. "
            "Dizem que kobolds tomaram o lugar e roubaram um dragãozinho. "
            "O sacerdote Belak tá cultuando uma árvore má lá embaixo. Perigoso, mas tem tesouro.'\n\n"
            "Depois aponta pro leste. 'Pela **Trilha Triboar** vai pra **Phandalin**, nas **Minas Perdidas**. "
            "Gundren Rockseeker partiu com mapa novo e não voltou. Goblins tão emboscando caravanas. "
            "A vila precisa de heróis.'"
        )

    # Norte / Cidadela
    if any(p in msg for p in ["norte", "cidadela", "kobold", "dragão", "belak", "árvore", "gulthias"]):
        return (
            "'A **Cidadela Sem Sol**... coisa feia lá, garoto. "
            "Kobolds da tribo Pedra Quebrada tomaram o lugar. "
            "O chefe deles, um tal de Durnn, fez aliança com um sacerdote louco — Belak, o Proscrito. "
            "Ele cultua a **Árvore Gulthias**, uma árvore má que brota nas profundezas. "
            "Dizem que até um dragãozinho, o Calcryx, foi roubado pelos kobolds. "
            "Um kobold chamado Meepo anda pedindo ajuda pra achar o bicho. "
            "Se tiver peito, pega a Estrada Velha ao norte. Mas cuidado: as armadilhas lá são traiçoeiras.'"
        )

    # Leste / Phandelver / Minas
    if any(p in msg for p in ["leste", "phandelver", "phandalin", "mina", "gundren", "rockseeker", "triboar", "goblin", "forja"]):
        return (
            "'A **Trilha Triboar** a leste... caminho perigoso ultimamente. "
            "**Gundren Rockseeker**, um anão mineiro, partiu com mapa novo pros lados da **Mina Perdida de Phandelver** — "
            "a lendária **Forja das Magias**. Não voltou. "
            "Goblins da **Tribo Pedra Quebrada** tão emboscando caravanas na trilha. "
            "A vila de **Phandalin** tá precisando de braços bons. "
            "Se for por lá, passa na estalagem Colina de Pedra. "
            "O Toblen, dono do lugar, paga bem por informações sobre Gundren.'"
        )

    # Serviços da taverna
    if any(p in msg for p in ["cerveja", "bebida", "hidromel", "ensopado", "comida", "quarto", "dormir", "hospedagem", "preço", "custa"]):
        return (
            "'Serviços do **Velho Javali**, anota aí:'\n\n"
            "🍺 **Cerveja** — 2 PO (gelada, boa pra esquecer o dia)\n"
            "🍯 **Hidromel** — 5 PO (forte, esquenta a alma)\n"
            "🍲 **Ensopado do Javali** — 3 PO (carne, raízes, segredo do chef)\n"
            "🛏️ **Quarto** — 5 PO/noite (cama de palha, cobertor de lã, porta que tranca)\n\n"
            "'Pagamento adiantado, nada de fiado. O que vai ser, herói?'"
        )

    # Saudação genérica
    if any(p in msg for p in ["oi", "olá", "eae", "salve", "bom dia", "boa tarde", "boa noite", "tudo bem"]):
        return (
            f"'Bem-vindo ao **Velho Javali**, {jogador_nome}. "
            "O que vai ser? Cerveja, hidromel, ensopado, quarto... ou rumores?'"
        )

    # Resposta padrão
    respostas = [
        "O taverneiro limpa um copo devagar, sem tirar os olhos de você. 'Fala, aventureiro. Em que posso ajudar?'",
        "'Mais um na estrada, hein? O Velho Javali tá aberto pra quem tem moeda e coragem. O que procura?'",
        "Ele apoia os cotovelos no balcão. 'Rumores, bebida, cama... ou só quer ouvir a chuva lá fora? Decide.'",
        "O taverneiro bufa. 'Não sou oráculo, garoto. Mas ouço coisas. O que você quer saber?'"
    ]
    return _random.choice(respostas)