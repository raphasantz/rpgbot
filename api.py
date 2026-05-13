from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from database import get_db_session
from models import Jogador, Campanha, Cena
import uvicorn

# Inicializa a nossa API
app = FastAPI(title="RPG RedNerds API", description="Backend para o Godot 4", version="1.0")

# ---------------------------------------------------------
# MODELOS DE DADOS (Como o Python espera receber os pedidos)
# ---------------------------------------------------------
class LoginRequest(BaseModel):
    codigo_acesso: str  # Pode ser o telefone ou o código da Party para testarmos

# ---------------------------------------------------------
# ROTAS (Endpoints)
# ---------------------------------------------------------

@app.get("/")
def ler_status_servidor():
    """Rota raiz apenas para o Godot testar se o servidor está vivo."""
    return {
        "status": "online", 
        "mensagem": "A Taverna está aberta! O Servidor Python está a ouvir e pronto para a aventura."
    }

@app.post("/api/login")
def login_godot(req: LoginRequest):
    """O Godot envia o código, o Python devolve a ficha do personagem."""
    with get_db_session() as db:
        # Para facilitar o nosso teste inicial, vamos deixar o jogador logar 
        # usando o "telefone" (User ID do Telegram) que está no banco de dados.
        jogador = db.query(Jogador).filter(Jogador.telefone == req.codigo_acesso).first()
        
        if not jogador:
            raise HTTPException(status_code=404, detail="Aventureiro não encontrado. Verifica o código.")
        
        # Buscar os dados da sala atual onde o jogador está
        sala = db.query(Cena).filter(Cena.cod_sala == jogador.cena_atual).first()
        nome_sala = sala.nome_sala if sala else "O Vazio"

        # Devolvemos ao Godot apenas o que ele precisa para desenhar a tela
        return {
            "sucesso": True,
            "jogador": {
                "id_conta": jogador.telefone,
                "nome": jogador.nome,
                "classe": jogador.classe,
                "nivel": jogador.nivel,
                "hp_atual": jogador.hp_atual,
                "hp_maximo": jogador.hp_maximo,
                "gold": jogador.gold,
                "cena_atual": jogador.cena_atual,
                "nome_sala_atual": nome_sala
            }
        }

# Executa o servidor na porta 8000
if __name__ == "__main__":
    print("🚀 A iniciar a API do Godot na porta 8000...")
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)