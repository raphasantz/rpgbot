import asyncio, sys
sys.path.insert(0, "/home/mesanerd")
from dotenv import load_dotenv
load_dotenv("/home/mesanerd/.env")

from ai_engine_web import _openai_available, client, narrar_taverna

print("OpenAI available:", _openai_available())

async def test():
    try:
        resp = await narrar_taverna(
            "Teste", "quero uma cerveja", "",
            npc_nome="O Taverneiro",
            npc_descricao="",
            npc_dialogo_base="",
        )
        print("RESPOSTA:", resp[:500])
    except Exception as e:
        print("ERRO:", type(e).__name__, str(e)[:500])

asyncio.run(test())
