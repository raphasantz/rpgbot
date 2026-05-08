import os
import json
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

async def interpretar_acao(acao_jogador, interativos_disponiveis="Nenhum"):
    """
    Envia a ação do jogador para o GPT-4o-mini e retorna a intenção classificada.
    Usa um sistema de cache em memória para economizar tokens e acelerar respostas repetidas.
    """
    # 1. Limpa a string para o cache ser preciso e adiciona contexto
    acao_limpa = acao_jogador.strip().lower()
    chave_cache = f"{acao_limpa}|{interativos_disponiveis}"
    
    # 2. Verifica se a IA já pensou sobre isso antes neste mesmo contexto
    if chave_cache in CACHE_INTENCOES:
        print(f"⚡ [CACHE HIT] Intenção recuperada da memória: {CACHE_INTENCOES[chave_cache]}")
        return CACHE_INTENCOES[chave_cache]

    system_prompt = (
        f"Você é um motor de processamento de linguagem natural para um jogo de RPG de mesa (D&D 5e).\n"
        f"Analise a seguinte ação de um jogador: '{acao_jogador}'.\n"
        f"Objetos interativos REAIS na sala atual: {interativos_disponiveis}\n\n"
        "Classifique a intenção principal do jogador em uma das seguintes categorias:\n"
        "1. COMBATE (Atacar, lutar, usar arma)\n"
        "2. MAGIA (Lançar um feitiço específico)\n"
        "3. NAVEGAR (Mover-se para uma direção ou lugar: Norte, Sul, Entrar, Sair, Subir, Descer)\n"
        "4. TESTE (Ações que exigem perícias como Investigar, Atletismo, Percepção)\n"
        "5. NARRATIVA (Falar, observar, interagir socialmente ou ações livres)\n"
        "6. PEGAR (Coletar itens ou tesouros)\n"
        "7. USAR_ITEM (Usar um item do inventário, beber poção, usar objeto do cenário)\n"
        "8. DESCANSO (Dormir, descansar, acampar, recuperar vida)\n"
        "9. NAVEGAR_FURTIVO (Mover-se com cautela, furtividade ou stealth para uma direção)\n"
        "10. INTERACAO_OBJETO (se tentar examinar, ler, abrir, destrancar, desarmar ou interagir EXCLUSIVAMENTE com os objetos REAIS listados acima)\n"
        "11. COBERTURA (Esconder-se atrás de mesas, colunas, barris ou paredes para ganhar proteção)\n"
        "12. MANOBRA (Tentar empurrar, agarrar, derrubar, desarmar ou usar táticas físicas contra o inimigo)\n\n"
        "Responda APENAS com o nome da categoria em MAIÚSCULO."
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
            ],
            temperature=0,
        )
        intencao = response.choices[0].message.content.strip().upper()
        
        # Validação Estrita (Whitelist)
        INTENCOES_VALIDAS = {
            "COMBATE", "MAGIA", "NAVEGAR", "TESTE", "NARRATIVA", 
            "PEGAR", "USAR_ITEM", "DESCANSO", "NAVEGAR_FURTIVO", 
            "INTERACAO_OBJETO", "COBERTURA", "MANOBRA", "AJUDAR"
        }
        
        if intencao not in INTENCOES_VALIDAS:
            print(f"⚠️ [IA FALHOU] Intenção inválida detectada: {intencao}. Fallback para NARRATIVA.")
            intencao = "NARRATIVA"
        
        # 3. Salva a resposta no cache para o futuro com o contexto
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
        # Validação Estrita (Whitelist) — evita atributos fantasmas
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
            response_format={"type": "json_object"}  # Garante JSON válido nativamente
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
    Retorna uma versão segura e visualmente descritiva.
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
        return descricao_sala  # Fallback: usa a original mesmo

async def gerar_imagem_sala(nome_sala, descricao_sala):
    """
    Gera uma imagem da sala usando DALL-E 3.
    Retorna a URL da imagem ou None em caso de erro.
    """
    # Sanitiza a descrição antes de enviar ao DALL-E
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
