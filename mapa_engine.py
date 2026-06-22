# mapa_engine.py
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente para garantir que a API KEY esteja disponível
load_dotenv()

_openai_key = os.getenv("OPENAI_API_KEY")
client = AsyncOpenAI(api_key=_openai_key) if _openai_key else None

# Cache TTL para evitar chamadas repetitivas à API + evitar memory leak
# Chave: (texto_jogador, opcoes_estáticas) -> Valor: direção_extraída
from collections import OrderedDict

try:
    from cachetools import TTLCache
    DIRECAO_CACHE = TTLCache(maxsize=500, ttl=3600)
except ImportError:
    class _BoundedCache(OrderedDict):
        """Cache fallback com limite de tamanho (evita memory leak)."""
        def __init__(self, maxsize=500, *args, **kwargs):
            self._maxsize = maxsize
            super().__init__(*args, **kwargs)

        def __setitem__(self, key, value):
            if key not in self:
                while len(self) >= self._maxsize:
                    self.popitem(last=False)
            super().__setitem__(key, value)

    DIRECAO_CACHE = _BoundedCache(maxsize=500)

async def extrair_direcao(texto_jogador: str, conexoes_validas: dict):
    """
    Analisa o texto do jogador e tenta mapeá-lo para uma das saídas válidas da sala.
    """
    # 1. Normalização e Preparação
    texto_limpo = texto_jogador.strip().lower()
    opcoes_lista = [k.lower() for k in conexoes_validas.keys()]
    if not opcoes_lista:
        return "invalido"
    opcoes_str = ", ".join(opcoes_lista)
    
    # 2. Verificação de Cache (Performance e Economia de Tokens)
    cache_key = (texto_limpo, opcoes_str)
    if cache_key in DIRECAO_CACHE:
        return DIRECAO_CACHE[cache_key]

    # 3. Prompt Estrito para Extração Determinística
    prompt = (
        f"O jogador disse: '{texto_jogador}'.\n"
        f"As saídas REAIS disponíveis nesta sala são: {opcoes_str}.\n\n"
        "REGRAS DE RESPOSTA:\n"
        "1. Se a intenção do jogador for ir para uma das saídas da lista, responda APENAS a palavra da saída em minúsculo.\n"
        "2. Se o jogador mencionou algo que NÃO está na lista, ou se a direção for ambígua, responda EXATAMENTE 'invalido'.\n"
        "3. NÃO escreva frases. NÃO explique. NÃO sugira.\n"
        "4. Responda apenas a palavra da direção ou 'invalido'."
    )

    try:
        if not client:
            return "invalido"
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Você é um extrator de direções geográficas rigoroso."},
                {"role": "user", "content": prompt}
            ],
            temperature=0, # Zero para garantir determinismo
            timeout=10.0
        )
        
        resultado = response.choices[0].message.content.strip().lower()
        
        # Validação final: garante que a IA não inventou uma direção fora da lista
        if resultado in opcoes_lista:
            DIRECAO_CACHE[cache_key] = resultado
            return resultado
        else:
            DIRECAO_CACHE[cache_key] = "invalido"
            return "invalido"
            
    except Exception as e:
        print(f"[MAPA] Erro crítico ao extrair direção: {e}")
        return "invalido"


# =====================================================================
# VERSÃO SÍNCRONA (para ActionResolver síncrono do FastAPI)
# =====================================================================
from openai import OpenAI
client_sync = OpenAI(api_key=_openai_key) if _openai_key else None

def extrair_direcao_sync(texto_jogador: str, conexoes_validas: dict) -> str:
    """
    Versão síncrona de extrair_direcao. Usa OpenAI client síncrono.
    """
    texto_limpo = texto_jogador.strip().lower()
    opcoes_lista = [k.lower() for k in conexoes_validas.keys()]
    opcoes_str = ", ".join(opcoes_lista)

    cache_key = (texto_limpo, opcoes_str)
    if cache_key in DIRECAO_CACHE:
        return DIRECAO_CACHE[cache_key]

    if not opcoes_lista:
        return "invalido"

    if not client_sync:
        return "invalido"

    prompt = (
        f"O jogador disse: '{texto_jogador}'.\n"
        f"As saídas REAIS disponíveis nesta sala são: {opcoes_str}.\n\n"
        "REGRAS DE RESPOSTA:\n"
        "1. Se a intenção do jogador for ir para uma das saídas da lista, responda APENAS a palavra da saída em minúsculo.\n"
        "2. Se o jogador mencionou algo que NÃO está na lista, ou se a direção for ambígua, responda EXATAMENTE 'invalido'.\n"
        "3. NÃO escreva frases. NÃO explique. NÃO sugira.\n"
        "4. Responda apenas a palavra da direção ou 'invalido'."
    )

    try:
        response = client_sync.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Você é um extrator de direções geográficas rigoroso."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            timeout=10.0
        )
        resultado = response.choices[0].message.content.strip().lower()
        if resultado in opcoes_lista:
            DIRECAO_CACHE[cache_key] = resultado
            return resultado
        else:
            DIRECAO_CACHE[cache_key] = "invalido"
            return "invalido"
    except Exception as e:
        print(f"[MAPA SYNC] Erro ao extrair direção: {e}")
        return "invalido"