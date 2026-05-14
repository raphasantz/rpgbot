from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from database import get_db_session
from models import Jogador, Campanha, Cena, Encontro, Inimigo, Interativo, ObjetoDestrutivel, Npc
from combat_logic import processar_ataque_fisico, processar_ataque_objeto
import random
import math
import uvicorn

app = FastAPI(title="RPG RedNerds Engine API", description="Backend Estruturado para o Godot 4", version="2.5")

# ==========================================================
# MODELOS DE DADOS (Contrato Estrito Godot <-> Python)
# ==========================================================

class LoginRequest(BaseModel):
    codigo_acesso: str

class PlayerState(BaseModel):
    id: str
    nome: str
    classe: str
    nivel: int
    hp_atual: int
    hp_maximo: int
    ca: int
    gold: int
    arma_equipada: str
    dano_dado: str
    status_efeitos: List[str]
    slots_magia: int
    slots_magia_max: int

class EnemyInstance(BaseModel):
    id_instancia: str  # Identificador único para o Godot (ex: "enc12_idx0")
    nome: str
    hp_atual: int
    hp_maximo: int
    ca: int
    imagem_url: Optional[str] = None
    is_boss: bool = False

class SceneState(BaseModel):
    cod_sala: str
    nome_sala: str
    descricao_visual: str
    imagem_url: Optional[str] = None
    conexoes: Dict[str, str]
    inimigos: List[EnemyInstance] = []
    em_combate: bool = False

class CombatResultData(BaseModel):
    acertou: bool
    critico: bool
    dano_causado: int = 0
    dados_rolados: str = ""
    total_ataque: int = 0
    ca_alvo: int = 0
    inimigo_morto: bool = False
    id_alvo: str = ""
    # Revide
    revide_acertos: int = 0
    revide_dano_total: int = 0
    status_aplicados_jogador: List[str] = []

class ActionRequest(BaseModel):
    intencao: str
    direcao: Optional[str] = None
    target_id: Optional[str] = None # Agora usa o ID da instância (ex: "enc12_idx0")
    acao_texto: Optional[str] = None

class ActionResponse(BaseModel):
    sucesso: bool
    mensagem: str
    jogador: PlayerState
    cena: SceneState
    combate: Optional[CombatResultData] = None
    vitoria: bool = False
    loot: List[str] = []
    nivel_subiu: bool = False

# ==========================================================
# FUNÇÕES AUXILIARES
# ==========================================================

def build_player_state(jogador: Jogador) -> PlayerState:
    return PlayerState(
        id=jogador.telefone, nome=jogador.nome, classe=jogador.classe, nivel=jogador.nivel,
        hp_atual=jogador.hp_atual, hp_maximo=jogador.hp_maximo, ca=jogador.modificador_defesa,
        gold=jogador.gold, arma_equipada=jogador.arma_equipada, dano_dado=jogador.dano_dado,
        status_efeitos=jogador.status_efeitos or [], slots_magia=jogador.slots_magia,
        slots_magia_max=jogador.slots_magia_max
    )

def build_scene_state(campanha: Campanha, db) -> SceneState:
    sala = db.query(Cena).filter(Cena.cod_sala == campanha.cena_atual).first()
    if not sala: raise HTTPException(status_code=404, detail="Sala não encontrada.")

    estado_campanha = campanha.estado_salas or {}
    enemies = []

    # CORREÇÃO DO GODOT: Instanciar inimigos individualmente em vez de Pool de HP
    encontros = db.query(Encontro).filter(Encontro.cod_sala == sala.cod_sala).all()
    for enc in encontros:
        if not estado_campanha.get(f"derrotado_{enc.id}"):
            inimigo_model = db.query(Inimigo).filter(Inimigo.nome == enc.nome_inimigo).first()
            if inimigo_model:
                for i in range(enc.quantidade):
                    id_instancia = f"enc{enc.id}_idx{i}"
                    # Inicializa o HP individual no estado da campanha se não existir
                    if id_instancia not in estado_campanha:
                        estado_campanha[id_instancia] = inimigo_model.hp_max
                    
                    enemies.append(EnemyInstance(
                        id_instancia=id_instancia,
                        nome=inimigo_model.nome,
                        hp_atual=estado_campanha[id_instancia],
                        hp_maximo=inimigo_model.hp_max,
                        ca=inimigo_model.ca,
                        imagem_url=inimigo_model.imagem_url,
                        is_boss=inimigo_model.is_boss
                    ))
    
    # Salva possíveis inicializações no banco
    campanha.estado_salas = estado_campanha

    return SceneState(
        cod_sala=sala.cod_sala, nome_sala=sala.nome_sala, descricao_visual=sala.descricao_visual,
        imagem_url=sala.imagem_url, conexoes=sala.conexoes or {}, inimigos=enemies,
        em_combate=campanha.em_combate
    )

