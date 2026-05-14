# api.py (Adições ao ficheiro existente)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from database import get_db_session
from models import Jogador, Campanha, Cena, Inimigo, Encontro
from combat_logic import processar_ataque_fisico
import random

app = FastAPI(title="RPG RedNerds API", version="1.0")

# ... (Rotas anteriores mantidas) ...

# ---------------------------------------------------------
# MODELOS DE DADOS (O que o Godot Envia e Recebe)
# ---------------------------------------------------------

class ActionRequest(BaseModel):
    intention: str  # Ex: "COMBATE", "NAVEGAR", "INTERACAO_OBJETO"
    direction: Optional[str] = None # Ex: "norte", "sul"
    target_id: Optional[int] = None # ID do inimigo ou objeto
    text_input: Optional[str] = None # Se o jogador usar um chat no Godot

class EnemyState(BaseModel):
    id: int
    name: str
    hp_current: int
    hp_max: int
    image_url: Optional[str] = None
    is_boss: bool = False

class PlayerState(BaseModel):
    id: str
    name: str
    hp_current: int
    hp_max: int
    ca: int
    gold: int
    weapon: str
    status_effects: List[str]

class SceneState(BaseModel):
    cod_sala: str
    nome_sala: str
    descricao_visual: str
    image_url: Optional[str] = None
    exits: Dict[str, str] # Ex: {"norte": "sala_2", "sul": "sala_3"}
    enemies: List[EnemyState] = []
    in_combat: bool = False

class ActionResponse(BaseModel):
    success: bool
    narrative: str # O texto do que aconteceu (Deus, que o Godot pode mostrar num log)
    player_state: PlayerState
    scene_state: SceneState
    combat_data: Optional[Dict[str, Any]] = None # Dados detalhados de dano/acerto para animações

# ---------------------------------------------------------
# ROTAS DO GODOT
# ---------------------------------------------------------

@app.get("/api/scene/{telegram_id}", response_model=SceneState)
def get_scene_state(telegram_id: str):
    """O Godot chama isto para saber O QUE desenhar na tela atual."""
    with get_db_session() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == telegram_id).first()
        if not jogador: raise HTTPException(404, "Jogador não encontrado")
        
        campanha = db.query(Campanha).filter(Campanha.party_id == jogador.party_id).first()
        if not campanha: raise HTTPException(404, "Campanha não encontrada")

        sala = db.query(Cena).filter(Cena.cod_sala == campanha.cena_atual).first()
        if not sala: raise HTTPException(404, "Sala não encontrada")

        # Mapear inimigos vivos na sala
        encontros = db.query(Encontro).filter(Encontro.cod_sala == sala.cod_sala).all()
        estado_campanha = campanha.estado_salas or {}
        enemies = []
        for enc in encontros:
            if not estado_campanha.get(f"derrotado_{enc.id}"):
                inimigo_model = db.query(Inimigo).filter(Inimigo.nome == enc.nome_inimigo).first()
                if inimigo_model:
                    hp_key = f"hp_{enc.id}"
                    hp_max = inimigo_model.hp_max * enc.quantidade
                    hp_current = estado_campanha.get(hp_key, hp_max)
                    enemies.append(EnemyState(
                        id=enc.id,
                        name=enc.nome_inimigo,
                        hp_current=hp_current,
                        hp_max=hp_max,
                        image_url=inimigo_model.imagem_url,
                        is_boss=inimigo_model.is_boss
                    ))

        return SceneState(
            cod_sala=sala.cod_sala,
            nome_sala=sala.nome_sala,
            descricao_visual=sala.descricao_visual,
            image_url=sala.imagem_url,
            exits=sala.conexoes or {},
            enemies=enemies,
            in_combat=campanha.em_combate
        )

@app.post("/api/action/{telegram_id}", response_model=ActionResponse)
def execute_action(telegram_id: str, req: ActionRequest):
    """O Godot chama isto quando o jogador clica num botão (Atacar, Andar, etc)."""
    with get_db_session() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == telegram_id).first()
        if not jogador: raise HTTPException(404, "Jogador não encontrado")
        
        campanha = db.query(Campanha).filter(Campanha.party_id == jogador.party_id).first()
        sala = db.query(Cena).filter(Cena.cod_sala == campanha.cena_atual).first()
        
        narrative = ""
        combat_data = {}
        
        # --- LÓGICA DE NAVEGAÇÃO (Exemplo) ---
        if req.intention == "NAVEGAR" and req.direction:
            conexoes = sala.conexoes or {}
            dir_lower = req.direction.lower()
            if dir_lower in conexoes:
                nova_sala_cod = conexoes[dir_lower]
                campanha.cena_anterior = campanha.cena_atual
                campanha.cena_atual = nova_sala_cod
                narrative = f"Moveste-te para {dir_lower}."
                # (Aqui adicionavas a verificação de hazards e encontros aleatórios)
            else:
                narrative = "Caminho bloqueado!"

        # --- LÓGICA DE COMBATE (Exemplo Simplificado) ---
        elif req.intention == "COMBATE" and req.target_id:
            encontro = db.query(Encontro).filter(Encontro.id == req.target_id).first()
            inimigo = db.query(Inimigo).filter(Inimigo.nome == encontro.nome_inimigo).first()
            
            # Usa o teu motor de combate existente!
            resultado = processar_ataque_fisico(jogador, inimigo.ca)
            
            combat_data = {
                "d20_roll": resultado.d20,
                "total_attack": resultado.total_ataque,
                "hit": resultado.acertou,
                "critical": resultado.critico,
                "damage_dealt": resultado.dano if resultado.acertou else 0
            }
            
            if resultado.acertou:
                narrative = f"Acertaste! Causaste {resultado.dano} de dano."
                # (Aqui atualizavas o hp_grupo no estado_salas como fazes no exploracao.py)
            else:
                narrative = "O teu ataque falhou!"

        # Atualiza o estado do jogador para enviar de volta ao Godot
        player_state = PlayerState(
            id=jogador.telefone,
            name=jogador.nome,
            hp_current=jogador.hp_atual,
            hp_max=jogador.hp_maximo,
            ca=jogador.modificador_defesa,
            gold=jogador.gold,
            weapon=jogador.arma_equipada,
            status_effects=jogador.status_efeitos or []
        )

        # Busca o estado atualizado da cena
        scene_state = get_scene_state(telegram_id) # Reutiliza a função de cima

        return ActionResponse(
            success=True,
            narrative=narrative,
            player_state=player_state,
            scene_state=scene_state,
            combat_data=combat_data if combat_data else None
        )