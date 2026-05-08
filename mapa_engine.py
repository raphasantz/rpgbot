# mapa_engine.py
from openai import AsyncOpenAI
import os

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def extrair_direcao(texto_jogador, conexoes_validas):
    # Convertemos as chaves para minúsculo para a IA classificar com precisão
    opcoes = ", ".join([k.lower() for k in conexoes_validas.keys()])

    # Prompt ajustado para forçar o retorno em minúsculo e evitar falsos positivos
    prompt = (
        f"O jogador disse: '{texto_jogador}'.\n"
        f"As saídas REAIS disponíveis são: {opcoes}.\n\n"
        "REGRAS:\n"
        "1. Se o que o jogador disse corresponder a uma das saídas, responda APENAS o nome da saída em minúsculo.\n"
        "2. Se o jogador mencionou uma direção que NÃO está na lista de saídas reais, responda 'INVALIDO'.\n"
        "3. Não tente adivinhar ou sugerir saídas que não estão na lista.\n"
        "Responda APENAS a palavra da direção em minúsculo ou 'INVALIDO'."
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response.choices[0].message.content.strip().lower()
    except Exception as e:
        print(f"[MAPA] Erro ao extrair direção: {e}")
        return "invalido"