# ==========================================================
# ROTAS
# ==========================================================

@app.get("/")
def ler_status_servidor():
    return {"status": "online", "mensagem": "Engine Godot-FastAPI operacional."}

@app.post("/api/login", response_model=ActionResponse)
def login_godot(req: LoginRequest):
    with get_db_session() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == req.codigo_acesso).first()
        if not jogador: raise HTTPException(status_code=404, detail="Aventureiro não encontrado.")
        campanha = db.query(Campanha).filter(Campanha.party_id == jogador.party_id).first()
        if not campanha: raise HTTPException(status_code=404, detail="O jogador não está numa Party.")

        player_state = build_player_state(jogador)
        scene_state = build_scene_state(campanha, db)

        return ActionResponse(
            sucesso=True, mensagem=f"Bem-vindo, {jogador.nome}.", jogador=player_state, cena=scene_state
        )

@app.get("/api/scene/{telegram_id}", response_model=SceneState)
def get_current_scene(telegram_id: str):
    with get_db_session() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == telegram_id).first()
        if not jogador: raise HTTPException(404, "Jogador não encontrado")
        campanha = db.query(Campanha).filter(Campanha.party_id == jogador.party_id).first()
        if not campanha: raise HTTPException(404, "Campanha não encontrada")
        return build_scene_state(campanha, db)

