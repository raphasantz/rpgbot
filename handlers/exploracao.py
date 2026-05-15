import asyncio
import random
import math
import unicodedata
import logging
from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from sqlalchemy import select, delete, func

from database import get_db_session
from models import Jogador, Campanha, Cena, Npc, EncontroAleatorio, Interativo, ObjetoDestrutivel, Missao, Encontro, Inimigo
from ai_engine import interpretar_acao_json, narrar_ambiente, narrar_combate, decidir_atributo_teste, gerar_imagem_sala
from combat_logic import processar_ataque_fisico, processar_ataque_objeto
from action_resolver import ActionResolver, ActionResult
from mapa_engine import extrair_direcao
from ui_utils import (
    obter_inventario_limpo, resumo_status, texto_saidas, teclado_saidas,
    adicionar_ao_inventario, gerar_loot_bau, gerar_loot_inimigo_comum,
    LOJA_CARVALHAL, BACKGROUND_SKILLS, XP_POR_NIVEL, HP_POR_CLASSE, MAGIAS_POR_CLASSE
)
from stats_manager import get_or_create_estatisticas, atualizar_estatistica, registrar_derrota

router = Router()

processing_users = set()
party_locks = {}

@router.callback_query(F.data.startswith("skill_"))
async def skill_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    skill = callback.data.replace("skill_", "")
    
    async with get_db_session() as db:
        result = await db.execute(select(Jogador).filter(Jogador.telefone == user_id))
        jogador = result.scalars().first()
        if not jogador or jogador.slots_magia <= 0:
            await callback.answer("Sem usos disponíveis!", show_alert=True)
            return
        
        jogador.slots_magia -= 1
        msg = ""
        efeitos = list(jogador.status_efeitos or [])
        
        if skill == "surto":
            if "Surto" not in efeitos: efeitos.append("Surto")
            msg = "⚔️ <b>Surto de Ação ativado!</b> Vais realizar um ataque extra neste turno."
        elif skill == "folego":
            cura = random.randint(1, 10) + jogador.nivel
            jogador.hp_atual = min(jogador.hp_maximo, jogador.hp_atual + cura)
            msg = f"❤️ <b>Retomar Fôlego!</b> Recuperaste {cura} HP."
        elif skill == "smite":
            if "Smite" not in efeitos: efeitos.append("Smite")
            msg = "✨ <b>Destruição Divina preparada!</b> Teu próximo ataque terá dano radiante extra."
        elif skill == "furia":
            if "Fúria" not in efeitos: efeitos.append("Fúria")
            msg = "😡 <b>Fúria ativada!</b> Mais dano e resistência a dano físico até o fim do combate."
        elif skill == "formaselvagem":
            cura = random.randint(1, 4) + jogador.nivel
            jogador.hp_atual = min(jogador.hp_maximo, jogador.hp_atual + cura)
            if "Forma Selvagem" not in efeitos: efeitos.append("Forma Selvagem")
            msg = f"🐾 <b>Forma Selvagem!</b> Curaste {cura} HP e teus ataques terão +2d6 de dano extra."
        
        jogador.status_efeitos = efeitos
        await callback.message.answer(msg, parse_mode="HTML")
        await callback.answer("Habilidade usada!")


@router.callback_query(F.data == "ataque_secundario")
async def ataque_secundario_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    async with get_db_session() as db:
        result = await db.execute(select(Jogador).filter(Jogador.telefone == user_id))
        jogador = result.scalars().first()
        if not jogador:
            return await callback.answer("Personagem não encontrado.", show_alert=True)
        
        result_camp = await db.execute(select(Campanha).filter(Campanha.party_id == jogador.party_id))
        campanha = result_camp.scalars().first()
        if not campanha or not campanha.em_combate:
            return await callback.answer("Não estás em combate.", show_alert=True)
        
        estado_campanha = campanha.estado_salas or {}
        ca_alvo = estado_campanha.get("ca_alvo") or 10
        
        dano_original = jogador.mod_dano
        jogador.mod_dano = 0
        res = processar_ataque_fisico(jogador, ca_alvo)
        jogador.mod_dano = dano_original
        
        if res.acertou:
            await callback.message.answer(f"⚔️ <b>Ataque Secundário</b> acerta! Causa {res.dano} de dano extra.\n━━━━━━━━━━━━━━━━\n❤️ {jogador.nome}: {jogador.hp_atual}/{jogador.hp_maximo} HP", parse_mode="HTML")
        else:
            await callback.message.answer("💨 <b>Ataque Secundário</b> falhou.", parse_mode="HTML")
    await callback.answer()


