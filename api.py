from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from database import get_db_session
from models import Jogador, Campanha, Cena, Encontro, Inimigo, Interativo, ObjetoDestrutivel, Npc
from combat_logic import processar_ataque_fisico, processar_ataque_objeto
import random
import math
import uvicorn

# Inicializa a nossa API
app = FastAPI(title="RPG RedNerds Engine API", description="Backend Estruturado para o Godot 4", version="2.0")

# ==========================================================
# MODELOS DE DADOS (Contrato entre Python e Godot)
# ==========================================================

class LoginRequest(BaseModel):
    codigo_acesso: str  # Telegram ID

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

class EnemyState(BaseModel):
    id_encontro: int
    nome: str
    hp_atual: int
    hp_maximo: int
    imagem_url: Optional[str] = None
    is_boss: bool = False

class NpcState(BaseModel):
    id: int
    nome: str

class ObjectState(BaseModel):
    id: int
    nome: str
    hp_atual: int
    hp_maximo: int
    ativo: bool

class SceneState(BaseModel):
    cod_sala: str
    nome_sala: str
    descricao_visual: str
    imagem_url: Optional[str] = None
    conexoes: Dict[str, str]  # Ex: {"norte": "sala_2", "sul": "sala_3"}
    inimigos: List[EnemyState] = []
    npcs: List[NpcState] = []
    objetos: List[ObjectState] = []
    em_combate: bool = False

class CombatResultData(BaseModel):
    acertou: bool
    critico: bool
    dano_causado: int = 0
    dados_rolados: str = ""
    total_ataque: int = 0
    ca_alvo: int = 0
    inimigos_mortos_ataque: int = 0
    # Dados do revide inimigo
    revide_acertos: int = 0
    revide_dano_total: int = 0
    status_aplicados_jogador: List[str] = []

class ActionRequest(BaseModel):
    intencao: str  # "NAVEGAR", "COMBATE", "ATACAR_OBJETO", "USAR_ITEM", "INTERAGIR"
    direcao: Optional[str] = None
    target_id: Optional[int] = None # ID do Encontro ou Objeto
    acao_texto: Optional[str] = None # Para a IA ou contexto, se necessário no futuro

class ActionResponse(BaseModel):
    sucesso: bool
    mensagem: str # Texto limpo para o log de combate do Godot
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
        id=jogador.telefone,
        nome=jogador.nome,
        classe=jogador.classe,
        nivel=jogador.nivel,
        hp_atual=jogador.hp_atual,
        hp_maximo=jogador.hp_maximo,
        ca=jogador.modificador_defesa,
        gold=jogador.gold,
        arma_equipada=jogador.arma_equipada,
        dano_dado=jogador.dano_dado,
        status_efeitos=jogador.status_efeitos or []
    )

def build_scene_state(campanha: Campanha, db) -> SceneState:
    sala = db.query(Cena).filter(Cena.cod_sala == campanha.cena_atual).first()
    if not sala:
        raise HTTPException(status_code=404, detail="Sala atual não encontrada no banco.")

    estado_campanha = campanha.estado_salas or {}

    # Mapear Inimigos
    encontros = db.query(Encontro).filter(Encontro.cod_sala == sala.cod_sala).all()
    enemies = []
    for enc in encontros:
        if not estado_campanha.get(f"derrotado_{enc.id}"):
            inimigo_model = db.query(Inimigo).filter(Inimigo.nome == enc.nome_inimigo).first()
            if inimigo_model:
                hp_key = f"hp_{enc.id}"
                hp_max_grupo = inimigo_model.hp_max * enc.quantidade
                hp_atual_grupo = estado_campanha.get(hp_key, hp_max_grupo)
                enemies.append(EnemyState(
                    id_encontro=enc.id,
                    nome=enc.nome_inimigo,
                    hp_atual=hp_atual_grupo,
                    hp_maximo=hp_max_grupo,
                    imagem_url=inimigo_model.imagem_url,
                    is_boss=inimigo_model.is_boss
                ))

    # Mapear NPCs
    npcs = db.query(Npc).filter(Npc.cod_sala == sala.cod_sala).all()
    npcs_state = [NpcState(id=n.id, nome=n.nome) for n in npcs]

    # Mapear Objetos Destrutíveis e Interativos
    objetos = db.query(ObjetoDestrutivel).filter(
        ObjetoDestrutivel.cod_sala == sala.cod_sala, 
        ObjetoDestrutivel.ativo == True
    ).all()
    objs_state = [ObjectState(id=o.id, nome=o.nome, hp_atual=o.hp_atual, hp_maximo=o.hp_max, ativo=o.ativo) for o in objetos]

    return SceneState(
        cod_sala=sala.cod_sala,
        nome_sala=sala.nome_sala,
        descricao_visual=sala.descricao_visual,
        imagem_url=sala.imagem_url,
        conexoes=sala.conexoes or {},
        inimigos=enemies,
        npcs=npcs_state,
        objetos=objs_state,
        em_combate=campanha.em_combate
    )

# ==========================================================
# ROTAS (Endpoints)
# ==========================================================

