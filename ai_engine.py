import os
import json
from typing import Dict, Any
from openai import AsyncOpenAI
from dotenv import load_dotenv

try:
    from cachetools import TTLCache
    CACHE_INTENCOES = TTLCache(maxsize=1000, ttl=3600)
except ImportError:
    CACHE_INTENCOES = {}

# Carrega as variáveis de ambiente
load_dotenv()

# Cliente assíncrono — não bloqueia o event loop do aiogram
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def interpretar_acao_json(texto_jogador: str, contexto_sala: str = "Nenhum") -> Dict[str, Any]:
    """
    Envia a ação do jogador para o GPT-4o-mini e retorna um JSON estruturado com a intenção e parâmetros mecânicos.
    Usa o response_format nativo para garantir um JSON válido.
    """
    acao_limpa = texto_jogador.strip().lower()
    chave_cache = f"json_{acao_limpa}|{contexto_sala}"
    
    if chave_cache in CACHE_INTENCOES:
        print(f"⚡ [CACHE HIT] Intenção JSON recuperada: {CACHE_INTENCOES[chave_cache]}")
        return CACHE_INTENCOES[chave_cache]

    system_prompt = (
        "És um motor de extração de intenções estrito para um RPG de texto baseado em D&D 5e.\n"
        "A tua ÚNICA função é ler a entrada do jogador e extrair a intenção mecânica num formato JSON pré-definido.\n\n"
        "REGRAS ABSOLUTAS:\n"
        "1. NUNCA narres ou decidas o resultado da ação (sucesso/falha).\n"
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
        '  "direcao": "norte | sul | leste | oeste | dentro | fora | null"\n'
        "}\n\n"
        "MAPEAMENTO DE INTENÇÕES:\n"
        "- COMBATE: Atacar fisicamente, golpear, atirar.\n"
        "- MAGIA: Lançar um feitiço específico ofensivo, defensivo ou de utilidade.\n"
        "- MANOBRA: Ações de combate não letais (empurrar, agarrar, derrubar, desarmar).\n"
        "- NAVEGAR: Mover-se para outra sala, fugir, andar.\n"
        "- INTERACAO: Examinar, abrir baús, desarmar armadilhas, falar com NPCs, pegar itens.\n"
        "- DESCANSAR: Dormir, montar acampamento, curar feridas, descanso curto/longo.\n"
        "- OUTRO: Qualquer ação livre, conversa, observação que não se encaixe acima.\n\n"
        f"Entrada do Jogador: '{texto_jogador}'\n"
        f"Contexto da Sala: {contexto_sala}"
    )

    fallback_json = {
        "intencao": "OUTRO", "alvo": None, "estilo": None, 
        "magia_usada": None, "manobra": None, "item": None, "direcao": None
    }

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        conteudo = response.choices[0].message.content.strip()
        dados_json = json.loads(conteudo)
        
        # Validação e Sanitização Estrita
        INTENCOES_VALIDAS = {"COMBATE", "MAGIA", "MANOBRA", "NAVEGAR", "INTERACAO", "DESCANSAR", "OUTRO"}
        intencao = dados_json.get("intencao", "OUTRO").upper()
        
        if intencao not in INTENCOES_VALIDAS:
            print(f"⚠️ [IA JSON] Intenção inválida '{intencao}'. Fallback para OUTRO.")
            intencao = "OUTRO"
            
        resultado = {
            "intencao": intencao,
            "alvo": dados_json.get("alvo"),
            "estilo": dados_json.get("estilo"),
            "magia_usada": dados_json.get("magia_usada"),
            "manobra": dados_json.get("manobra"),
            "item": dados_json.get("item"),
            "direcao": dados_json.get("direcao")
        }
        
        CACHE_INTENCOES[chave_cache] = resultado
        print(f"🧠 [IA JSON PROCESSADO] {resultado}")
        return resultado
        
    except json.JSONDecodeError as e:
        print(f"❌ [IA JSON] Falha ao parsear JSON: {e} - Resposta: {conteudo}")
        return fallback_json
    except Exception as e:
        print(f"❌ [IA JSON] Erro crítico: {e}")
        return fallback_json

# =====================================================================
# FUNÇÕES LEGADAS E NARRATIVAS (MANTIDAS INTACTAS)
# =====================================================================