def _normalizar(texto: str) -> str:
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8').lower()


async def verificar_hazards(message, jogador, nova_sala) -> bool:
    hazards = getattr(nova_sala, 'hazards', None) or []
    if not hazards:
        return True

    for hazard in hazards:
        tipo = hazard.get("tipo", "")
        cd = hazard.get("cd", 13)
        dano_str = hazard.get("dano", "1d4")
        descricao = hazard.get("descricao", "Um perigo oculto")

        try:
            partes = dano_str.split("d")
            qtd_dados = int(partes[0])
            faces = int(partes[1])
            dano_total = sum(random.randint(1, faces) for _ in range(qtd_dados))
        except Exception:
            dano_total = random.randint(1, 4)

        if tipo == "dex_save":
            rolagem = random.randint(1, 20) + jogador.mod_dex
            if rolagem >= cd:
                await message.answer(f"⚠️ <b>{descricao}!</b>\n🎲 Teste de Destreza: <b>{rolagem}</b> vs CD {cd} ✅\n<i>Desvias-te habilmente do perigo!</i>", parse_mode="HTML")
            else:
                jogador.hp_atual -= dano_total
                await message.answer(f"⚠️ <b>{descricao}!</b>\n🎲 Teste de Destreza: <b>{rolagem}</b> vs CD {cd} ❌\n🩸 Sofres <b>{dano_total} de dano</b> ao atravessar o terreno perigoso!", parse_mode="HTML")
        elif tipo == "str_save":
            rolagem = random.randint(1, 20) + jogador.mod_str
            if rolagem < cd:
                jogador.hp_atual -= dano_total
                await message.answer(f"⚠️ <b>{descricao}!</b>\n🎲 Teste de Força: <b>{rolagem}</b> vs CD {cd} ❌\n🩸 Sofres <b>{dano_total} de dano</b>!", parse_mode="HTML")
        elif tipo == "con_save":
            rolagem = random.randint(1, 20) + jogador.mod_con
            if rolagem < cd:
                jogador.hp_atual -= dano_total
                await message.answer(f"⚠️ <b>{descricao}!</b>\n🎲 Teste de Constituição: <b>{rolagem}</b> vs CD {cd} ❌\n🩸 Sofres <b>{dano_total} de dano</b>!", parse_mode="HTML")
        elif tipo == "dano_automatico":
            jogador.hp_atual -= dano_total
            await message.answer(f"🔥 <b>{descricao}</b>\n🩸 Sofres <b>{dano_total} de dano</b> automaticamente ao entrar na área.", parse_mode="HTML")

    return jogador.hp_atual > 0


