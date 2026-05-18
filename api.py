import hashlib # ADICIONADO: Para hashes determinísticos
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from database import get_async_db
from models import Jogador, Campanha, Cena, Encontro, Inimigo, Interativo, ObjetoDestrutivel, Npc
from combat_logic import processar_ataque_fisico, processar_ataque_objeto
import random
import math
import uvicorn

app = FastAPI(title="RPG RedNerds Engine API", description="Backend Estruturado para o Godot 4", version="3.5")

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
    inventario: List[str] = [] # ADICIONADO: Essencial para a UI do Godot

class EnemyInstance(BaseModel):
    id_instancia: str
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
    revide_acertos: int = 0
    revide_dano_total: int = 0
    status_aplicados_jogador: List[str] = []

class ActionRequest(BaseModel):
    intencao: str
    direcao: Optional[str] = None
    target_id: Optional[str] = None
    acao_texto: Optional[str] = None # Usado para USAR_ITEM, EQUIPAR, USAR_HABILIDADE

class ActionResponse(BaseModel):
    sucesso: bool
    mensagem: str
    jogador: PlayerState
    cena: SceneState
    combate: Optional[CombatResultData] = None
    vitoria: bool = False
    loot: List[str] = []
    nivel_subiu: bool = False
    state_hash: str = "" # Alterado para String (MD5)

# ==========================================================
# FUNÇÕES AUXILIARES
# ==========================================================

def build_player_state(jogador: Jogador) -> PlayerState:
    from ui_utils import obter_inventario_limpo
    # Limpamos o inventário (removendo os códigos internos) antes de mandar para o Godot
    inv_limpo = obter_inventario_limpo(jogador.inventario) if jogador.inventario else []
    
    return PlayerState(
        id=jogador.telefone, nome=jogador.nome, classe=jogador.classe, nivel=jogador.nivel,
        hp_atual=jogador.hp_atual, hp_maximo=jogador.hp_maximo, ca=jogador.modificador_defesa,
        gold=jogador.gold, arma_equipada=jogador.arma_equipada, dano_dado=jogador.dano_dado,
        status_efeitos=jogador.status_efeitos or [], slots_magia=jogador.slots_magia,
        slots_magia_max=jogador.slots_magia_max,
        inventario=inv_limpo # ADICIONADO
    )

def build_scene_state(campanha: Campanha, db) -> SceneState:
    sala = db.query(Cena).filter(Cena.cod_sala == campanha.cena_atual).first()
    if not sala: raise HTTPException(status_code=404, detail="Sala não encontrada.")

    estado_campanha = campanha.estado_salas or {}
    enemies = []

    encontros = db.query(Encontro).filter(Encontro.cod_sala == sala.cod_sala).all()
    for enc in encontros:
        if not estado_campanha.get(f"derrotado_{enc.id}"):
            inimigo_model = db.query(Inimigo).filter(Inimigo.nome == enc.nome_inimigo).first()
            if inimigo_model:
                for i in range(enc.quantidade):
                    id_instancia = f"enc{enc.id}_idx{i}"
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
    
    campanha.estado_salas = estado_campanha

    return SceneState(
        cod_sala=sala.cod_sala, nome_sala=sala.nome_sala, descricao_visual=sala.descricao_visual,
        imagem_url=sala.imagem_url, conexoes=sala.conexoes or {}, inimigos=enemies,
        em_combate=campanha.em_combate
    )

def generate_state_hash(jogador: Jogador, campanha: Campanha) -> str:
    """Gera um hash MD5 fixo. Não muda mesmo que o servidor reinicie."""
    state_string = f"{jogador.hp_atual}{jogador.gold}{jogador.xp}{campanha.cena_atual}{campanha.em_combate}"
    return hashlib.md5(state_string.encode('utf-8')).hexdigest()

# ==========================================================
# ROTAS
# ==========================================================

@app.get("/")
def ler_status_servidor():
    return {"status": "online", "mensagem": "Engine Godot-FastAPI operacional."}

@app.post("/api/login", response_model=ActionResponse)
def login_godot(req: LoginRequest):
    async with get_async_db() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == req.codigo_acesso).first()
        if not jogador: raise HTTPException(status_code=404, detail="Aventureiro não encontrado.")
        campanha = db.query(Campanha).filter(Campanha.party_id == jogador.party_id).first()
        if not campanha: raise HTTPException(status_code=404, detail="O jogador não está numa Party.")

        player_state = build_player_state(jogador)
        scene_state = build_scene_state(campanha, db)

        return ActionResponse(
            sucesso=True, mensagem=f"Bem-vindo, {jogador.nome}.", jogador=player_state, cena=scene_state,
            state_hash=generate_state_hash(jogador, campanha)
        )

@app.get("/api/scene/{telegram_id}", response_model=SceneState)
def get_current_scene(telegram_id: str):
    async with get_async_db() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == telegram_id).first()
        if not jogador: raise HTTPException(404, "Jogador não encontrado")
        campanha = db.query(Campanha).filter(Campanha.party_id == jogador.party_id).first()
        if not campanha: raise HTTPException(404, "Campanha não encontrada")
        return build_scene_state(campanha, db)