@app.get("/")
def ler_status_servidor():
    return {"status": "online", "mensagem": "A Taverna está aberta! Engine Godot-FastAPI operacional."}

@app.post("/api/login", response_model=ActionResponse)
def login_godot(req: LoginRequest):
    """O Godot envia o ID, o Python devolve o estado completo inicial."""
    with get_db_session() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == req.codigo_acesso).first()
        if not jogador:
            raise HTTPException(status_code=404, detail="Aventureiro não encontrado.")
        
        campanha = db.query(Campanha).filter(Campanha.party_id == jogador.party_id).first()
        if not campanha:
            raise HTTPException(status_code=404, detail="O jogador não está numa Party.")

        player_state = build_player_state(jogador)
        scene_state = build_scene_state(campanha, db)

        return ActionResponse(
            sucesso=True,
            mensagem=f"Bem-vindo de volta, {jogador.nome}.",
            jogador=player_state,
            cena=scene_state
        )

@app.get("/api/scene/{telegram_id}", response_model=SceneState)
def get_current_scene(telegram_id: str):
    """Rota para o Godot fazer Polling ou atualizar a cena após uma ação de outro jogador."""
    with get_db_session() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == telegram_id).first()
        if not jogador: raise HTTPException(404, "Jogador não encontrado")
        campanha = db.query(Campanha).filter(Campanha.party_id == jogador.party_id).first()
        if not campanha: raise HTTPException(404, "Campanha não encontrada")
        
        return build_scene_state(campanha, db)