@app.post("/api/action/{telegram_id}", response_model=ActionResponse)
def execute_action(telegram_id: str, req: ActionRequest):
    with get_db_session() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == telegram_id).first()
        if not jogador: raise HTTPException(404, "Jogador não encontrado")
        campanha = db.query(Campanha).filter(Campanha.party_id == jogador.party_id).first()
        if not campanha: raise HTTPException(404, "Campanha não encontrada")

        estado_campanha = dict(campanha.estado_salas or {})
        sala_atual = db.query(Cena).filter(Cena.cod_sala == campanha.cena_atual).first()
        
        mensagem = ""
        combate_data = None
        vitoria = False
        loot = []
        nivel_subiu = False

        # =========================================================================
        # 1. NAVEGAÇÃO
        # =========================================================================
        if req.intencao == "NAVEGAR" and req.direcao:
            encontros = db.query(Encontro).filter(Encontro.cod_sala == campanha.cena_atual).all()
            encontros_vivos = [e for e in encontros if not estado_campanha.get(f"derrotado_{e.id}")]
            
            if encontros_vivos:
                mensagem = "Caminho bloqueado! Inimigos na sala."
            else:
                direcao = req.direcao.lower()
                conexoes = sala_atual.conexoes or {}
                if direcao in conexoes and conexoes[direcao]:
                    campanha.cena_anterior = campanha.cena_atual
                    campanha.cena_atual = conexoes[direcao]
                    # Sincroniza Party
                    for m in db.query(Jogador).filter(Jogador.party_id == campanha.party_id).all():
                        m.cena_atual = campanha.cena_atual
                    mensagem = f"Moveu-se para {direcao}."
                else:
                    mensagem = "Direção inválida."

        # =========================================================================
        # 2. COMBATE (A Grande Refatoração para o Godot)
        # =========================================================================
        elif req.intencao == "COMBATE" and req.target_id:
            target_id = req.target_id # Ex: "enc12_idx0"
            
            if target_id not in estado_campanha or estado_campanha[target_id] <= 0:
                raise HTTPException(400, "Alvo já está morto ou não existe.")

            # Descobre o modelo do inimigo baseado no ID da instância
            enc_id = int(target_id.split('_')[0].replace('enc', ''))
            encontro = db.query(Encontro).filter(Encontro.id == enc_id).first()
            inimigo = db.query(Inimigo).filter(Inimigo.nome == encontro.nome_inimigo).first()
            
            if not inimigo: raise HTTPException(404, "Estatísticas do monstro não encontradas")

            # Lógica de Boss (Ex: Durnn)
            ca_alvo = inimigo.ca
            is_durnn_furia = False
            if getattr(inimigo, 'is_boss', False) and estado_campanha[target_id] <= (inimigo.hp_max / 2):
                is_durnn_furia = True
                ca_alvo = max(10, ca_alvo - 2)

            # --- ATAQUE DO JOGADOR ---
            res = processar_ataque_fisico(jogador, ca_alvo)
            dano_causado = res.dano if res.acertou else 0
            inimigo_morto = False

            if res.acertou:
                estado_campanha[target_id] -= dano_causado
                if estado_campanha[target_id] <= 0:
                    estado_campanha[target_id] = 0
                    inimigo_morto = True
                    loot.append(f"{inimigo.ouro_recompensa or 5} PO")

            # Verifica Vitória Total (Todos os inimigos da sala morreram?)
            encontros = db.query(Encontro).filter(Encontro.cod_sala == campanha.cena_atual).all()
            todos_mortos = True
            for enc_check in encontros:
                for i in range(enc_check.quantidade):
                    id_check = f"enc{enc_check.id}_idx{i}"
                    if estado_campanha.get(id_check, 1) > 0:
                        todos_mortos = False
                        break
                if not todos_mortos: break

            if todos_mortos:
                vitoria = True
                campanha.em_combate = False
                for enc_v in encontros: estado_campanha[f"derrotado_{enc_v.id}"] = True
                jogador.xp += (inimigo.xp_recompensa or 50)
                mensagem = f"Vitória! Derrotaste todos os inimigos."

                # Level Up Check Simples
                from ui_utils import XP_POR_NIVEL, HP_POR_CLASSE
                if jogador.xp >= XP_POR_NIVEL.get(jogador.nivel + 1, 999999):
                    jogador.nivel += 1
                    jogador.hp_maximo += HP_POR_CLASSE.get(jogador.classe, 8) + jogador.mod_con
                    jogador.hp_atual = jogador.hp_maximo
                    nivel_subiu = True
                    mensagem += f" Subiste para o Nível {jogador.nivel}!"
            
            # --- REVIDE DO INIMIGO (Se o alvo sobreviveu) ---
            revide_acertos = 0
            revide_dano_total = 0
            status_aplicados = []

            if not inimigo_morto and not vitoria:
                # O inimigo atacado revida
                mod_inimigo = int(str(inimigo.ataque).replace('+', '')) if '+' in str(inimigo.ataque) else 0
                d20_inimigo = random.randint(1, 20)
                
                if d20_inimigo + mod_inimigo >= jogador.modificador_defesa or d20_inimigo == 20:
                    revide_acertos = 1
                    dano_base = random.randint(1, 4)
                    if is_durnn_furia: dano_base += 2
                    if d20_inimigo == 20: dano_base *= 2
                    revide_dano_total = dano_base
                
                jogador.hp_atual -= revide_dano_total

                # Veneno (20% chance)
                efeitos_jogador = list(jogador.status_efeitos or [])
                if revide_acertos > 0 and random.randint(1, 100) <= 20 and "Envenenado" not in efeitos_jogador:
                    efeitos_jogador.append("Envenenado")
                    status_aplicados.append("Envenenado")
                    dano_veneno = random.randint(1, 4)
                    jogador.hp_atual -= dano_veneno
                
                jogador.status_efeitos = efeitos_jogador
                mensagem = f"Atacaste {inimigo.nome}. Ele revidou."

            combate_data = CombatResultData(
                acertou=res.acertou, critico=res.critico, dano_causado=dano_causado,
                dados_rolados=res.detalhes_d20, total_ataque=res.total_ataque, ca_alvo=ca_alvo,
                inimigo_morto=inimigo_morto, id_alvo=target_id,
                revide_acertos=revide_acertos, revide_dano_total=revide_dano_total,
                status_aplicados_jogador=status_aplicados
            )

        # Salva Estado
        campanha.estado_salas = estado_campanha
        db.commit()
        db.refresh(jogador)

        player_state = build_player_state(jogador)
        scene_state = build_scene_state(campanha, db)

        return ActionResponse(
            sucesso=True, mensagem=mensagem, jogador=player_state, cena=scene_state,
            combate=combate_data, vitoria=vitoria, loot=loot, nivel_subiu=nivel_subiu
        )

