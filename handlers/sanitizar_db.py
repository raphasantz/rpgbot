from database import get_db_session
from models import Jogador
import json

def sanitizar_banco():
    print("Iniciando saneamento do inventário...")
    with get_db_session() as db:
        jogadores = db.query(Jogador).all()
        count = 0
        for j in jogadores:
            # Se o inventário for uma string, precisamos limpar
            if isinstance(j.inventario, str):
                try:
                    # Tenta converter a string em lista
                    lista_limpa = json.loads(j.inventario.replace("'", '"'))
                    j.inventario = lista_limpa
                    count += 1
                except:
                    # Se falhar, zera o inventário corrompido ou trata manualmente
                    j.inventario = [] 
                    count += 1
            
            # Garante que status_efeitos também é lista
            if isinstance(j.status_efeitos, str):
                j.status_efeitos = []
                
        db.commit()
    print(f"Saneamento concluído! {count} jogadores tiveram o inventário corrigido.")

if __name__ == "__main__":
    sanitizar_bancofrom database import get_db_session
from models import Jogador
import json

def sanitizar_banco():
    print("Iniciando saneamento do inventário...")
    with get_db_session() as db:
        jogadores = db.query(Jogador).all()
        count_sucesso = 0
        count_falha = 0
        
        for j in jogadores:
            # Limpeza do Inventário
            if isinstance(j.inventario, str):
                try:
                    # Tenta converter a string em lista
                    lista_limpa = json.loads(j.inventario.replace("'", '"'))
                    j.inventario = lista_limpa
                    count_sucesso += 1
                except Exception as e:
                    # SE FALHAR, NÃO APAGA NADA! Só avisa.
                    print(f"⚠️ Atenção: O inventário de {j.nome} está muito bagunçado e não foi alterado. Valor atual: {j.inventario}")
                    count_falha += 1
            
            # Limpeza dos Efeitos
            if isinstance(j.status_efeitos, str):
                try:
                    lista_efeitos = json.loads(j.status_efeitos.replace("'", '"'))
                    j.status_efeitos = lista_efeitos
                except:
                    j.status_efeitos = [] # Efeitos negativos nós podemos zerar sem stress
                
        db.commit()
    print(f"✅ Saneamento concluído! {count_sucesso} inventários limpos com sucesso. {count_falha} ignorados para evitar perdas.")

if __name__ == "__main__":
    sanitizar_banco()()