@router.message(F.text & ~F.text.startswith("/"))
async def acao_handler(message: types.Message):
    if not message.text: return
    user_id = str(message.from_user.id)
    if user_id in processing_users: return
    processing_users.add(user_id)
    
    try:
        async with get_db_session() as db:
            result_temp = await db.execute(select(Jogador).filter(Jogador.telefone == user_id))
            jogador_temp = result_temp.scalars().first()
            party_id = jogador_temp.party_id if jogador_temp else None

        if party_id:
            lock = party_locks.setdefault(party_id, asyncio.Lock())
        else:
            lock = party_locks.setdefault(f"solo_{user_id}", asyncio.Lock())

        async with lock:
            async with get_db_session() as db:
                result_jog = await db.execute(select(Jogador).filter(Jogador.telefone == user_id))
                jogador = result_jog.scalars().first()
                
                if jogador and jogador.party_id:
                    result_camp = await db.execute(select(Campanha).filter(Campanha.party_id == jogador.party_id))
                    campanha = result_camp.scalars().first()
                else:
                    campanha = None
                
                if not jogador:
                    return await message.answer("⚠️ Não tens personagem. Usa /criar para começares a tua lenda.")
                if not campanha:
                    return await message.answer(
                        "🤝 <b>SISTEMA DE GRUPO (PARTY)</b>\n"
                        "⚠️ <i>Lembrete: Não podes explorar as masmorras sem um grupo!</i>\n"
                        "👑 <b>/party criar</b> - Começa a tua própria saga e recebe um código.\n"
                        "🔗 <b>/party entrar [CÓDIGO]</b> - Junta-te aos teus amigos.",
                        parse_mode="HTML"
                    )
                
                result_sala = await db.execute(select(Cena).filter(Cena.cod_sala == campanha.cena_atual))
                sala_atual = result_sala.scalars().first()
                if not sala_atual:
                    return await message.answer("⚠️ Erro: Sala atual não encontrada no banco de dados.")
                
                result_enc_ale = await db.execute(select(EncontroAleatorio).filter(EncontroAleatorio.cod_sala == campanha.cena_atual))
                encontro_ale = result_enc_ale.scalars().first()
                if encontro_ale and random.randint(1, 100) <= encontro_ale.chance:
                    if not campanha.em_combate:
                        estado_campanha = dict(campanha.estado_salas or {})
                        estado_campanha[f"derrotado_ale_{encontro_ale.id}"] = False
                        campanha.estado_salas = estado_campanha
                        encontro_temp = Encontro(
                            cod_sala = campanha.cena_atual,
                            nome_inimigo = encontro_ale.nome_inimigo,
                            quantidade = encontro_ale.quantidade
                        )
                        db.add(encontro_temp)
                        await db.flush()
                        await message.answer(f"⚡ <b>Emboscada!</b> {encontro_ale.quantidade}x {encontro_ale.nome_inimigo} surgem das sombras!")
                        campanha.em_combate = True
                
                result_inter = await db.execute(select(Interativo).filter(Interativo.cod_sala == campanha.cena_atual))
                interativos = result_inter.scalars().all()
                result_obj = await db.execute(select(ObjetoDestrutivel).filter(
                    ObjetoDestrutivel.cod_sala == campanha.cena_atual,
                    ObjetoDestrutivel.ativo == True
                ))
                objetos_destrutiveis = result_obj.scalars().all()
                
                nomes_interativos = ", ".join([i.nome for i in interativos]) if interativos else "Nenhum"
                nomes_destrutiveis = ", ".join([o.nome for o in objetos_destrutiveis]) if objetos_destrutiveis else ""
                contexto_objetos = nomes_interativos + (", " + nomes_destrutiveis if nomes_destrutiveis else "")
                
                texto_min = message.text.lower()
                texto_limpo_acao = unicodedata.normalize('NFKD', message.text).encode('ASCII', 'ignore').decode('utf-8').lower()
                
                # --- FASE 1: CHAMADA AO JSON MODE DA IA ---
                is_fuga_temp = any(p in texto_limpo_acao for p in ["fugir", "fujo", "correr", "escapar", "recuar"])
                texto_contexto_ia = f"{message.text} [FUJA]" if is_fuga_temp and campanha.em_combate else message.text
                json_ia = await interpretar_acao_json(texto_contexto_ia, contexto_objetos)
                intencao = json_ia.get("intencao", "OUTRO").upper()
                
                try: await atualizar_estatistica(db, user_id, 'tempo_jogo_minutos', 1)
                except Exception: pass

                # --- BLINDAGEM DE TURNO ---
                efeitos_jogador = list(jogador.status_efeitos or [])
                
                if "Atordoado" in efeitos_jogador:
                    return await message.answer("💫 <b>Estás Atordoado!</b> Perdes o teu turno e não consegues agir.", parse_mode="HTML")

                if intencao == "NAVEGAR" and "Agarrado" in efeitos_jogador:
                    return await message.answer("⛓️ <b>Estás Agarrado!</b> A tua velocidade é 0. Tens de usar a tua ação numa MANOBRA para tentar escapar antes de te moveres.", parse_mode="HTML")

                if campanha.em_combate:
                    estado_campanha = dict(campanha.estado_salas or {})
                    ultimo_jogador = estado_campanha.get("ultimo_jogador_acao")
                    
                    result_aliados = await db.execute(select(Jogador).filter(
                        Jogador.party_id == campanha.party_id,
                        Jogador.cena_atual == campanha.cena_atual,
                        Jogador.hp_atual > 0
                    ))
                    aliados_vivos = result_aliados.scalars().all()
                    
                    if len(aliados_vivos) > 1 and ultimo_jogador == user_id:
                        if intencao not in ["NARRATIVA", "OUTRO"]: 
                            return await message.answer("⏳ <b>Espera a tua vez!</b>\nOutro membro do grupo precisa de agir antes de fazeres outra ação.", parse_mode="HTML")
                    
                    if intencao not in ["NARRATIVA", "OUTRO"]:
                        estado_campanha["ultimo_jogador_acao"] = user_id
                        campanha.estado_salas = estado_campanha

                # --- FASE 2: ROUTE PARA O ACTION RESOLVER ---
                resolver = ActionResolver(db)
                action_result = await resolver.resolver_acao(jogador, campanha, sala_atual, json_ia, message.text)

                # --- FASE 3: PROCESSAMENTO DO RESULTADO ---
                if not action_result.sucesso:
                    await message.answer(f"❌ {action_result.narrativa_mecanica}\n{resumo_status(jogador)}", parse_mode="HTML")
                    return

                # Ação de Navegação tem fluxo próprio (imagens, hazards, etc)
                if action_result.tipo_acao == "navegacao":
                    nova_cena_cod = action_result.dados_extras.get("nova_cena")
                    if not nova_cena_cod:
                        await message.answer(action_result.narrativa_mecanica, parse_mode="HTML")
                        return

                    result_nova_sala = await db.execute(select(Cena).filter(Cena.cod_sala == nova_cena_cod))
                    nova_sala = result_nova_sala.scalars().first()
                    if not nova_sala:
                        await message.answer("⚠️ Erro ao carregar a nova sala.", parse_mode="HTML")
                        return
                    
                    # DALL-E E IMAGENS (Com proteção extra)
                    try:
                        if not nova_sala.imagem_url:
                            msg_temp = await message.answer("🎨 <i>O Mestre está a visualizar o local...</i>", parse_mode="HTML")
                            img_url = await gerar_imagem_sala(nova_sala.nome_sala, nova_sala.descricao_visual)
                            if img_url: 
                                nova_sala.imagem_url = img_url
                            await msg_temp.delete()
                    except Exception as e:
                        logging.error(f"Erro DALL-E: {e}")
                        
                    if nova_sala.imagem_url:
                        try:
                            await message.answer_photo(photo=nova_sala.imagem_url)
                        except Exception:
                            await message.answer("🎨 <i>A névoa obscurece a tua visão... (Falha ao carregar imagem)</i>", parse_mode="HTML")

                    sobreviveu = await verificar_hazards(message, jogador, nova_sala)
                    if not sobreviveu:
                        return await message.answer(f"💀 <b>{jogador.nome.upper()} SUCUMBIU AOS PERIGOS DO TERRENO!</b>\nUse <b>/criar</b> para recomeçar.", parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
                        
                    # Checa ameaças na sala
                    estado_campanha = dict(campanha.estado_salas or {})
                    result_enc_novos = await db.execute(select(Encontro).filter(Encontro.cod_sala == nova_sala.cod_sala))
                    encontros_novos = result_enc_novos.scalars().all()
                    ameacas_vivas = [f"{enc.quantidade}x {enc.nome_inimigo}" for enc in encontros_novos if not estado_campanha.get(f"derrotado_{enc.id}")]
                    alerta = f"\n\n⚠️ <b>AMEAÇAS NA SALA:</b> " + " | ".join(ameacas_vivas) if ameacas_vivas else ""

                    narracao = await narrar_ambiente(jogador.nome, message.text, nova_sala.descricao_visual)

                    await message.answer(f"👣 {action_result.narrativa_mecanica}\n\n📍 <b>{nova_sala.nome_sala}</b>\n{narracao}{alerta}\n\n{texto_saidas(nova_sala)}\n{resumo_status(jogador)}", parse_mode="HTML", reply_markup=teclado_saidas(nova_sala))
                    return

                # Narrativas genéricas
                if action_result.tipo_acao in ["manobra", "interacao", "descanso", "status"]:
                    narracao = await narrar_ambiente(jogador.nome, message.text, sala_atual.descricao_visual)
                    await message.answer(f"{narracao}\n\n{action_result.narrativa_mecanica}\n{resumo_status(jogador)}", parse_mode="HTML")
                    return

                # Combate e Magia: Narração da IA no topo + Bloco Mecânico Limpo
                if action_result.tipo_acao in ["combate", "magia"]:
                    narracao_combate = await narrar_combate(jogador.nome, message.text, action_result.narrativa_mecanica, sala_atual.descricao_visual)
                    msg_final = f"{narracao_combate}\n\n{action_result.narrativa_mecanica}"
                    reply_markup = teclado_saidas(sala_atual) if not campanha.em_combate else None
                    await message.answer(msg_final, parse_mode="HTML", reply_markup=reply_markup)
                    return

                # Fallback Narrativo
                narracao = await narrar_ambiente(jogador.nome, message.text, sala_atual.descricao_visual)
                await message.answer(f"{narracao}\n\n{texto_saidas(sala_atual)}\n{resumo_status(jogador)}", parse_mode="HTML")

    finally:
        processing_users.discard(user_id)


async def lock_garbage_collector():
    while True:
        await asyncio.sleep(1800)
        try:
            chaves_removidas = 0
            for k in list(party_locks.keys()):
                if not party_locks[k].locked():
                    del party_locks[k]
                    chaves_removidas += 1
            if chaves_removidas > 0:
                logging.info(f"🧹 Garbage Collector de Locks: {chaves_removidas} locks inativos removidos.")
        except Exception as e:
            logging.error(f"Erro no Garbage Collector: {e}")