if __name__ == "__main__":
    print("🚀 A iniciar a API do Godot na porta 8000...")
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from database import get_db_session
from models import Jogador, Campanha, Cena, Encontro, Inimigo, Interativo, ObjetoDestrutivel, Npc
from combat_logic import processar_ataque_fisico, processar_ataque_objeto
import random
import math
import uvicorn

app = FastAPI(title="RPG RedNerds Engine API", description="Backend Estruturado para o Godot 4", version="2.5")

# ==========================================================
# MODELOS DE DADOS (Contrato Estrito Godot <-> Python)
# ==========================================================

class LoginRequest(BaseModel):
    codigo_acesso: str

class PlayerState(BaseModel):
    id: str
    nome: str
    classe: str
    nivel: int
    hp_atual: int
    hp_maximo: int
    ca: int
    gold: int
    arma_equipada: str
    dano_dado: str
    status_efeitos: List[str]
    slots_magia: int
    slots_magia_max: int

class EnemyInstance(BaseModel):
    id_instancia: str  # Identificador único para o Godot (ex: "enc12_idx0")
    nome: str
    hp_atual: int
    hp_maximo: int
    ca: int
    imagem_url: Optional[str] = None
    is_boss: bool = False

class SceneState(BaseModel):
    cod_sala: str
    nome_sala: str
    descricao_visual: str
    imagem_url: Optional[str] = None
    conexoes: Dict[str, str]
    inimigos: List[EnemyInstance] = []
    em_combate: bool = False

class CombatResultData(BaseModel):
    acertou: bool
    critico: bool
    dano_causado: int = 0
    dados_rolados: str = ""
    total_ataque: int = 0
    ca_alvo: int = 0
    inimigo_morto: bool = False
    id_alvo: str = ""
    # Revide
    revide_acertos: int = 0
    revide_dano_total: int = 0
    status_aplicados_jogador: List[str] = []

class ActionRequest(BaseModel):
    intencao: str
    direcao: Optional[str] = None
    target_id: Optional[str] = None # Agora usa o ID da instância (ex: "enc12_idx0")
    acao_texto: Optional[str] = None

class ActionResponse(BaseModel):
    sucesso: bool
    mensagem: str
    jogador: PlayerState
    cena: SceneState
    combate: Optional[CombatResultData] = None
    vitoria: bool = False
    loot: List[str] = []
    nivel_subiu: bool = False

# ==========================================================
# FUNÇÕES AUXILIARES
# ==========================================================

def build_player_state(jogador: Jogador) -> PlayerState:
    return PlayerState(
        id=jogador.telefone, nome=jogador.nome, classe=jogador.classe, nivel=jogador.nivel,
        hp_atual=jogador.hp_atual, hp_maximo=jogador.hp_maximo, ca=jogador.modificador_defesa,
        gold=jogador.gold, arma_equipada=jogador.arma_equipada, dano_dado=jogador.dano_dado,
        status_efeitos=jogador.status_efeitos or [], slots_magia=jogador.slots_magia,
        slots_magia_max=jogador.slots_magia_max
    )

def build_scene_state(campanha: Campanha, db) -> SceneState:
    sala = db.query(Cena).filter(Cena.cod_sala == campanha.cena_atual).first()
    if not sala: raise HTTPException(status_code=404, detail="Sala não encontrada.")

    estado_campanha = campanha.estado_salas or {}
    enemies = []

    # CORREÇÃO DO GODOT: Instanciar inimigos individualmente em vez de Pool de HP
    encontros = db.query(Encontro).filter(Encontro.cod_sala == sala.cod_sala).all()
    for enc in encontros:
        if not estado_campanha.get(f"derrotado_{enc.id}"):
            inimigo_model = db.query(Inimigo).filter(Inimigo.nome == enc.nome_inimigo).first()
            if inimigo_model:
                for i in range(enc.quantidade):
                    id_instancia = f"enc{enc.id}_idx{i}"
                    # Inicializa o HP individual no estado da campanha se não existir
                    if id_instancia not in estado_campanha:
                        estado_campanha[id_instancia] = inimigo_model.hp_max
                    
                    enemies.append(EnemyInstance(
                        id_instancia=id_instancia,
                        nome=inimigo_model.nome,
                        hp_atual=estado_campanha[id_instancia],
                        hp_maximo=inimigo_model.hp_max,
                        ca=inimigo_model.ca,
                        imagem_url=inimigo_model.imagem_url,
                        is_boss=inimigo_model.is_boss
                    ))
    
    # Salva possíveis inicializações no banco
    campanha.estado_salas = estado_campanha

    return SceneState(
        cod_sala=sala.cod_sala, nome_sala=sala.nome_sala, descricao_visual=sala.descricao_visual,
        imagem_url=sala.imagem_url, conexoes=sala.conexoes or {}, inimigos=enemies,
        em_combate=campanha.em_combate
    )

