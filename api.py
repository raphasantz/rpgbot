"""
RedNerds Engine API v3
======================
Backend FastAPI para comunicação exclusiva com cliente Godot 4.
Transforma respostas do ActionResolver em schema estruturado para VTT/MUD.
"""

import hashlib
import random
from typing import List, Optional, Dict, Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select

# =============================================================================
# IMPORTS DO MOTOR EXISTENTE
# =============================================================================
from action_resolver import ActionResolver, ActionResult
from ai_engine import interpretar_acao_json
from database import get_db_session
from models import Jogador, Campanha, Cena, Encontro, Inimigo, Interativo, ObjetoDestrutivel
from ui_utils import obter_inventario_limpo

# =============================================================================
# CONFIGURAÇÃO DA APP FASTAPI
# =============================================================================
app = FastAPI(
    title="RedNerds Engine API v3",
    description="Backend estruturado para cliente Godot 4 - MUD/VTT RPG D&D 5e",
    version="3.5.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# MODELOS PYDANTIC - CONTRATO ESTRITO GODOT <-> PYTHON
# =============================================================================

class ActionRequest(BaseModel):
    jogador_id: str = Field(..., description="Telefone/ID único do jogador")
    texto_acao: str = Field(..., description="Texto livre da ação do jogador", min_length=1)

class NarrativaResponse(BaseModel):
    texto_cinematico: str
    texto_mecanico: Optional[str] = None
    alerta_ameaca: Optional[str] = None

class InterfaceVisualResponse(BaseModel):
    imagem_url: Optional[str] = None
    efeito_ecran: Optional[Literal["shake_light", "shake_heavy", "flash_red_and_die", None]] = None

class EfeitosSonorosResponse(BaseModel):
    tocar_efeito: Optional[Literal["sword_hit", "critical_hit", "error", "heal", "level_up", "item_use", None]] = None
    trocar_musica_fundo: Optional[Literal["exploration", "combat_drums", "boss_theme", "village_ambient", None]] = None

class EstadoJogadorResponse(BaseModel):
    nome: str
    classe: str
    nivel: int
    hp_atual: int
    hp_maximo: int
    ca: int
    gold: int
    slots_magia: int
    slots_magia_max: int
    status_efeitos: List[str] = []
    inventario: List[str] = []

class InimigoStatusResponse(BaseModel):
    nome: str
    hp_atual: int
    hp_maximo: int
    is_boss: bool = False
    imagem_url: Optional[str] = None

class EstadoAmbienteResponse(BaseModel):
    nome_sala: str
    em_combate: bool
    saidas_disponiveis: List[str] = []
    inimigos_vivos: List[InimigoStatusResponse] = []
    interativos: List[str] = []
    objetos_destrutiveis: List[str] = []

class ActionResponse(BaseModel):
    sucesso: bool
    tipo_acao: Optional[str] = None
    narrativa: NarrativaResponse
    interface_visual: InterfaceVisualResponse
    efeitos_sonoros: EfeitosSonorosResponse
    estado_jogador: EstadoJogadorResponse
    estado_ambiente: EstadoAmbienteResponse
    state_hash: str

# =============================================================================
# FUNÇÕES AUXILIARES DE MAPEAMENTO (AGORA ASSÍNCRONAS)
# =============================================================================

def gerar_state_hash(jogador: Jogador, campanha: Campanha) -> str:
    estado_str = f"{jogador.telefone}|{jogador.hp_atual}|{jogador.gold}|{jogador.xp}|{campanha.cena_atual}|{campanha.em_combate}|{jogador.nivel}"
    return hashlib.md5(estado_str.encode("utf-8")).hexdigest()

def extrair_saidas_disponiveis(sala: Cena, em_combate: bool) -> List[str]:
    if em_combate or not sala.conexoes: return []
    return [dir.upper() for dir, destino in sala.conexoes.items() if destino]

async def buscar_inimigos_vivos(db, cod_sala: str, estado_campanha: Dict) -> List[InimigoStatusResponse]:
    resultados = []
    result_enc = await db.execute(select(Encontro).filter(Encontro.cod_sala == cod_sala))
    encontros = result_enc.scalars().all()
    
    for enc in encontros:
        if estado_campanha.get(f"derrotado_{enc.id}"): continue
            
        result_ini = await db.execute(select(Inimigo).filter(Inimigo.nome == enc.nome_inimigo))
        inimigo_model = result_ini.scalars().first()
        if not inimigo_model: continue
            
        chave_hp = f"hp_{enc.id}"
        hp_grupo = estado_campanha.get(chave_hp, inimigo_model.hp_max * enc.quantidade)
        
        if hp_grupo > 0:
            inimigos_vivos = min(math.ceil(hp_grupo / inimigo_model.hp_max), enc.quantidade)
            for i in range(inimigos_vivos):
                resultados.append(InimigoStatusResponse(
                    nome=inimigo_model.nome,
                    hp_atual=inimigo_model.hp_max if i < inimigos_vivos - 1 else hp_grupo % inimigo_model.hp_max or inimigo_model.hp_max,
                    hp_maximo=inimigo_model.hp_max,
                    is_boss=getattr(inimigo_model, 'is_boss', False),
                    imagem_url=inimigo_model.imagem_url if hasattr(inimigo_model, 'imagem_url') else None
                ))
    return resultados

async def buscar_interativos(db, cod_sala: str) -> List[str]:
    result = await db.execute(select(Interativo).filter(Interativo.cod_sala == cod_sala, Interativo.ativo == True))
    return [it.nome for it in result.scalars().all()]

async def buscar_destrutiveis(db, cod_sala: str) -> List[str]:
    result = await db.execute(select(ObjetoDestrutivel).filter(ObjetoDestrutivel.cod_sala == cod_sala, ObjetoDestrutivel.ativo == True))
    return [obj.nome for obj in result.scalars().all()]

# =============================================================================
# ROTAS DA API
# =============================================================================

@app.post("/api/v3/action", response_model=ActionResponse, tags=["Gameplay"])
async def executar_acao_jogador(req: ActionRequest):
    async with get_db_session() as db:
        result_jog = await db.execute(select(Jogador).filter(Jogador.telefone == req.jogador_id))
        jogador = result_jog.scalars().first()
        if not jogador:
            raise HTTPException(status_code=404, detail="Jogador não encontrado.")
        
        result_camp = await db.execute(select(Campanha).filter(Campanha.party_id == jogador.party_id))
        campanha = result_camp.scalars().first()
        if not campanha:
            raise HTTPException(status_code=404, detail="Campanha não encontrada.")

        result_sala = await db.execute(select(Cena).filter(Cena.cod_sala == campanha.cena_atual))
        sala_atual = result_sala.scalars().first()

        # 1. IA Extrai Intenção
        json_ia = await interpretar_acao_json(req.texto_acao, sala_atual.descricao_visual if sala_atual else "Nenhum")

        # 2. Cérebro Resolve Ação
        resolver = ActionResolver(db)
        resultado: ActionResult = await resolver.resolver_acao(jogador, campanha, sala_atual, json_ia, req.texto_acao)

        # 3. Atualizar Estado Local
        estado_campanha = dict(campanha.estado_salas or {})
        inimigos_vivos = await buscar_inimigos_vivos(db, sala_atual.cod_sala, estado_campanha)

        # 4. Construir Resposta Visual/Áudio
        efeito_ecran = "flash_red_and_die" if jogador.hp_atual <= 0 else "shake_light" if (resultado.tipo_acao == "combate" and resultado.sucesso) else None
        sfx = "error" if jogador.hp_atual <= 0 else "sword_hit" if resultado.tipo_acao == "combate" else None
        bgm = "combat_drums" if campanha.em_combate else "exploration"

        narrativa = NarrativaResponse(
            texto_cinematico=resultado.narrativa_mecanica,
            alerta_ameaca=f"⚠️ {len(inimigos_vivos)} inimigos!" if inimigos_vivos and campanha.em_combate else None
        )

        return ActionResponse(
            sucesso=resultado.sucesso,
            tipo_acao=resultado.tipo_acao,
            narrativa=narrativa,
            interface_visual=InterfaceVisualResponse(imagem_url=sala_atual.imagem_url if sala_atual else None, efeito_ecran=efeito_ecran),
            efeitos_sonoros=EfeitosSonorosResponse(tocar_efeito=sfx, trocar_musica_fundo=bgm),
            estado_jogador=EstadoJogadorResponse(
                nome=jogador.nome, classe=jogador.classe, nivel=jogador.nivel,
                hp_atual=jogador.hp_atual, hp_maximo=jogador.hp_maximo, ca=jogador.modificador_defesa,
                gold=jogador.gold, slots_magia=jogador.slots_magia, slots_magia_max=jogador.slots_magia_max,
                status_efeitos=jogador.status_efeitos or [], inventario=obter_inventario_limpo(jogador.inventario) if jogador.inventario else []
            ),
            estado_ambiente=EstadoAmbienteResponse(
                nome_sala=sala_atual.nome_sala, em_combate=campanha.em_combate,
                saidas_disponiveis=extrair_saidas_disponiveis(sala_atual, campanha.em_combate),
                inimigos_vivos=inimigos_vivos,
                interativos=await buscar_interativos(db, sala_atual.cod_sala),
                objetos_destrutiveis=await buscar_destrutiveis(db, sala_atual.cod_sala)
            ),
            state_hash=gerar_state_hash(jogador, campanha)
        )

@app.get("/api/v3/player/status", response_model=ActionResponse, tags=["Gameplay"])
async def obter_status_jogador(jogador_id: str = Query(..., alias="jogador_id")):
    async with get_db_session() as db:
        result_jog = await db.execute(select(Jogador).filter(Jogador.telefone == jogador_id))
        jogador = result_jog.scalars().first()
        if not jogador: raise HTTPException(status_code=404, detail="Jogador não encontrado.")
        
        result_camp = await db.execute(select(Campanha).filter(Campanha.party_id == jogador.party_id))
        campanha = result_camp.scalars().first()
        
        result_sala = await db.execute(select(Cena).filter(Cena.cod_sala == campanha.cena_atual))
        sala_atual = result_sala.scalars().first()

        estado_campanha = dict(campanha.estado_salas or {})
        inimigos_vivos = await buscar_inimigos_vivos(db, sala_atual.cod_sala, estado_campanha)

        narrativa = NarrativaResponse(
            texto_cinematico=f"Bem-vindo de volta, {jogador.nome}! Estás na {sala_atual.nome_sala}.",
            alerta_ameaca=f"⚠️ {len(inimigos_vivos)} inimigos próximos!" if inimigos_vivos and campanha.em_combate else None
        )

        return ActionResponse(
            sucesso=True,
            tipo_acao="status",
            narrativa=narrativa,
            interface_visual=InterfaceVisualResponse(imagem_url=sala_atual.imagem_url if sala_atual else None),
            efeitos_sonoros=EfeitosSonorosResponse(trocar_musica_fundo="combat_drums" if campanha.em_combate else "exploration"),
            estado_jogador=EstadoJogadorResponse(
                nome=jogador.nome, classe=jogador.classe, nivel=jogador.nivel,
                hp_atual=jogador.hp_atual, hp_maximo=jogador.hp_maximo, ca=jogador.modificador_defesa,
                gold=jogador.gold, slots_magia=jogador.slots_magia, slots_magia_max=jogador.slots_magia_max,
                status_efeitos=jogador.status_efeitos or [], inventario=obter_inventario_limpo(jogador.inventario) if jogador.inventario else []
            ),
            estado_ambiente=EstadoAmbienteResponse(
                nome_sala=sala_atual.nome_sala, em_combate=campanha.em_combate,
                saidas_disponiveis=extrair_saidas_disponiveis(sala_atual, campanha.em_combate),
                inimigos_vivos=inimigos_vivos,
                interativos=await buscar_interativos(db, sala_atual.cod_sala),
                objetos_destrutiveis=await buscar_destrutiveis(db, sala_atual.cod_sala)
            ),
            state_hash=gerar_state_hash(jogador, campanha)
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)