@app.get("/api/sync/{telegram_id}")
def get_sync_state(telegram_id: str):
    """Endpoint leve para o Smart Polling do Godot."""
    async with get_async_db() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == telegram_id).first()
        if not jogador: raise HTTPException(404, "Jogador não encontrado")
        campanha = db.query(Campanha).filter(Campanha.party_id == jogador.party_id).first()
        if not campanha: raise HTTPException(404, "Campanha não encontrada")

        return {
            "state_hash": generate_state_hash(jogador, campanha),
            "cena_atual": campanha.cena_atual,
            "em_combate": campanha.em_combate
        }

@app.post("/api/action/{telegram_id}", response_model=ActionResponse)
def execute_action(telegram_id: str, req: ActionRequest):
    async with get_async_db() as db:
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
                    for m in db.query(Jogador).filter(Jogador.party_id == campanha.party_id).all():
                        m.cena_atual = campanha.cena_atual
                    mensagem = f"Moveu-se para {direcao}."
                else:
                    mensagem = "Direção inválida."

        # =========================================================================
        # 2. COMBATE
        # =========================================================================
        elif req.intencao == "COMBATE" and req.target_id:
            target_id = req.target_id
            
            if target_id not in estado_campanha or estado_campanha[target_id] <= 0:
                raise HTTPException(400, "Alvo já está morto ou não existe.")

            enc_id = int(target_id.split('_')[0].replace('enc', ''))
            encontro = db.query(Encontro).filter(Encontro.id == enc_id).first()
            inimigo = db.query(Inimigo).filter(Inimigo.nome == encontro.nome_inimigo).first()
            
            if not inimigo: raise HTTPException(404, "Estatísticas do monstro não encontradas")

            ca_alvo = inimigo.ca
            is_durnn_furia = False
            if getattr(inimigo, 'is_boss', False) and estado_campanha[target_id] <= (inimigo.hp_max / 2):
                is_durnn_furia = True
                ca_alvo = max(10, ca_alvo - 2)

            res = processar_ataque_fisico(jogador, ca_alvo)
            dano_causado = res.dano if res.acertou else 0
            inimigo_morto = False

            if res.acertou:
                estado_campanha[target_id] -= dano_causado
                if estado_campanha[target_id] <= 0:
                    estado_campanha[target_id] = 0
                    inimigo_morto = True
                    loot.append(f"{inimigo.ouro_recompensa or 5} PO")

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

                from ui_utils import XP_POR_NIVEL, HP_POR_CLASSE
                if jogador.xp >= XP_POR_NIVEL.get(jogador.nivel + 1, 999999):
                    jogador.nivel += 1
                    jogador.hp_maximo += HP_POR_CLASSE.get(jogador.classe, 8) + jogador.mod_con
                    jogador.hp_atual = jogador.hp_maximo
                    nivel_subiu = True
                    mensagem += f" Subiste para o Nível {jogador.nivel}!"
            
            revide_acertos = 0
            revide_dano_total = 0
            status_aplicados = []

            if not inimigo_morto and not vitoria:
                mod_inimigo = int(str(inimigo.ataque).replace('+', '')) if '+' in str(inimigo.ataque) else 0
                d20_inimigo = random.randint(1, 20)
                
                if d20_inimigo + mod_inimigo >= jogador.modificador_defesa or d20_inimigo == 20:
                    revide_acertos = 1
                    dano_base = random.randint(1, 4)
                    if is_durnn_furia: dano_base += 2
                    if d20_inimigo == 20: dano_base *= 2
                    revide_dano_total = dano_base
                
                jogador.hp_atual -= revide_dano_total

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

        # =========================================================================
        # 3. USAR HABILIDADE (Fúria, Smite, Surto)
        # =========================================================================
        elif req.intencao == "USAR_HABILIDADE" and req.acao_texto:
            skill = req.acao_texto.lower()
            efeitos = list(jogador.status_efeitos or [])
            if jogador.slots_magia <= 0:
                mensagem = "Sem usos de habilidade disponíveis!"
            else:
                jogador.slots_magia -= 1
                if skill == "furia" and "Fúria" not in efeitos: 
                    efeitos.append("Fúria")
                    mensagem = "Fúria ativada! Bónus de dano aplicado."
                elif skill == "smite" and "Smite" not in efeitos: 
                    efeitos.append("Smite")
                    mensagem = "Smite preparado! O próximo ataque causa dano extra."
                elif skill == "surto":
                    efeitos.append("Surto")
                    mensagem = "Surto de Ação! Ataca duas vezes."
                else:
                    jogador.slots_magia += 1 # Devolve o uso se a skill não for reconhecida
                    mensagem = "Habilidade não reconhecida ou já ativa."
                jogador.status_efeitos = efeitos

        # =========================================================================
        # 4. USAR ITEM (Poções, Antídotos)
        # =========================================================================
        elif req.intencao == "USAR_ITEM" and req.acao_texto:
            from ui_utils import obter_inventario_limpo
            inv = obter_inventario_limpo(jogador.inventario)
            item_nome = req.acao_texto
            
            # Verifica se o item está no inventário
            if item_nome in inv:
                inv.remove(item_nome)
                jogador.inventario = inv
                
                if "poção" in item_nome.lower() or "pocao" in item_nome.lower():
                    cura = sum(random.randint(1, 4) for _ in range(2)) + 2
                    jogador.hp_atual = min(jogador.hp_maximo, jogador.hp_atual + cura)
                    mensagem = f"Usaste {item_nome} e curaste {cura} HP!"
                elif "antídoto" in item_nome.lower() or "antidoto" in item_nome.lower():
                    efeitos = list(jogador.status_efeitos or [])
                    if "Envenenado" in efeitos: efeitos.remove("Envenenado")
                    jogador.status_efeitos = efeitos
                    mensagem = "Veneno neutralizado!"
                else:
                    mensagem = f"Usaste {item_nome}."
            else:
                mensagem = f"Não tens {item_nome} no inventário."

        # =========================================================================
        # 5. EQUIPAR ITEM (Armas e Armaduras)
        # =========================================================================
        elif req.intencao == "EQUIPAR" and req.acao_texto:
            from ui_utils import obter_inventario_limpo, ARMAS_DB, LOJA_CARVALHAL
            inv = obter_inventario_limpo(jogador.inventario)
            item_nome = req.acao_texto
            
            if item_nome in inv:
                is_arma = False
                # Verifica Armas
                for nome, dados in ARMAS_DB.items():
                    if nome.lower() in item_nome.lower():
                        jogador.arma_equipada = nome
                        jogador.dano_dado = dados["dano"]
                        atr = dados["atributo"]
                        mod_escolhido = jogador.mod_dex if atr in ["DEX", "FINESSE"] and jogador.mod_dex >= jogador.mod_str else jogador.mod_str
                        jogador.mod_dano = mod_escolhido
                        jogador.modificador_ataque = mod_escolhido + jogador.proficiencia
                        is_arma = True
                        mensagem = f"Equipaste {nome}! Dano: {dados['dano']}"
                        break
                
                # Verifica Armaduras
                if not is_arma:
                    for nome, dados in LOJA_CARVALHAL.items():
                        if nome.lower() in item_nome.lower() and dados.get("tipo") in ["armadura", "escudo"]:
                            if dados.get("subtipo") == "escudo":
                                jogador.modificador_defesa += dados.get("ca_base", 2)
                                mensagem = f"Equipaste {nome}! CA aumentada."
                            else:
                                ca_base = dados.get("ca_base", 10)
                                if dados.get("subtipo") == "leve": nova_ca = ca_base + jogador.mod_dex
                                elif dados.get("subtipo") == "media": nova_ca = ca_base + min(2, jogador.mod_dex)
                                else: nova_ca = ca_base # pesada
                                jogador.modificador_defesa = nova_ca
                                mensagem = f"Vestiste {nome}! Nova CA: {jogador.modificador_defesa}"
                            jogador.armadura_equipada = nome
                            break
            else:
                mensagem = f"Não tens {item_nome} para equipar."

        # =========================================================================
        # 6. DESCANSO (Curto ou Longo)
        # =========================================================================
        elif req.intencao == "DESCANSO":
            if campanha.cena_atual == "carvalhal":
                jogador.hp_atual = jogador.hp_maximo
                jogador.slots_magia = jogador.slots_magia_max
                jogador.hit_dice_atual = getattr(jogador, 'hit_dice_max', 1)
                jogador.status_efeitos = []
                mensagem = "Descanso Longo na Vila. HP e Magia restaurados!"
            else:
                if jogador.hit_dice_atual > 0:
                    jogador.hit_dice_atual -= 1
                    cura = max(1, (jogador.hp_maximo // 4) + jogador.mod_con)
                    jogador.hp_atual = min(jogador.hp_maximo, jogador.hp_atual + cura)
                    if jogador.classe.lower() == "guerreiro":
                        jogador.slots_magia = min(jogador.slots_magia_max, jogador.slots_magia + 1)
                    mensagem = f"Descanso Curto. Curaste {cura} HP. Hit Dice restantes: {jogador.hit_dice_atual}"
                else:
                    mensagem = "Exausto! Sem Hit Dice. Regressa à Vila."

        # Salva Estado
        campanha.estado_salas = estado_campanha
        db.commit()
        db.refresh(jogador)

        player_state = build_player_state(jogador)
        scene_state = build_scene_state(campanha, db)

        return ActionResponse(
            sucesso=True, mensagem=mensagem, jogador=player_state, cena=scene_state,
            combate=combate_data, vitoria=vitoria, loot=loot, nivel_subiu=nivel_subiu,
            state_hash=generate_state_hash(jogador, campanha)
        )

if __name__ == "__main__":
    print("🚀 A iniciar a API do Godot na porta 8000...")
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)