@app.post("/api/action/{telegram_id}", response_model=ActionResponse)
def execute_action(telegram_id: str, req: ActionRequest):
    """O coração da comunicação Godot->Python. Executa uma ação e devolve o estado novo."""
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
            # Verifica se está em combate (não pode sair)
            encontros = db.query(Encontro).filter(Encontro.cod_sala == campanha.cena_atual).all()
            encontros_vivos = [e for e in encontros if not estado_campanha.get(f"derrotado_{e.id}")]
            
            if encontros_vivos:
                mensagem = "Caminho bloqueado! Existem inimigos na sala."
                # No Godot, isto impede a transição de cena e mostra um ícone de bloqueio
            else:
                direcao = req.direcao.lower()
                conexoes = sala_atual.conexoes or {}
                if direcao in conexoes and conexoes[direcao]:
                    campanha.cena_anterior = campanha.cena_atual
                    campanha.cena_atual = conexoes[direcao]
                    mensagem = f"Moveu-se para {direcao}."
                    # O Godot vai chamar /api/scene/ logo de seguida para carregar o novo mapa
                else:
                    mensagem = "Direção inválida ou bloqueada."

        # =========================================================================
        # 2. COMBATE FÍSICO (Contra Inimigos)
        # =========================================================================
        elif req.intencao == "COMBATE" and req.target_id:
            encontro = db.query(Encontro).filter(Encontro.id == req.target_id).first()
            if not encontro:
                raise HTTPException(404, "Alvo não encontrado")
            
            inimigo = db.query(Inimigo).filter(Inimigo.nome == encontro.nome_inimigo).first()
            if not inimigo:
                raise HTTPException(404, "Estatísticas do monstro não encontradas")

            chave_hp = f"hp_{encontro.id}"
            hp_max_inimigo = inimigo.hp_max * encontro.quantidade
            hp_grupo = estado_campanha.get(chave_hp, hp_max_inimigo)
            ca_alvo = inimigo.ca

            # Lógica de Boss (Ex: Durnn)
            if getattr(inimigo, 'is_boss', False) and hp_grupo <= (hp_max_inimigo / 2) and hp_grupo > 0:
                ca_alvo = max(10, ca_alvo - 2) # Boss enfurecido fica mais fácil de acertar

            # --- ATAQUE DO JOGADOR ---
            res = processar_ataque_fisico(jogador, ca_alvo)
            dano_causado = res.dano if res.acertou else 0
            mortos_ataque = 0

            if res.acertou:
                vivos_antes = math.ceil(hp_grupo / inimigo.hp_max) if hp_grupo > 0 else 0
                hp_grupo -= dano_causado
                vivos_depois = math.ceil(hp_grupo / inimigo.hp_max) if hp_grupo > 0 else 0
                mortos_ataque = max(0, vivos_antes - vivos_depois)
                estado_campanha[chave_hp] = hp_grupo

            # Verifica Vitória
            if hp_grupo <= 0:
                vitoria = True
                estado_campanha[f"derrotado_{encontro.id}"] = True
                campanha.em_combate = False
                
                # Distribuir XP e Ouro (Lógica simplificada do exploracao.py)
                xp_total = (inimigo.xp_recompensa or 50) * encontro.quantidade
                ouro_total = (inimigo.ouro_recompensa or 5) * encontro.quantidade
                jogador.xp += xp_total
                jogador.gold += ouro_total
                loot.append(f"{ouro_total} PO")
                loot.append(f"{xp_total} XP")

                # Level Up Check
                from ui_utils import XP_POR_NIVEL, HP_POR_CLASSE
                if jogador.xp >= XP_POR_NIVEL.get(jogador.nivel + 1, 999999):
                    jogador.nivel += 1
                    jogador.hp_maximo += HP_POR_CLASSE.get(jogador.classe, 8) + jogador.mod_con
                    jogador.hp_atual = jogador.hp_maximo
                    nivel_subiu = True
                    mensagem = f"Subiste para o Nível {jogador.nivel}! "

                mensagem += f"Vitória! Derrotaste {encontro.nome_inimigo}."
                
                combate_data = CombatResultData(
                    acertou=res.acertou, critico=res.critico, dano_causado=dano_causado,
                    dados_rolados=res.detalhes_d20, total_ataque=res.total_ataque, ca_alvo=ca_alvo,
                    inimigos_mortos_ataque=mortos_ataque, revide_acertos=0, revide_dano_total=0
                )
            else:
                # --- REVIDE DO INIMIGO (Se não morreu) ---
                mod_inimigo = int(str(inimigo.ataque).replace('+', '')) if '+' in str(inimigo.ataque) else 0
                vivos_agora = math.ceil(hp_grupo / inimigo.hp_max) if hp_grupo > 0 else 0
                atacantes = min(vivos_agora, 2) # Limite de ataques por turno
                acertos_inimigo = 0
                dano_revide_total = 0
                status_aplicados = []

                for _ in range(atacantes):
                    d20_inimigo = random.randint(1, 20)
                    if d20_inimigo + mod_inimigo >= jogador.modificador_defesa or d20_inimigo == 20:
                        acertos_inimigo += 1
                        dano_base = random.randint(1, 4) # Dano genérico do revide
                        if d20_inimigo == 20: dano_base *= 2
                        dano_revide_total += dano_base
                
                jogador.hp_atual -= dano_revide_total

                # Veneno (20% chance)
                efeitos_jogador = list(jogador.status_efeitos or [])
                if acertos_inimigo > 0 and random.randint(1, 100) <= 20 and "Envenenado" not in efeitos_jogador:
                    if any(n in inimigo.nome.lower() for n in ["rato", "aranha", "goblin"]):
                        efeitos_jogador.append("Envenenado")
                        status_aplicados.append("Envenenado")
                        jogador.hp_atual -= random.randint(1, 4)
                
                jogador.status_efeitos = efeitos_jogador

                combate_data = CombatResultData(
                    acertou=res.acertou, critico=res.critico, dano_causado=dano_causado,
                    dados_rolados=res.detalhes_d20, total_ataque=res.total_ataque, ca_alvo=ca_alvo,
                    inimigos_mortos_ataque=mortos_ataque,
                    revide_acertos=acertos_inimigo, revide_dano_total=dano_revide_total,
                    status_aplicados_jogador=status_aplicados
                )
                mensagem = f"Atacaste {encontro.nome_inimigo}. O inimigo revidou {acertos_inimigo} vezes."

        # =========================================================================
        # 3. ATAQUE A OBJETOS (Barrís, Portas, Cadeados)
        # =========================================================================
        elif req.intencao == "ATACAR_OBJETO" and req.target_id:
            obj = db.query(ObjetoDestrutivel).filter(ObjetoDestrutivel.id == req.target_id, ObjetoDestrutivel.ativo == True).first()
            if not obj: raise HTTPException(404, "Objeto não encontrado ou já destruído")

            res_obj = processar_ataque_objeto(jogador, obj)
            
            if res_obj.acertou or res_obj.quebrou_por_forca:
                obj.hp_atual = res_obj.hp_restante
                if res_obj.destruido:
                    obj.ativo = False
                    mensagem = f"Destruíste {obj.nome}!"
                    # Lógica de Loot de objeto (se existir)
                    if obj.recompensa_ao_destruir:
                        from ui_utils import adicionar_ao_inventario
                        itens_reais = adicionar_ao_inventario(jogador, obj.recompensa_ao_destruir)
                        loot.extend(itens_reais)
                else:
                    mensagem = f"Acertaste {obj.nome}. HP restante: {obj.hp_atual}/{obj.hp_max}"
            else:
                mensagem = f"Falhaste o ataque a {obj.nome}."

            combate_data = CombatResultData(
                acertou=res_obj.acertou, critico=res_obj.critico, dano_causado=res_obj.dano,
                dados_rolados=res_obj.detalhes_d20, total_ataque=res_obj.total_ataque, ca_alvo=obj.ca,
                inimigos_mortos_ataque=0, revide_acertos=0, revide_dano_total=0
            )

        # Salva as alterações no Banco de Dados
        campanha.estado_salas = estado_campanha
        db.commit()
        db.refresh(jogador) # Garante que o Godot recebe os dados atualizados do BD

        # Constrói a resposta final
        player_state = build_player_state(jogador)
        scene_state = build_scene_state(campanha, db)

        return ActionResponse(
            sucesso=True,
            mensagem=mensagem,
            jogador=player_state,
            cena=scene_state,
            combate=combate_data,
            vitoria=vitoria,
            loot=loot,
            nivel_subiu=nivel_subiu
        )

if __name__ == "__main__":
    print("🚀 A iniciar a API do Godot na porta 8000...")
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)