# ==========================================================
# ROTAS
# ==========================================================

@app.get("/")
def ler_status_servidor():
    return {"status": "online", "mensagem": "Engine Godot-FastAPI operacional."}

@app.post("/api/login", response_model=ActionResponse)
def login_godot(req: LoginRequest):
    with get_db_session() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == req.codigo_acesso).first()
        if not jogador: raise HTTPException(status_code=404, detail="Aventureiro não encontrado.")
        campanha = db.query(Campanha).filter(Campanha.party_id == jogador.party_id).first()
        if not campanha: raise HTTPException(status_code=404, detail="O jogador não está numa Party.")

        player_state = build_player_state(jogador)
        scene_state = build_scene_state(campanha, db)

        return ActionResponse(
            sucesso=True, mensagem=f"Bem-vindo, {jogador.nome}.", jogador=player_state, cena=scene_state
        )

@app.get("/api/scene/{telegram_id}", response_model=SceneState)
def get_current_scene(telegram_id: str):
    with get_db_session() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == telegram_id).first()
        if not jogador: raise HTTPException(404, "Jogador não encontrado")
        campanha = db.query(Campanha).filter(Campanha.party_id == jogador.party_id).first()
        if not campanha: raise HTTPException(404, "Campanha não encontrada")
        return build_scene_state(campanha, db)