async def interpretar_acao(acao_jogador, interativos_disponiveis="Nenhum"):
    """
    [LEGADO] Envia a ação do jogador para o GPT-4o-mini e retorna a intenção classificada como string.
    """
    acao_limpa = acao_jogador.strip().lower()
    chave_cache = f"{acao_limpa}|{interativos_disponiveis}"
    
    if chave_cache in CACHE_INTENCOES:
        print(f"⚡ [CACHE HIT] Intenção recuperada da memória: {CACHE_INTENCOES[chave_cache]}")
        return CACHE_INTENCOES[chave_cache]

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
        )
        intencao = response.choices[0].message.content.strip().upper()
        
        INTENCOES_VALIDAS = {
            "COMBATE", "MAGIA", "NAVEGAR", "TESTE", "NARRATIVA", 
            "PEGAR", "USAR_ITEM", "DESCANSO", "NAVEGAR_FURTIVO", 
            "INTERACAO_OBJETO", "COBERTURA", "MANOBRA", "AJUDAR"
        }
        
        if intencao not in INTENCOES_VALIDAS:
            print(f"⚠️ [IA FALHOU] Intenção inválida detectada: {intencao}. Fallback para NARRATIVA.")
            intencao = "NARRATIVA"
        
        CACHE_INTENCOES[chave_cache] = intencao
        print(f"🧠 [IA PROCESSOU] Nova intenção aprendida: {intencao}")
        return intencao
        
    except Exception as e:
        print(f"Erro na IA (Interpretar Ação): {e}")
        return "NARRATIVA"

async def narrar_combate(jogador_nome, acao_jogador, resultado_dados, descricao_sala):
    """
    Gera uma narração cinematográfica para um round de combate.
    """
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
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Você avança e executa sua ação contra o inimigo."

async def decidir_atributo_teste(acao_jogador):
    """
    Define qual atributo de D&D (STR, DEX, etc) deve ser usado para uma ação de TESTE.
    """
    ATRIBUTOS_VALIDOS = {"STR", "DEX", "CON", "INT", "WIS", "CHA"}
    prompt = (
        f"Dada a ação: '{acao_jogador}', qual atributo de D&D 5e é o mais apropriado?\n"
        "Responda apenas com a sigla: STR, DEX, CON, INT, WIS ou CHA."
    )
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        atr = response.choices[0].message.content.strip().upper()
        if atr not in ATRIBUTOS_VALIDOS:
            print(f"⚠️ [IA] Atributo inválido '{atr}' ignorado. Fallback: INT.")
            return "INT"
        return atr
    except Exception as e:
        return "STR"

async def narrar_ambiente(jogador_nome, acao_jogador, descricao_sala):
    """
    Gera uma narração imersiva para interações gerais com o ambiente.
    """
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
        )
        return response.choices[0].message.content
    except Exception as e:
        return "Você observa o ambiente ao seu redor, mas nada fora do comum chama sua atenção."

async def extrair_itens_da_narracao(narracao: str) -> list:
    """
    Analisa a narração e extrai itens úteis de forma estruturada.
    Usa response_format json_object para garantir JSON válido e evitar JSONDecodeError.
    """
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
            response_format={"type": "json_object"}
        )
        
        conteudo = response.choices[0].message.content.strip()
        dados_json = json.loads(conteudo)
        itens = dados_json.get("itens", [])
        
        if isinstance(itens, list):
            return itens
        return []
        
    except Exception as e:
        print(f"❌ Erro crítico ao extrair saque (Loot falhou): {e}")
        return []

async def sanitizar_descricao_para_dalle(descricao_sala):
    """
    Usa o GPT para reescrever a descrição da sala removendo conteúdo
    que viola as políticas do DALL-E (gore, violência explícita, ossos, sangue).
    """
    prompt = (
        f"Reescreva a seguinte descrição de cenário de fantasia para ser adequada para geração de imagem. "
        f"Remova qualquer menção a: sangue, cadáveres, ossos humanos, gore, violência explícita, morte. "
        f"Substitua por elementos atmosféricos equivalentes (ex: 'ossos' → 'pedras antigas', 'sangue' → 'marcas escuras'). "
        f"Mantenha o tom sombrio e de fantasia medieval. Responda apenas com a descrição reescrita, sem comentários.\n\n"
        f"Descrição original: {descricao_sala}"
    )
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[FILTRO DALLE] Erro ao sanitizar: {e}")
        return descricao_sala

async def gerar_imagem_sala(nome_sala, descricao_sala):
    """
    Gera uma imagem da sala usando DALL-E 3.
    Retorna a URL da imagem ou None em caso de erro.
    """
    descricao_limpa = await sanitizar_descricao_para_dalle(descricao_sala)

    prompt_imagem = (
        f"Fantasy dark dungeon RPG scene, D&D style illustration. "
        f"Location: {nome_sala}. "
        f"Scene description: {descricao_limpa[:300]}. "
        f"Style: detailed fantasy art, dramatic lighting, dark atmosphere, high quality."
    )

    try:
        response = await client.images.generate(
            model="dall-e-3",
            prompt=prompt_imagem,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        url = response.data[0].url
        print(f"🎨 [DALL-E] Imagem gerada para '{nome_sala}': {url}")
        return url
    except Exception as e:
        print(f"⚠️ [DALL-E] Erro ao gerar imagem para '{nome_sala}': {e}")
        return None