@app.post("/api/action/{telegram_id}", response_model=ActionResponse)
def execute_action(telegram_id: str, req: ActionRequest):
    with get_db_session() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == telegram_id).first()
        if not jogador: raise HTTPException(404, "Jogador não encontrado")
        campanha = db.query(Campanha).filter(Campanha.party_id == jogador.party_id).first()
        if not campanha: raise HTTPException(404, "Campanha não encontrada")

        estado_campanha = dict(campanha.estado_salas or {})
        sala_atual = db.query(Cena).filter(Cena.cod_sala == campanha.cena_atual).first()
        
        mensagem = ""
        combate_data = None
        vitoria = False
        loot = []
        nivel_subiu = False

        # =========================================================================
        # 1. NAVEGAÇÃO
        # =========================================================================
        if req.intencao == "NAVEGAR" and req.direcao:
            encontros = db.query(Encontro).filter(Encontro.cod_sala == campanha.cena_atual).all()
            encontros_vivos = [e for e in encontros if not estado_campanha.get(f"derrotado_{e.id}")]
            
            if encontros_vivos:
                mensagem = "Caminho bloqueado! Inimigos na sala."
            else:
                direcao = req.direcao.lower()
                conexoes = sala_atual.conexoes or {}
                if direcao in conexoes and conexoes[direcao]:
                    campanha.cena_anterior = campanha.cena_atual
                    campanha.cena_atual = conexoes[direcao]
                    # Sincroniza Party
                    for m in db.query(Jogador).filter(Jogador.party_id == campanha.party_id).all():
                        m.cena_atual = campanha.cena_atual
                    mensagem = f"Moveu-se para {direcao}."
                else:
                    mensagem = "Direção inválida."

        # =========================================================================
        # 2. COMBATE (A Grande Refatoração para o Godot)
        # =========================================================================
        elif req.intencao == "COMBATE" and req.target_id:
            target_id = req.target_id # Ex: "enc12_idx0"
            
            if target_id not in estado_campanha or estado_campanha[target_id] <= 0:
                raise HTTPException(400, "Alvo já está morto ou não existe.")

            # Descobre o modelo do inimigo baseado no ID da instância
            enc_id = int(target_id.split('_')[0].replace('enc', ''))
            encontro = db.query(Encontro).filter(Encontro.id == enc_id).first()
            inimigo = db.query(Inimigo).filter(Inimigo.nome == encontro.nome_inimigo).first()
            
            if not inimigo: raise HTTPException(404, "Estatísticas do monstro não encontradas")

            # Lógica de Boss (Ex: Durnn)
            ca_alvo = inimigo.ca
            is_durnn_furia = False
            if getattr(inimigo, 'is_boss', False) and estado_campanha[target_id] <= (inimigo.hp_max / 2):
                is_durnn_furia = True
                ca_alvo = max(10, ca_alvo - 2)

            # --- ATAQUE DO JOGADOR ---
            res = processar_ataque_fisico(jogador, ca_alvo)
            dano_causado = res.dano if res.acertou else 0
            inimigo_morto = False

            if res.acertou:
                estado_campanha[target_id] -= dano_causado
                if estado_campanha[target_id] <= 0:
                    estado_campanha[target_id] = 0
                    inimigo_morto = True
                    loot.append(f"{inimigo.ouro_recompensa or 5} PO")

            # Verifica Vitória Total (Todos os inimigos da sala morreram?)
            encontros = db.query(Encontro).filter(Encontro.cod_sala == campanha.cena_atual).all()
            todos_mortos = True
            for enc_check in encontros:
                for i in range(enc_check.quantidade):
                    id_check = f"enc{enc_check.id}_idx{i}"
                    if estado_campanha.get(id_check, 1) > 0:
                        todos_mortos = False
                        break
                if not todos_mortos: break

            if todos_mortos:
                vitoria = True
                campanha.em_combate = False
                for enc_v in encontros: estado_campanha[f"derrotado_{enc_v.id}"] = True
                jogador.xp += (inimigo.xp_recompensa or 50)
                mensagem = f"Vitória! Derrotaste todos os inimigos."

                # Level Up Check Simples
                from ui_utils import XP_POR_NIVEL, HP_POR_CLASSE
                if jogador.xp >= XP_POR_NIVEL.get(jogador.nivel + 1, 999999):
                    jogador.nivel += 1
                    jogador.hp_maximo += HP_POR_CLASSE.get(jogador.classe, 8) + jogador.mod_con
                    jogador.hp_atual = jogador.hp_maximo
                    nivel_subiu = True
                    mensagem += f" Subiste para o Nível {jogador.nivel}!"
            
            # --- REVIDE DO INIMIGO (Se o alvo sobreviveu) ---
            revide_acertos = 0
            revide_dano_total = 0
            status_aplicados = []

            if not inimigo_morto and not vitoria:
                # O inimigo atacado revida
                mod_inimigo = int(str(inimigo.ataque).replace('+', '')) if '+' in str(inimigo.ataque) else 0
                d20_inimigo = random.randint(1, 20)
                
                if d20_inimigo + mod_inimigo >= jogador.modificador_defesa or d20_inimigo == 20:
                    revide_acertos = 1
                    dano_base = random.randint(1, 4)
                    if is_durnn_furia: dano_base += 2
                    if d20_inimigo == 20: dano_base *= 2
                    revide_dano_total = dano_base
                
                jogador.hp_atual -= revide_dano_total

                # Veneno (20% chance)
                efeitos_jogador = list(jogador.status_efeitos or [])
                if revide_acertos > 0 and random.randint(1, 100) <= 20 and "Envenenado" not in efeitos_jogador:
                    efeitos_jogador.append("Envenenado")
                    status_aplicados.append("Envenenado")
                    dano_veneno = random.randint(1, 4)
                    jogador.hp_atual -= dano_veneno
                
                jogador.status_efeitos = efeitos_jogador
                mensagem = f"Atacaste {inimigo.nome}. Ele revidou."

            combate_data = CombatResultData(
                acertou=res.acertou, critico=res.critico, dano_causado=dano_causado,
                dados_rolados=res.detalhes_d20, total_ataque=res.total_ataque, ca_alvo=ca_alvo,
                inimigo_morto=inimigo_morto, id_alvo=target_id,
                revide_acertos=revide_acertos, revide_dano_total=revide_dano_total,
                status_aplicados_jogador=status_aplicados
            )

        # Salva Estado
        campanha.estado_salas = estado_campanha
        db.commit()
        db.refresh(jogador)

        player_state = build_player_state(jogador)
        scene_state = build_scene_state(campanha, db)

        return ActionResponse(
            sucesso=True, mensagem=mensagem, jogador=player_state, cena=scene_state,
            combate=combate_data, vitoria=vitoria, loot=loot, nivel_subiu=nivel_subiu
        )

if __name__ == "__main__":
    print("🚀 A iniciar a API do Godot na porta 8000...")
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)