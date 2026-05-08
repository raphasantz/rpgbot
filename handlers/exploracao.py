import asyncio
import random
import math
import unicodedata
import logging
from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove

from database import get_db_session
from models import Jogador, Campanha, Cena, Npc, EncontroAleatorio, Interativo, ObjetoDestrutivel, Missao, Encontro, Inimigo
from ai_engine import interpretar_acao, narrar_ambiente, narrar_combate, decidir_atributo_teste, gerar_imagem_sala
from combat_logic import processar_ataque_fisico, processar_ataque_objeto
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
    
    with get_db_session() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == user_id).first()
        if not jogador or jogador.slots_magia <= 0:
            await callback.answer("Sem usos disponíveis!", show_alert=True)
            return
        
        jogador.slots_magia -= 1
        msg = ""
        
        if skill == "surto":
            if not hasattr(jogador, '_surto'):
                jogador._surto = True
            msg = "⚔️ <b>Surto de Ação ativado!</b> Vais realizar um ataque extra neste turno."
        elif skill == "folego":
            cura = random.randint(1, 10) + jogador.nivel
            jogador.hp_atual = min(jogador.hp_maximo, jogador.hp_atual + cura)
            msg = f"❤️ <b>Retomar Fôlego!</b> Recuperaste {cura} HP."
        elif skill == "smite":
            jogador._smite = True
            msg = "✨ <b>Destruição Divina preparada!</b> Teu próximo ataque terá dano radiante extra."
        elif skill == "furia":
            jogador._furia = True
            msg = "😡 <b>Fúria ativada!</b> Mais dano e resistência a dano físico até o fim do combate."
        elif skill == "formaselvagem":
            cura = random.randint(1, 4) + jogador.nivel
            jogador.hp_atual = min(jogador.hp_maximo, jogador.hp_atual + cura)
            jogador._formaselvagem = True
            msg = f"🐾 <b>Forma Selvagem!</b> Curaste {cura} HP e teus ataques terão +2d6 de dano extra."
        
        await callback.message.answer(msg, parse_mode="HTML")
        await callback.answer("Habilidade usada!")


@router.callback_query(F.data == "ataque_secundario")
async def ataque_secundario_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    with get_db_session() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == user_id).first()
        if not jogador:
            return await callback.answer("Personagem não encontrado.", show_alert=True)
        
        campanha = db.query(Campanha).filter(Campanha.party_id == jogador.party_id).first()
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


KEYWORDS_POR_CLASSE = {
    "artífice": {
        "explosão arcana": {"bonus_dano": 4, "texto": "Explosão Arcana: +1d4 de dano elemental extra!"},
        "retornar à vida": {"cura": True, "texto": "Retornar à Vida: O teu aliado recupera 1d8+INT HP."},
        "infusão": {"bonus_ca": 2, "texto": "Infusão Protetora: +2 de CA neste turno."},
    },
    "bárbaro": {
        "temerário": {"vantagem": True, "texto": "Ataque Temerário: Rolaste com Vantagem! Inimigos ganham vantagem no revide."},
        "temerario": {"vantagem": True, "texto": "Ataque Temerário: Rolaste com Vantagem! Inimigos ganham vantagem no revide."},
        "reckless":  {"vantagem": True, "texto": "Ataque Temerário: Rolaste com Vantagem! Inimigos ganham vantagem no revide."},
    },
    "guerreiro": {
        "estocar": {"bonus_ataque": 2, "texto": "Estilo de Combate: +2 no ataque de estoques."},
        "defesa total": {"bonus_ca": 4, "texto": "Defesa Total: +4 de CA até o próximo turno."},
    },
    "paladino": {
        "aura": {"bonus_ca": 3, "texto": "Aura Protetora: +3 de CA pela presença divina."},
        "abjurar": {"bonus_ca": 5, "texto": "Abjuração: +5 de CA neste turno."},
    },
    "monge": {
        "flurry": {"ataque_extra": True, "texto": "Torrente de Golpes: Ataque extra sem custo de uso!"},
        "torrente": {"ataque_extra": True, "texto": "Torrente de Golpes: Ataque extra sem custo de uso!"},
        "ki": {"bonus_ataque": 2, "texto": "Ki Focado: +2 no ataque."},
    },
    "ladino": {
        "furtivo": {"dano_extra": "sneak_attack", "texto": "Ataque Furtivo ativado!"},
        "sorrateiro": {"dano_extra": "sneak_attack", "texto": "Ataque Furtivo ativado!"},
        "pelas costas": {"dano_extra": "sneak_attack", "texto": "Ataque pelas costas — Ataque Furtivo!"},
    },
    "patrulheiro": {
        "marca": {"bonus_dano": 6, "texto": "Marca do Caçador: +1d6 no próximo ataque."},
    },
}


def _normalizar(texto: str) -> str:
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8').lower()


def resolver_alvo(texto: str, encontros_ativos: list, objetos_destrutiveis: list) -> tuple:
    texto_norm = _normalizar(texto)

    if encontros_ativos:
        return "inimigo", None

    for obj in objetos_destrutiveis:
        if not obj.ativo:
            continue
        nome_norm = _normalizar(obj.nome)
        palavras_obj = nome_norm.split()
        if any(palavra in texto_norm for palavra in palavras_obj if len(palavra) > 3):
            return "objeto_destrutivel", obj

    return "ambiente", None


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
                await message.answer(
                    f"⚠️ <b>{descricao}!</b>\n"
                    f"🎲 Teste de Destreza: <b>{rolagem}</b> vs CD {cd} ✅\n"
                    f"<i>Desvias-te habilmente do perigo!</i>",
                    parse_mode="HTML"
                )
            else:
                jogador.hp_atual -= dano_total
                await message.answer(
                    f"⚠️ <b>{descricao}!</b>\n"
                    f"🎲 Teste de Destreza: <b>{rolagem}</b> vs CD {cd} ❌\n"
                    f"🩸 Sofres <b>{dano_total} de dano</b> ao atravessar o terreno perigoso!",
                    parse_mode="HTML"
                )

        elif tipo == "str_save":
            rolagem = random.randint(1, 20) + jogador.mod_str
            if rolagem < cd:
                jogador.hp_atual -= dano_total
                await message.answer(
                    f"⚠️ <b>{descricao}!</b>\n"
                    f"🎲 Teste de Força: <b>{rolagem}</b> vs CD {cd} ❌\n"
                    f"🩸 Sofres <b>{dano_total} de dano</b>!",
                    parse_mode="HTML"
                )

        elif tipo == "con_save":
            rolagem = random.randint(1, 20) + jogador.mod_con
            if rolagem < cd:
                jogador.hp_atual -= dano_total
                await message.answer(
                    f"⚠️ <b>{descricao}!</b>\n"
                    f"🎲 Teste de Constituição: <b>{rolagem}</b> vs CD {cd} ❌\n"
                    f"🩸 Sofres <b>{dano_total} de dano</b>!",
                    parse_mode="HTML"
                )

        elif tipo == "dano_automatico":
            jogador.hp_atual -= dano_total
            await message.answer(
                f"🔥 <b>{descricao}</b>\n"
                f"🩸 Sofres <b>{dano_total} de dano</b> automaticamente ao entrar na área.",
                parse_mode="HTML"
            )

    return jogador.hp_atual > 0


@router.message(F.text & ~F.text.startswith("/"))
async def acao_handler(message: types.Message):
    if not message.text: return
    user_id = str(message.from_user.id)
    if user_id in processing_users: return
    processing_users.add(user_id)
    
    try:
        with get_db_session() as db:
            jogador_temp = db.query(Jogador).filter(Jogador.telefone == user_id).first()
            party_id = jogador_temp.party_id if jogador_temp else None

        if party_id:
            lock = party_locks.setdefault(party_id, asyncio.Lock())
        else:
            lock = party_locks.setdefault(f"solo_{user_id}", asyncio.Lock())

        async with lock:
            with get_db_session() as db:
                jogador = db.query(Jogador).filter(Jogador.telefone == user_id).first()
                campanha = db.query(Campanha).filter(Campanha.party_id == jogador.party_id).first() if jogador and jogador.party_id else None
                
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
                
                sala_atual = db.query(Cena).filter(Cena.cod_sala == campanha.cena_atual).first()
                if not sala_atual:
                    return await message.answer("⚠️ Erro: Sala atual não encontrada no banco de dados.")
                
                encontro_ale = db.query(EncontroAleatorio).filter(EncontroAleatorio.cod_sala == campanha.cena_atual).first()
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
                        db.flush()
                        
                        await message.answer(f"⚡ <b>Emboscada!</b> {encontro_ale.quantidade}x {encontro_ale.nome_inimigo} surgem das sombras!")
                        campanha.em_combate = True
                
                interativos = db.query(Interativo).filter(Interativo.cod_sala == campanha.cena_atual).all()
                objetos_destrutiveis = db.query(ObjetoDestrutivel).filter(
                    ObjetoDestrutivel.cod_sala == campanha.cena_atual,
                    ObjetoDestrutivel.ativo == True
                ).all()
                nomes_interativos = ", ".join([i.nome for i in interativos]) if interativos else "Nenhum"
                nomes_destrutiveis = ", ".join([o.nome for o in objetos_destrutiveis]) if objetos_destrutiveis else ""
                contexto_objetos = nomes_interativos + (", " + nomes_destrutiveis if nomes_destrutiveis else "")
                
                intencao = await interpretar_acao(message.text, interativos_disponiveis=contexto_objetos)
                
                try: atualizar_estatistica(db, user_id, 'tempo_jogo_minutos', 1)
                except Exception: pass

                texto_min = message.text.lower()
                texto_limpo_acao = unicodedata.normalize('NFKD', message.text).encode('ASCII', 'ignore').decode('utf-8').lower()
                
                direcao_temp = await extrair_direcao(message.text, sala_atual.conexoes)
                direcao_temp = direcao_temp.strip().lower() if direcao_temp else "invalido"

                conexoes_lower_temp = {}
                for k, v in sala_atual.conexoes.items():
                    chave_limpa = k.strip().lower()
                    chave_limpa = unicodedata.normalize('NFKD', chave_limpa).encode('ASCII', 'ignore').decode('utf-8')
                    valor_limpo = v.strip() if isinstance(v, str) else ""
                    if valor_limpo:
                        conexoes_lower_temp[chave_limpa] = valor_limpo

                if direcao_temp not in conexoes_lower_temp:
                    for k in conexoes_lower_temp.keys():
                        if k in texto_limpo_acao.split() or k == texto_limpo_acao:
                            direcao_temp = k
                            break

                is_fuga_temp = any(p in texto_limpo_acao for p in ["fugir", "fujo", "correr", "escapar", "recuar"])

                # =========================================================================
                # --- O LEÃO DE CHÁCARA (Blindagem de Turnos e Condições) ---
                # =========================================================================
                acao_texto = message.text.lower()
                
                # 1. Trava de Movimento (Agarrado)
                if "Agarrado" in (jogador.status_efeitos or []):
                    if any(palavra in acao_texto for palavra in ["correr", "fugir", "andar", "ir", "norte", "sul", "leste", "oeste", "recuar"]):
                        return await message.answer("⛓️ <b>Estás Agarrado!</b> A tua velocidade é 0. Tens de usar a tua ação numa MANOBRA para tentar escapar antes de te moveres.", parse_mode="HTML")

                # 2. Trava de Spam em Combate Multiplayer (Rodízio Soft)
                if campanha.em_combate:
                    estado_campanha = dict(campanha.estado_salas or {})
                    ultimo_jogador = estado_campanha.get("ultimo_jogador_acao")
                    
                    aliados_vivos = db.query(Jogador).filter(
                        Jogador.party_id == campanha.party_id,
                        Jogador.cena_atual == campanha.cena_atual,
                        Jogador.hp_atual > 0
                    ).all()
                    
                    # Se há mais de 1 jogador vivo, impede que o mesmo spamme 2 ações seguidas
                    if len(aliados_vivos) > 1 and ultimo_jogador == user_id:
                        # Permite apenas falar/ver inventário
                        if not any(p in texto_limpo_acao for p in ["falar", "conversar", "dizer", "olhar", "status", "inventario"]):
                            return await message.answer("⏳ <b>Espera a tua vez!</b>\nOutro membro do grupo precisa de agir antes de fazeres outra ação.", parse_mode="HTML")
                    
                    # Atualiza o último a jogar se foi uma ação real
                    if not any(p in texto_limpo_acao for p in ["falar", "conversar", "dizer", "olhar", "status", "inventario"]):
                        estado_campanha["ultimo_jogador_acao"] = user_id
                        campanha.estado_salas = estado_campanha
                # =========================================================================
                
                if "CURAR" in intencao or ("pocao" in texto_limpo_acao and any(p in texto_limpo_acao for p in ["beber", "tomar", "usar", "bebo", "tomo", "uso", "bebe", "usa"])) or "antidoto" in texto_limpo_acao:
                    inv_linhas = obter_inventario_limpo(jogador.inventario)
                    
                    if "antidoto" in texto_limpo_acao:
                        antidoto = next((i for i in inv_linhas if "antídoto" in i.lower() or "antidoto" in i.lower()), None)
                        if antidoto:
                            inv_linhas.remove(antidoto)
                            jogador.inventario = inv_linhas
                            efeitos = list(jogador.status_efeitos) if jogador.status_efeitos else []
                            if "Envenenado" in efeitos:
                                efeitos.remove("Envenenado")
                            jogador.status_efeitos = efeitos
                            return await message.answer(f"🧪 Bebeste o {antidoto}. O veneno foi neutralizado!\n{resumo_status(jogador)}", parse_mode="HTML")
                        else:
                            return await message.answer("⚠️ <i>Não tens nenhum Antídoto no inventário! (Usa /loja para comprar)</i>", parse_mode="HTML")
                    
                    pocao = next((i for i in inv_linhas if i in LOJA_CARVALHAL and LOJA_CARVALHAL[i]["tipo"] == "pocao" and "antídoto" not in i.lower()), None)
                    if pocao:
                        inv_linhas.remove(pocao)
                        jogador.inventario = inv_linhas
                        cura = sum(random.randint(1, 4) for _ in range(2)) + 2
                        jogador.hp_atual = min(jogador.hp_maximo, jogador.hp_atual + cura)
                        return await message.answer(f"🧪 Bebeste a {pocao} e recuperaste HP!\n{resumo_status(jogador)}", parse_mode="HTML")
                    else:
                        return await message.answer("⚠️ <i>Não tens nenhuma poção!</i>", parse_mode="HTML")

                elif ("NAVEGAR" in intencao or "NAVEGAR_FURTIVO" in intencao) and (direcao_temp in conexoes_lower_temp or is_fuga_temp or len(message.text.split()) <= 3):
                    
                    encontros_atuais = db.query(Encontro).filter(Encontro.cod_sala == campanha.cena_atual).all()
                    estado_campanha = dict(campanha.estado_salas) if campanha.estado_salas else {}
                    encontro_bloqueio = next((e for e in encontros_atuais if not estado_campanha.get(f"derrotado_{e.id}")), None)

                    if encontro_bloqueio:
                        if is_fuga_temp:
                            destino_fuga = campanha.cena_anterior
                            
                            if not destino_fuga:
                                if campanha.cena_atual != "carvalhal":
                                    destino_fuga = "carvalhal"
                                else:
                                    return await message.answer("🛑 <b>Não tens para onde recuar!</b> Terás que lutar.", parse_mode="HTML")

                            mod_ataque_inimigo = 4   
                            dano_dado_inimigo = 6    

                            rolagem_inimigo = random.randint(1, 20)
                            total_ataque_inimigo = rolagem_inimigo + mod_ataque_inimigo

                            if rolagem_inimigo == 20 or total_ataque_inimigo >= jogador.modificador_defesa:
                                dano_fuga = random.randint(1, dano_dado_inimigo)
                                if rolagem_inimigo == 20:
                                    dano_fuga += random.randint(1, dano_dado_inimigo) 

                                jogador.hp_atual -= dano_fuga
                                if jogador.hp_atual <= 0:
                                    return await message.answer(
                                        f"💀 <b>{jogador.nome.upper()} MORREU!</b>\n"
                                        f"Foste abatido por um <b>Ataque de Oportunidade</b> de "
                                        f"{encontro_bloqueio.nome_inimigo} ao tentar fugir (Dano: {dano_fuga})!\n\n"
                                        f"Use <b>/criar</b> para recomeçar a tua lenda.",
                                        parse_mode="HTML", reply_markup=ReplyKeyboardRemove()
                                    )
                                return await message.answer(
                                    f"🩸 <b>Fuga Falhou!</b> Viraste as costas a {encontro_bloqueio.nome_inimigo} "
                                    f"e sofreste um <b>Ataque de Oportunidade</b>! Levaste {dano_fuga} de dano letal nas costas!\n"
                                    f"{resumo_status(jogador)}",
                                    parse_mode="HTML"
                                )
                            else:
                                campanha.cena_atual = destino_fuga
                                campanha.cena_anterior = None
                                sala_destino = db.query(Cena).filter(Cena.cod_sala == campanha.cena_atual).first()

                                if not sala_destino.imagem_url:
                                    msg_temp = await message.answer("🎨 <i>O Mestre está a visualizar o local...</i>", parse_mode="HTML")
                                    img_url = await gerar_imagem_sala(sala_destino.nome_sala, sala_destino.descricao_visual)
                                    if img_url:
                                        sala_destino.imagem_url = img_url
                                    await msg_temp.delete()
                                    
                                if sala_destino.imagem_url:
                                    await message.answer_photo(photo=sala_destino.imagem_url)

                                return await message.answer(f"🏃 <b>Fuga bem sucedida!</b>\n\n📍 <b>{sala_destino.nome_sala}</b>\n{sala_destino.descricao_visual}\n{texto_saidas(sala_destino)}\n{resumo_status(jogador)}", parse_mode="HTML", reply_markup=teclado_saidas(sala_destino))
                        else:
                            return await message.answer(f"🛑 <b>Caminho Bloqueado!</b> Luta contra {encontro_bloqueio.nome_inimigo}!", parse_mode="HTML")

                    direcao = direcao_temp
                    conexoes_lower = conexoes_lower_temp
                    if direcao in conexoes_lower:
                        
                        if "Cobertura" in (jogador.status_efeitos or []):
                            efeitos_atuais = list(jogador.status_efeitos)
                            efeitos_atuais.remove("Cobertura")
                            jogador.status_efeitos = efeitos_atuais
                            
                        campanha.cena_anterior = campanha.cena_atual
                        campanha.cena_atual = conexoes_lower[direcao]
                        nova_sala = db.query(Cena).filter(Cena.cod_sala == campanha.cena_atual).first()
                        alerta = ""
                        encontros_novos = db.query(Encontro).filter(Encontro.cod_sala == nova_sala.cod_sala).all()
                        ameacas_vivas = []
                        for enc in encontros_novos:
                            if not estado_campanha.get(f"derrotado_{enc.id}"):
                                ameacas_vivas.append(f"{enc.quantidade}x {enc.nome_inimigo}")
                        
                        if ameacas_vivas:
                            alerta = f"\n\n⚠️ <b>AMEAÇAS NA SALA:</b> " + " | ".join(ameacas_vivas)
                        
                        if not nova_sala.imagem_url:
                            msg_temp = await message.answer("🎨 <i>O Mestre está a visualizar o local...</i>", parse_mode="HTML")
                            img_url = await gerar_imagem_sala(nova_sala.nome_sala, nova_sala.descricao_visual)
                            if img_url:
                                nova_sala.imagem_url = img_url
                            await msg_temp.delete()
                            
                        if nova_sala.imagem_url:
                            await message.answer_photo(photo=nova_sala.imagem_url)

                        sobreviveu = await verificar_hazards(message, jogador, nova_sala)
                        if not sobreviveu:
                            return await message.answer(
                                f"💀 <b>{jogador.nome.upper()} SUCUMBIU AOS PERIGOS DO TERRENO!</b>\nUse <b>/criar</b> para recomeçar.",
                                parse_mode="HTML", reply_markup=ReplyKeyboardRemove()
                            )
                            
                        return await message.answer(f"👣 Segues para {direcao}.\n\n📍 <b>{nova_sala.nome_sala}</b>\n{nova_sala.descricao_visual}{alerta}\n{texto_saidas(nova_sala)}\n{resumo_status(jogador)}", parse_mode="HTML", reply_markup=teclado_saidas(nova_sala))
                    else:
                        return await message.answer(f"🤔 Caminho bloqueado.\n{texto_saidas(sala_atual)}")

                elif any(p in texto_limpo_acao for p in ["falar", "conversar", "perguntar", "ferreiro", "missao"]):
                    
                    npcs_na_sala = db.query(Npc).filter(Npc.cod_sala == campanha.cena_atual).all()
                    if npcs_na_sala:
                        for npc in npcs_na_sala:
                            nome_npc_limpo = unicodedata.normalize('NFKD', npc.nome).encode('ASCII', 'ignore').decode('utf-8').lower()
                            if nome_npc_limpo in texto_limpo_acao:
                                dialogo = npc.dialogo_base
                                inv = obter_inventario_limpo(jogador.inventario)
                                if npc.item_gatilho and any(npc.item_gatilho.lower() in item.lower() for item in inv):
                                    dialogo = npc.dialogo_item_especial or npc.dialogo_base
                                
                                narracao = await narrar_ambiente(jogador.nome, f"Conversando com {npc.nome}: {dialogo}", sala_atual.descricao_visual)
                                return await message.answer(f"🧙 <b>{npc.nome}:</b>\n{narracao}\n{resumo_status(jogador)}", parse_mode="HTML")
                        nomes_npcs = ", ".join([n.nome for n in npcs_na_sala])
                        return await message.answer(f"👥 Podes falar com: <b>{nomes_npcs}</b>.", parse_mode="HTML")
                    
                    missoes_globais = db.query(Missao).filter(Missao.jogador_telefone == "MULTI").all()
                    for mg in missoes_globais:
                        nome_npc_limpo = unicodedata.normalize('NFKD', mg.npc_nome).encode('ASCII', 'ignore').decode('utf-8').lower()
                        primeiro_nome_npc = nome_npc_limpo.split()[0] if nome_npc_limpo else ""
                        
                        if primeiro_nome_npc and (primeiro_nome_npc in texto_limpo_acao or nome_npc_limpo in texto_limpo_acao):
                            existe = db.query(Missao).filter(Missao.jogador_telefone == user_id, Missao.titulo == mg.titulo).first()
                            if not existe:
                                nova_missao = Missao(
                                    jogador_telefone=user_id, npc_nome=mg.npc_nome, titulo=mg.titulo,
                                    descricao=mg.descricao, objetivo_item=mg.objetivo_item, objetivo_quantidade=mg.objetivo_quantidade,
                                    recompensa_xp=mg.recompensa_xp, recompensa_ouro=mg.recompensa_ouro, recompensa_item=mg.recompensa_item, concluida=False
                                )
                                db.add(nova_missao)
                                await message.answer(f"📜 <b>Nova Missão:</b> {mg.titulo}\n<i>Anotaste o pedido de {mg.npc_nome} no teu diário. (Usa /missoes para ver)</i>", parse_mode="HTML")
                                
                                rep = dict(jogador.reputacao or {})
                                rep["carvalhal"] = rep.get("carvalhal", 0) + 2
                                jogador.reputacao = rep

                    if campanha.cena_atual == "carvalhal" and any(p in texto_limpo_acao for p in ["ferreiro", "falar", "conversar"]):
                        missao = db.query(Missao).filter(Missao.jogador_telefone == user_id, Missao.npc_nome == "Ferreiro de Carvalhal").first()
                        inv = obter_inventario_limpo(jogador.inventario)
                        qtd_item = sum(1 for i in inv if "Dente de Goblin" in i)
                        
                        if not missao:
                            nova_missao = Missao(
                                jogador_telefone=user_id, npc_nome="Ferreiro de Carvalhal", titulo="Lâminas e Dentes",
                                descricao="Goblins têm atacado as caravanas. Traz-me 3 Dentes de Goblin como prova de abate na masmorra.",
                                objetivo_item="Dente de Goblin", objetivo_quantidade=3, recompensa_ouro=50, recompensa_xp=150
                            )
                            db.add(nova_missao)
                            msg_npc = "🔨 <b>Ferreiro de Carvalhal:</b>\n<i>'Saudações! Goblins asquerosos têm atacado as minhas caravanas de minério nas redondezas. Traz-me 3 Dentes de Goblin como prova de que estás a limpar a Cidadela e eu dou-te um belo saco de moedas.'</i>\n\n📜 <b>Nova Missão Adicionada:</b> Lâminas e Dentes (Usa /missoes para ver)"
                            return await message.answer(msg_npc, parse_mode="HTML")
                        elif not missao.concluida:
                            if qtd_item >= missao.objetivo_quantidade:
                                for _ in range(missao.objetivo_quantidade):
                                    item_remover = next(i for i in inv if "Dente de Goblin" in i)
                                    inv.remove(item_remover)
                                jogador.inventario = inv
                                jogador.gold += missao.recompensa_ouro
                                jogador.xp += missao.recompensa_xp
                                missao.concluida = True
                                
                                rep = dict(jogador.reputacao or {})
                                rep["carvalhal"] = rep.get("carvalhal", 0) + 10
                                jogador.reputacao = rep
                                
                                msg_npc = f"🔨 <b>Ferreiro de Carvalhal:</b>\n<i>'Pelos Deuses, tu conseguiste mesmo! Um brinde à tua bravura! Aqui está o teu pagamento, herói.'</i>\n\n✅ <b>Missão Concluída: Lâminas e Dentes!</b>\n🪙 +{missao.recompensa_ouro} PO\n🌟 +{missao.recompensa_xp} XP"
                                return await message.answer(msg_npc, parse_mode="HTML")
                            else:
                                msg_npc = f"🔨 <b>Ferreiro de Carvalhal:</b>\n<i>'Ainda não tens os {missao.objetivo_quantidade} Dentes de Goblin? Despacha-te! A estrada não é segura.'</i> (Tens {qtd_item}/{missao.objetivo_quantidade})"
                                return await message.answer(msg_npc, parse_mode="HTML")
                    
                    narracao = await narrar_ambiente(jogador.nome, message.text, sala_atual.descricao_visual)
                    return await message.answer(f"{narracao}\n\n{resumo_status(jogador)}", parse_mode="HTML")

                elif "COBERTURA" in intencao:
                    efeitos = list(jogador.status_efeitos or [])
                    if "Cobertura" not in efeitos:
                        efeitos.append("Cobertura")
                        jogador.status_efeitos = efeitos
                        narracao = await narrar_ambiente(jogador.nome, message.text, sala_atual.descricao_visual)
                        await message.answer(f"{narracao}\n\n🛡️ <b>Cobertura!</b> Protegeste-te atrás do cenário. Ganhaste +2 de CA contra os próximos ataques inimigos.\n{resumo_status(jogador)}", parse_mode="HTML")
                    else:
                        await message.answer("⚠️ Já estás protegido em cobertura.", parse_mode="HTML")

                elif "MANOBRA" in intencao:
                    efeitos_atuais = list(jogador.status_efeitos or [])
                    if "levantar" in texto_limpo_acao or "levanto" in texto_limpo_acao:
                        if "Caído" in efeitos_atuais:
                            efeitos_atuais.remove("Caído")
                            jogador.status_efeitos = efeitos_atuais
                            narracao = await narrar_ambiente(jogador.nome, message.text, sala_atual.descricao_visual)
                            return await message.answer(f"{narracao}\n\n🏃 <b>Levantaste-te!</b> Já não estás Caído no chão.", parse_mode="HTML")

                    atr = "STR" if any(p in texto_limpo_acao for p in ["empurrar", "agarrar", "derrubar", "forca", "força", "desarmar"]) else "DEX"
                    mod_base = jogador.mod_str if atr == "STR" else jogador.mod_dex
                    total = random.randint(1, 20) + mod_base + jogador.proficiencia
                    narracao = await narrar_ambiente(jogador.nome, message.text, sala_atual.descricao_visual)
                    
                    if total >= 14:
                        if "Agarrado" in efeitos_atuais:
                            efeitos_atuais.remove("Agarrado")
                            jogador.status_efeitos = efeitos_atuais
                            return await message.answer(f"{narracao}\n\n🔓 <b>Manobra Bem Sucedida! (Teste {atr}: {total})</b>\nConseguiste libertar-te com sucesso! Já não estás Agarrado.", parse_mode="HTML")

                        if campanha.em_combate:
                            estado_campanha = dict(campanha.estado_salas or {})
                            estado_campanha["inimigo_debilidade"] = True
                            campanha.estado_salas = estado_campanha
                            await message.answer(f"{narracao}\n\n⚔️ <b>Manobra Bem Sucedida! (Teste {atr}: {total})</b>\nDeixaste o inimigo vulnerável! O próximo ataque do grupo terá Vantagem.", parse_mode="HTML")
                        else:
                            await message.answer(f"{narracao}\n\n🤸 <b>Manobra Sucesso! (Teste {atr}: {total})</b>\nFizeste uma demonstração formidável de destreza ou força no ambiente.", parse_mode="HTML")
                    else:
                        await message.answer(f"{narracao}\n\n❌ <b>Manobra Falhou (Teste {atr}: {total}).</b>\nO teu alvo previu o movimento e bloqueou a tua tentativa, ou escorregaste.", parse_mode="HTML")

                elif "INTERACAO_OBJETO" in intencao or "PEGAR" in intencao or "USAR_ITEM" in intencao or any(p in texto_limpo_acao for p in ["abrir", "vasculhar", "procurar", "investigar", "destrancar", "desarmar", "saquear", "loot"]):
                    
                    if any(p in texto_limpo_acao for p in ["sala", "chão", "tudo", "chao", "vasculhar", "procurar"]):
                        if hasattr(sala_atual, 'loot_fixo') and sala_atual.loot_fixo and len(sala_atual.loot_fixo) > 0:
                            itens_encontrados = sala_atual.loot_fixo
                            itens_reais = adicionar_ao_inventario(jogador, itens_encontrados)
                            sala_atual.loot_fixo = [] 
                            lista = ", ".join(itens_reais) if itens_reais else "Moedas de Ouro"
                            narracao = await narrar_ambiente(jogador.nome, message.text, sala_atual.descricao_visual)
                            return await message.answer(f"{narracao}\n\n👀 <b>Encontraste algo escondido na sala!</b>\n🎁 <b>Saque:</b> {lista}\n{resumo_status(jogador)}", parse_mode="HTML")

                    interativos_ativos = db.query(Interativo).filter(Interativo.cod_sala == sala_atual.cod_sala, Interativo.ativo == True).all()
                    interagiu = False
                    
                    for obj in interativos_ativos:
                        if obj.tipo.lower() in texto_min or any(p in texto_min for p in obj.nome.lower().split()):
                            interagiu = True
                            mod = getattr(jogador, f"mod_{obj.atributo_teste.lower()}", 0)
                            
                            bonus_prof = 0
                            pericias = BACKGROUND_SKILLS.get(jogador.background, [])
                            if obj.atributo_teste == "DEX" and "Furtividade" in pericias: bonus_prof = jogador.proficiencia
                            if obj.atributo_teste == "INT" and "Arcanismo" in pericias: bonus_prof = jogador.proficiencia
                            
                            total = random.randint(1, 20) + mod + bonus_prof
                            narracao = await narrar_ambiente(jogador.nome, message.text, f"{sala_atual.descricao_visual}. Alvo da ação: {obj.nome} - {obj.descricao}")

                            if total >= obj.cd_teste:
                                obj.ativo = False
                                recompensa_lista = []
                                if obj.tipo == "bau":
                                    recompensa_lista = obj.recompensa if obj.recompensa else gerar_loot_bau(jogador.nivel)
                                elif obj.tipo == "armadilha":
                                    recompensa_lista = obj.recompensa 
                                    
                                if recompensa_lista:
                                    itens_reais = adicionar_ao_inventario(jogador, recompensa_lista)
                                    lista_str = ", ".join(itens_reais) if itens_reais else "Ouro recolhido"
                                    msg_sucesso = f"✅ <b>Teste de {obj.atributo_teste} [{total}] vs CD {obj.cd_teste}</b>\nDesbloqueaste/Desarmaste <b>{obj.nome}</b> com sucesso!\n🎁 <b>Saque:</b> {lista_str}"
                                else:
                                    msg_sucesso = f"✅ <b>Teste de {obj.atributo_teste} [{total}] vs CD {obj.cd_teste}</b>\nSuperaste <b>{obj.nome}</b> com sucesso!"
                                    
                                return await message.answer(f"{narracao}\n\n{msg_sucesso}\n{resumo_status(jogador)}", parse_mode="HTML")
                            else:
                                if obj.dano_falha > 0:
                                    jogador.hp_atual -= obj.dano_falha
                                    if obj.tipo == "armadilha": obj.ativo = False 
                                    msg_falha = f"❌ <b>Teste de {obj.atributo_teste} [{total}] vs CD {obj.cd_teste}</b>\nFalhaste e acionaste <b>{obj.nome}</b>!\n🩸 Sofres {obj.dano_falha} de dano!"
                                    return await message.answer(f"{narracao}\n\n{msg_falha}\n{resumo_status(jogador)}", parse_mode="HTML")
                                else:
                                    msg_falha = f"❌ <b>Teste de {obj.atributo_teste} [{total}] vs CD {obj.cd_teste}</b>\nNão conseguiste lidar com <b>{obj.nome}</b>."
                                    return await message.answer(f"{narracao}\n\n{msg_falha}\n{resumo_status(jogador)}", parse_mode="HTML")
                    
                    if not interagiu:
                        narracao = await narrar_ambiente(jogador.nome, message.text, sala_atual.descricao_visual)
                        await message.answer(f"{narracao}\n\n⚠️ <i>Não encontraste nada de útil para interagir diretamente.</i>\n{resumo_status(jogador)}", parse_mode="HTML")
                        return

                elif "AJUDAR" in intencao:
                    aliados = db.query(Jogador).filter(
                        Jogador.party_id == jogador.party_id,
                        Jogador.cena_atual == campanha.cena_atual,
                        Jogador.hp_atual > 0,
                        Jogador.telefone != user_id
                    ).all()

                    if not aliados:
                        await message.answer("🤝 Não há aliados na sala para ajudar.")
                        return

                    alvo = aliados[0] 
                    efeitos = list(alvo.status_efeitos or [])
                    if "Ajudado" not in efeitos:
                        efeitos.append("Ajudado")
                    alvo.status_efeitos = efeitos

                    await message.answer(
                        f"🤝 <b>{jogador.nome}</b> posiciona-se para dar suporte a <b>{alvo.nome}</b>!\n"
                        f"O próximo ataque de {alvo.nome} terá <u>vantagem</u>.",
                        parse_mode="HTML"
                    )
                    return

                elif "COMBATE" in intencao or "MAGIA" in intencao:
                    encontros = db.query(Encontro).filter(Encontro.cod_sala == campanha.cena_atual).all()
                    estado_campanha = dict(campanha.estado_salas) if campanha.estado_salas else {}
                    encontros_vivos = [e for e in encontros if not estado_campanha.get(f"derrotado_{e.id}")]
                    encontro = encontros_vivos[0] if encontros_vivos else None

                    if not encontro:
                        tipo_alvo, obj_alvo = resolver_alvo(message.text, [], objetos_destrutiveis)
                    else:
                        tipo_alvo, obj_alvo = "inimigo", None

                    if tipo_alvo == "objeto_destrutivel" and obj_alvo:
                        res_obj = processar_ataque_objeto(jogador, obj_alvo)
                        narracao = await narrar_combate(
                            jogador.nome, message.text,
                            f"Alvo: {obj_alvo.nome} (HP {obj_alvo.hp_atual}/{obj_alvo.hp_max}, CA {obj_alvo.ca})",
                            sala_atual.descricao_visual
                        )

                        if res_obj.quebrou_por_forca:
                            obj_alvo.hp_atual = 0
                            obj_alvo.ativo = False
                            msg_destr = (f"{narracao}\n\n"
                                         f"💪 <b>Arrombado pela Força Pura!</b>\n"
                                         f"O teu STR ({jogador.str_val}) supera o limiar de {obj_alvo.break_threshold}. "
                                         f"<b>{obj_alvo.nome}</b> cede com um estrondo!")
                        elif not res_obj.acertou:
                            msg_destr = (f"{narracao}\n\n"
                                         f"🎲 d20={getattr(res_obj, 'detalhes_d20', f'[{res_obj.d20}]')}+{jogador.modificador_ataque}={res_obj.total_ataque} vs CA {obj_alvo.ca} ❌\n"
                                         f"O golpe raspou em <b>{obj_alvo.nome}</b> sem causar dano significativo.\n"
                                         f"🏚️ HP do objeto: {obj_alvo.hp_atual}/{obj_alvo.hp_max}")
                        else:
                            obj_alvo.hp_atual = res_obj.hp_restante
                            if res_obj.destruido:
                                obj_alvo.ativo = False
                                loot_obj = getattr(obj_alvo, 'recompensa_ao_destruir', []) or []
                                texto_loot = ""
                                if loot_obj:
                                    itens_reais = adicionar_ao_inventario(jogador, loot_obj)
                                    if itens_reais:
                                        texto_loot = f"\n🎁 <b>Saque liberado:</b> {', '.join(itens_reais)}"
                                msg_destr = (f"{narracao}\n\n"
                                             f"🎲 d20={getattr(res_obj, 'detalhes_d20', f'[{res_obj.d20}]')}+{jogador.modificador_ataque}={res_obj.total_ataque} vs CA {obj_alvo.ca} "
                                             f"{'💥 CRÍTICO!' if res_obj.critico else '✅'}\n"
                                             f"💥 Dano: <b>{res_obj.dano}</b>\n"
                                             f"🔨 <b>{obj_alvo.nome} foi destruído!</b>{texto_loot}")
                            else:
                                msg_destr = (f"{narracao}\n\n"
                                             f"🎲 d20={getattr(res_obj, 'detalhes_d20', f'[{res_obj.d20}]')}+{jogador.modificador_ataque}={res_obj.total_ataque} vs CA {obj_alvo.ca} "
                                             f"{'💥 CRÍTICO!' if res_obj.critico else '✅'}\n"
                                             f"💥 Dano: <b>{res_obj.dano}</b>\n"
                                             f"🏚️ <b>{obj_alvo.nome}</b> HP: {res_obj.hp_restante}/{obj_alvo.hp_max}")

                        return await message.answer(f"{msg_destr}\n{resumo_status(jogador)}", parse_mode="HTML")

                    if encontro:
                        inimigo = db.query(Inimigo).filter(Inimigo.nome == encontro.nome_inimigo).first()
                        
                        if not inimigo:
                            await message.answer(f"⚠️ <b>Distorção Mágica:</b> O monstro '<b>{encontro.nome_inimigo}</b>' existe na sala, mas as suas estatísticas não estão no Bestiário! Pede ao Mestre para o adicionar ao banco de dados.", parse_mode="HTML")
                            return
                        
                        chave_hp = f"hp_{encontro.id}"
                        hp_max_inimigo = inimigo.hp_max if inimigo.hp_max is not None else 10
                        hp_grupo = estado_campanha.get(chave_hp, hp_max_inimigo * encontro.quantidade)

                        ca_alvo = inimigo.ca if inimigo.ca is not None else 10
                        is_durnn_furia = False
                        if getattr(inimigo, 'is_boss', False) or "Durnn" in inimigo.nome:
                            if hp_grupo <= (hp_max_inimigo / 2) and hp_grupo > 0:
                                is_durnn_furia = True
                                ca_alvo = max(10, ca_alvo - 2)
                                
                        is_gulthias = "árvore" in inimigo.nome.lower() or "arvore" in inimigo.nome.lower() or "gulthias" in inimigo.nome.lower()
                        vulneravel_fogo = False
                        if is_gulthias and "MAGIA" in intencao and any(p in texto_min for p in ["fogo", "ardente", "chamas", "bola"]):
                            vulneravel_fogo = True

                        estado_campanha["ca_alvo"] = ca_alvo
                        campanha.estado_salas = estado_campanha

                        if any(p in texto_min for p in ["esquivar", "defender", "dodge", "defesa total"]):
                            if "Esquivando" not in (jogador.status_efeitos or []):
                                efeitos = list(jogador.status_efeitos or [])
                                efeitos.append("Esquivando")
                                jogador.status_efeitos = efeitos
                                await message.answer("🛡️ <b>Posição Defensiva!</b> Inimigos terão desvantagem para te acertar até teu próximo turno.", parse_mode="HTML")
                                return
                            else:
                                await message.answer("⚠️ Já estás em posição defensiva.", parse_mode="HTML")
                                return

                        if any(p in texto_min for p in ["preparar", "mirar", "aguardar", "ready"]):
                            jogador.acao_preparada = {
                                "tipo": "ataque",
                                "gatilho": texto_min.replace("preparar", "").replace("mirar", "").replace("aguardar", "").strip(),
                                "dano_base": jogador.dano_dado,
                                "mod_dano": jogador.mod_dano
                            }
                            await message.answer(f"⏳ <b>Ação Preparada:</b> atacar quando algo '{jogador.acao_preparada['gatilho']}' acontecer.", parse_mode="HTML")
                            return

                        if "MAGIA" in intencao:
                            if jogador.slots_magia <= 0: return await message.answer("✨ <b>Sem Usos de Magia ou Habilidade!</b>", parse_mode="HTML")
                            jogador.slots_magia -= 1
                            mod_original = jogador.modificador_ataque
                            dano_arma_original = jogador.dano_dado
                            _cls = jogador.classe.lower()
                            jogador.modificador_ataque = (jogador.mod_int if _cls == "mago" else jogador.mod_cha) + jogador.proficiencia
                            chave_classe = next((c for c in MAGIAS_POR_CLASSE.keys() if c == _cls), "default")
                            magia_escolhida = MAGIAS_POR_CLASSE[chave_classe].copy()
                            jogador.dano_dado = magia_escolhida["dano"]

                        # Flags de Habilidades Ativas
                        dano_extra_flag = 0
                        if hasattr(jogador, '_smite') and jogador._smite:
                            dados_smite = min(5, 2 + (jogador.nivel // 4))
                            dano_extra_flag += sum(random.randint(1, 8) for _ in range(dados_smite))
                            jogador._smite = False
                        if hasattr(jogador, '_formaselvagem') and jogador._formaselvagem:
                            dano_extra_flag += sum(random.randint(1, 6) for _ in range(2))
                            jogador._formaselvagem = False
                        if hasattr(jogador, '_furia') and jogador._furia:
                            bonus_furia = 2
                            if jogador.nivel >= 16: bonus_furia = 4
                            elif jogador.nivel >= 9: bonus_furia = 3
                            dano_extra_flag += bonus_furia
                            jogador._furia = False

                        _cls_kw = jogador.classe.lower()
                        kws_classe = KEYWORDS_POR_CLASSE.get(_cls_kw, {})
                        mod_keyword = {}
                        keyword_feature_msg = ""
                        for kw_texto, kw_efeitos in kws_classe.items():
                            if kw_texto in texto_min:
                                mod_keyword = kw_efeitos
                                keyword_feature_msg = f"\n⚡ <i>{kw_efeitos.get('texto', '')}</i>"
                                break

                        mod_atq_original = jogador.modificador_ataque
                        if mod_keyword.get("bonus_ataque"):
                            jogador.modificador_ataque += mod_keyword["bonus_ataque"]

                        bonus_ca_kw = mod_keyword.get("bonus_ca", 0)

                        vantagem_ajuda = "Ajudado" in (jogador.status_efeitos or [])
                        desvantagem_caido = "Caído" in (jogador.status_efeitos or [])
                        
                        tem_vantagem = mod_keyword.get("vantagem") or estado_campanha.get("inimigo_debilidade") or vantagem_ajuda
                        tem_desvantagem = desvantagem_caido
                        
                        if tem_vantagem and not tem_desvantagem:
                            res1 = processar_ataque_fisico(jogador, ca_alvo)
                            res2 = processar_ataque_fisico(jogador, ca_alvo)
                            res = res1 if res1.total_ataque >= res2.total_ataque else res2
                            _keyword_inimigo_vantagem = mod_keyword.get("vantagem", False)
                            if estado_campanha.get("inimigo_debilidade"):
                                keyword_feature_msg += "\n🎯 <i>Aproveitaste a falha na defesa inimiga (Vantagem)!</i>"
                                estado_campanha["inimigo_debilidade"] = False
                            if vantagem_ajuda:
                                keyword_feature_msg += "\n🤝 <i>O teu aliado facilitou o teu ataque (Vantagem)!</i>"
                                efeitos_atuais = list(jogador.status_efeitos or [])
                                if "Ajudado" in efeitos_atuais:
                                    efeitos_atuais.remove("Ajudado")
                                jogador.status_efeitos = efeitos_atuais
                        elif tem_desvantagem and not tem_vantagem:
                            res1 = processar_ataque_fisico(jogador, ca_alvo)
                            res2 = processar_ataque_fisico(jogador, ca_alvo)
                            res = res1 if res1.total_ataque <= res2.total_ataque else res2
                            _keyword_inimigo_vantagem = False
                            if desvantagem_caido:
                                keyword_feature_msg += "\n⚠️ <i>Estás Caído no chão! O teu ataque teve Desvantagem.</i>"
                        else:
                            res = processar_ataque_fisico(jogador, ca_alvo)
                            _keyword_inimigo_vantagem = False

                        jogador.modificador_ataque = mod_atq_original

                        if hasattr(jogador, '_surto') and jogador._surto:
                            res_extra = processar_ataque_fisico(jogador, ca_alvo)
                            if res_extra.acertou:
                                res.dano += res_extra.dano
                            jogador._surto = False

                        if mod_keyword.get("ataque_extra"):
                            res_kw_extra = processar_ataque_fisico(jogador, ca_alvo)
                            if res_kw_extra.acertou:
                                res.dano += res_kw_extra.dano
                                keyword_feature_msg += f" (+{res_kw_extra.dano} extra)"
                        
                        status_msg = ""
                        pode_atacar = True
                        efeitos_atuais = list(jogador.status_efeitos) if jogador.status_efeitos else []
                        dano_veneno = 0
                        
                        if is_durnn_furia:
                            status_msg += f"\n😡 <b>Fúria Sanguinária:</b> Durnn abaixou a guarda, mas ataca com ferocidade letal!"
                        if vulneravel_fogo:
                            status_msg += f"\n🔥 A Árvore Gulthias contorce-se, vulnerável às tuas chamas!"
                        
                        if "Envenenado" in efeitos_atuais:
                            dano_veneno = random.randint(1, 4)
                            jogador.hp_atual -= dano_veneno
                            status_msg += f"\n🤢 <b>Veneno:</b> Sofres {dano_veneno} de dano direto!"
                            
                        if "Atordoado" in efeitos_atuais:
                            pode_atacar = False
                            efeitos_atuais.remove("Atordoado")
                            status_msg += f"\n💫 <b>Atordoado:</b> Ficas tonto e perdes a tua ação neste turno!"
                            jogador.status_efeitos = efeitos_atuais

                        feature_msg = keyword_feature_msg
                        dano_extra_feature = dano_extra_flag
                        resistencia_furia = hasattr(jogador, '_furia') and jogador._furia
                        desvantagem_inimigo = False
                        bonus_ca_temporario = bonus_ca_kw
                        _cls = jogador.classe.lower()
                        
                        if "MAGIA" not in intencao and pode_atacar:
                            if _cls == "paladino" and any(p in texto_min for p in ["destruição", "smite", "divina"]):
                                if jogador.slots_magia > 0:
                                    jogador.slots_magia -= 1
                                    dados_smite = min(5, 2 + (jogador.nivel // 4))
                                    dano_extra_feature += sum(random.randint(1, 8) for _ in range(dados_smite))
                                    feature_msg = f"\n✨ <i>Destruição Divina: +{dados_smite}d8 de dano radiante! (-1 Uso)</i>"
                                else:
                                    feature_msg = f"\n⚠️ <i>Sem Usos de Destruição Divina restantes!</i>"
                            elif _cls == "ladino" and any(p in texto_min for p in ["furtivo", "escondido", "costas", "sorrateiro", "escondo"]):
                                dados_furtivo = math.ceil(jogador.nivel / 2)
                                dano_extra_feature += sum(random.randint(1, 6) for _ in range(dados_furtivo))
                                feature_msg = f"\n🗡️ <i>Ataque Furtivo: +{dano_extra_feature} de dano extra!</i>"
                            elif _cls == "bárbaro" and any(p in texto_min for p in ["fúria", "furia", "enfurecer", "raiva"]):
                                if jogador.slots_magia > 0:
                                    jogador.slots_magia -= 1
                                    bonus_furia = 2
                                    if jogador.nivel >= 16: bonus_furia = 4
                                    elif jogador.nivel >= 9: bonus_furia = 3
                                    dano_extra_feature += bonus_furia
                                    resistencia_furia = True
                                    feature_msg = f"\n😡 <i>Fúria Bárbaro: +{bonus_furia} de dano e Resistência Ativada! (-1 Uso)</i>"
                                else:
                                    feature_msg = f"\n⚠️ <i>Sem Usos de Fúria restantes!</i>"
                            elif _cls == "druida" and any(p in texto_min for p in ["forma selvagem", "urso", "lobo", "fera", "transformo", "viro"]):
                                if jogador.slots_magia > 0:
                                    jogador.slots_magia -= 1
                                    cura_selvagem = random.randint(1, 4) + jogador.nivel
                                    jogador.hp_atual = min(jogador.hp_maximo, jogador.hp_atual + cura_selvagem)
                                    dano_extra_feature += sum(random.randint(1, 6) for _ in range(2))
                                    feature_msg = f"\n🐾 <i>Forma Selvagem: Curou {cura_selvagem} HP e deu +2d6 de dano de garras! (-1 Uso)</i>"
                                else:
                                    feature_msg = f"\n⚠️ <i>Sem Usos de Forma Selvagem restantes!</i>"
                            elif _cls == "guerreiro" and any(p in texto_min for p in ["surto", "ação", "acao", "duas vezes"]):
                                if jogador.slots_magia > 0:
                                    jogador.slots_magia -= 1
                                    res_extra = processar_ataque_fisico(jogador, ca_alvo)
                                    dano_surto = res_extra.dano if res_extra.acertou else 0
                                    res.dano += dano_surto
                                    texto_hit_extra = "Acertou" if res_extra.acertou else "Falhou"
                                    feature_msg = f"\n⚔️ <i>Surto de Ação: Rolou 2º ataque ({texto_hit_extra})! (-1 Uso)</i>"
                                else:
                                    feature_msg = f"\n⚠️ <i>Sem Usos de Surto de Ação restantes!</i>"
                            elif _cls == "guerreiro" and any(p in texto_min for p in ["fôlego", "folego", "curar", "retomar"]):
                                if jogador.slots_magia > 0:
                                    jogador.slots_magia -= 1
                                    cura_guerreiro = random.randint(1, 10) + jogador.nivel
                                    jogador.hp_atual = min(jogador.hp_maximo, jogador.hp_atual + cura_guerreiro)
                                    feature_msg = f"\n⚔️ <i>Retomar o Fôlego: Recuperou {cura_guerreiro} HP! (-1 Uso)</i>"
                                else:
                                    feature_msg = f"\n⚠️ <i>Sem Usos de Retomar o Fôlego restantes!</i>"
                            elif _cls == "patrulheiro" and any(p in texto_min for p in ["marca", "caçador", "cacador"]):
                                dano_extra_feature += random.randint(1, 6)
                                feature_msg = f"\n🏹 <i>Marca do Caçador: +1d6 de dano extra!</i>"
                            elif _cls == "bruxo" and any(p in texto_min for p in ["maldição", "maldicao", "hex"]):
                                dano_extra_feature += random.randint(1, 6)
                                feature_msg = f"\n👁️ <i>Maldição (Hex): +1d6 de dano necrótico!</i>"

                        if "MAGIA" in intencao and pode_atacar:
                            if _cls == "bardo" and any(p in texto_min for p in ["zombaria", "viciosa", "insulto", "insultar"]):
                                desvantagem_inimigo = True
                                feature_msg = f"\n🎸 <i>Zombaria Viciosa: Inimigo atacará com desvantagem! (-1 Uso)</i>"
                            elif _cls == "mago" and any(p in texto_min for p in ["escudo", "arcano"]):
                                bonus_ca_temporario = 5
                                feature_msg = f"\n📖 <i>Escudo Arcano: +5 de CA neste turno! (-1 Uso)</i>"
                            elif _cls == "feiticeiro" and any(p in texto_min for p in ["metamagia", "duplicar"]):
                                res.dano *= 2
                                feature_msg = f"\n🔮 <i>Metamagia ativada: Dano da magia duplicado! (-1 Uso)</i>"
                            elif _cls == "clérigo" and any(p in texto_min for p in ["canalizar", "divindade", "luz"]):
                                cura_clerigo = random.randint(1, 8) + jogador.nivel
                                jogador.hp_atual = min(jogador.hp_maximo, jogador.hp_atual + cura_clerigo)
                                res.dano = math.ceil(res.dano * 1.5)
                                feature_msg = f"\n✝️ <i>Canalizar Divindade: Curou {cura_clerigo} HP e aumentou impacto! (-1 Uso)</i>"

                            jogador.modificador_ataque = mod_original
                            jogador.dano_dado = dano_arma_original
                            if res.acertou and magia_escolhida["aoe"]: res.dano *= min(max(1, math.ceil(hp_grupo / hp_max_inimigo)), 3)

                        ini_jogador = random.randint(1, 20) + jogador.mod_dex
                        ini_inimigo = random.randint(1, 20) + 1
                        jogador_primeiro = ini_jogador >= ini_inimigo
                        texto_iniciativa = f"⚡ <b>INICIATIVA:</b> Herói {ini_jogador} vs Inimigo {ini_inimigo}\n"
                        
                        dano_causado = 0
                        texto_vitoria = ""
                        vitoria = False
                        texto_revide = ""
                        dano_final_revide = 0
                        mortos_no_golpe = 0

                        if campanha.em_combate:
                            botoes = []
                            _cls = jogador.classe.lower()
                            if _cls == "guerreiro" and jogador.slots_magia > 0:
                                botoes.append([InlineKeyboardButton(text="⚔️ Surto de Ação", callback_data="skill_surto")])
                                botoes.append([InlineKeyboardButton(text="❤️ Retomar Fôlego", callback_data="skill_folego")])
                            elif _cls == "paladino" and jogador.slots_magia > 0:
                                botoes.append([InlineKeyboardButton(text="✨ Destruição Divina", callback_data="skill_smite")])
                            elif _cls == "bárbaro" and jogador.slots_magia > 0:
                                botoes.append([InlineKeyboardButton(text="😡 Fúria", callback_data="skill_furia")])
                            elif _cls == "druida" and jogador.slots_magia > 0:
                                botoes.append([InlineKeyboardButton(text="🐾 Forma Selvagem", callback_data="skill_formaselvagem")])
                                
                            if botoes:
                                teclado_skills = InlineKeyboardMarkup(inline_keyboard=botoes)
                                try:
                                    await message.bot.send_message(
                                        chat_id=user_id,
                                        text=f"💡 <b>Suas habilidades disponíveis:</b>",
                                        parse_mode="HTML",
                                        reply_markup=teclado_skills
                                    )
                                except Exception:
                                    pass

                        def aplicar_ataque_jogador():
                            nonlocal hp_grupo, vitoria, texto_vitoria, mortos_no_golpe, dano_causado
                            if not pode_atacar: return
                            
                            if res.acertou:
                                dano_causado = res.dano + dano_extra_feature
                                if vulneravel_fogo: dano_causado *= 2
                                vivos_antes = math.ceil(hp_grupo / hp_max_inimigo) if hp_grupo > 0 else 0
                                hp_grupo -= dano_causado
                                mortos_no_golpe = max(0, vivos_antes - (math.ceil(hp_grupo / hp_max_inimigo) if hp_grupo > 0 else 0))
                                estado_campanha[chave_hp] = hp_grupo
                                
                                if hp_grupo <= 0:
                                    vitoria, estado_campanha[f"derrotado_{encontro.id}"] = True, True
                                    
                                    xp_base = getattr(inimigo, 'xp_recompensa', 50)
                                    xp_total = (xp_base if xp_base is not None else 50) * encontro.quantidade
                                    ouro_base = getattr(inimigo, 'ouro_recompensa', 5)
                                    ouro_total = (ouro_base if ouro_base is not None else 5) * encontro.quantidade
                                    
                                    membros_party = db.query(Jogador).filter(Jogador.party_id == jogador.party_id).all()
                                    qtd_membros = len(membros_party)
                                    xp_por_jogador = max(1, xp_total // qtd_membros)
                                    ouro_por_jogador = max(1, ouro_total // qtd_membros)
                                    
                                    texto_vitoria = f"\n\n🏆 <b>VITÓRIA!</b> O grupo recebe {xp_total} XP e {ouro_total} PO ({xp_por_jogador} XP e {ouro_por_jogador} PO para cada)."
                                    
                                    for membro in membros_party:
                                        membro.xp += xp_por_jogador
                                        membro.gold += ouro_por_jogador
                                        
                                        if membro.xp >= XP_POR_NIVEL.get(membro.nivel + 1, 999999):
                                            membro.nivel += 1
                                            membro.hp_maximo += HP_POR_CLASSE.get(membro.classe, 8) + membro.mod_con
                                            membro.hp_atual = membro.hp_maximo
                                            
                                            membro.slots_magia_max += 1
                                            membro.slots_magia = membro.slots_magia_max
                                            
                                            membro.hit_dice_max = (getattr(membro, 'hit_dice_max', 1)) + 1
                                            membro.hit_dice_atual = membro.hit_dice_max
                                            
                                            nova_proficiencia = 2 + ((membro.nivel - 1) // 4)
                                            if nova_proficiencia > membro.proficiencia:
                                                membro.proficiencia = nova_proficiencia
                                                membro.modificador_ataque = membro.mod_dano + membro.proficiencia
                                                texto_vitoria += f"\n🌟 <b>{membro.nome.upper()} SUBIU PARA O NÍVEL {membro.nivel}!</b> (Proficiência aumentou para +{nova_proficiencia})"
                                            else:
                                                texto_vitoria += f"\n🌟 <b>{membro.nome.upper()} SUBIU PARA O NÍVEL {membro.nivel}!</b>"

                                        if membro.classe.lower() == "monge" and "Desarmado" in getattr(membro, 'arma_equipada', ''):
                                            if membro.nivel >= 17: membro.dano_dado = "1d10"
                                            elif membro.nivel >= 11: membro.dano_dado = "1d8"
                                            elif membro.nivel >= 5: membro.dano_dado = "1d6"
                                            else: membro.dano_dado = "1d4"

                                    loot_combate = []

                                    if getattr(inimigo, 'loot_especial', None):
                                        loot_combate.extend(inimigo.loot_especial)

                                    missoes_ativas = db.query(Missao).filter(
                                        Missao.jogador_telefone == user_id,
                                        Missao.concluida == False
                                    ).all()
                                    itens_quest_garantidos = []
                                    for missao_ativa in missoes_ativas:
                                        if not missao_ativa.objetivo_item:
                                            continue
                                        nome_inimigo_norm = _normalizar(inimigo.nome)
                                        objetivo_norm = _normalizar(missao_ativa.objetivo_item)
                                        if nome_inimigo_norm in objetivo_norm or objetivo_norm in nome_inimigo_norm:
                                            inv_atual = obter_inventario_limpo(jogador.inventario)
                                            qtd_atual = sum(1 for i in inv_atual if missao_ativa.objetivo_item.lower() in i.lower())
                                            faltam = max(0, missao_ativa.objetivo_quantidade - qtd_atual)
                                            if faltam > 0:
                                                itens_quest_garantidos.append(missao_ativa.objetivo_item)
                                    loot_combate.extend(itens_quest_garantidos)

                                    for _ in range(encontro.quantidade):
                                        loot_drop = gerar_loot_inimigo_comum()
                                        if loot_drop: loot_combate.extend(loot_drop)

                                    if "goblin" in inimigo.nome.lower() and random.randint(1, 100) <= 50:
                                        loot_combate.append("Dente de Goblin")
                                    
                                    if loot_combate:
                                        itens_reais = adicionar_ao_inventario(jogador, loot_combate)
                                        if itens_reais:
                                            texto_vitoria += f"\n🎁 <b>Saque (Recolhido por {jogador.nome}):</b> {', '.join(itens_reais)}"
                                    
                                    texto_vitoria += f"\n\n{texto_saidas(sala_atual)}"

                        if not vitoria:
                            hp_total_atual = hp_grupo
                            hp_total_max = hp_max_inimigo * encontro.quantidade

                            if hp_total_max > 0 and (hp_total_atual / hp_total_max) <= 0.20:
                                boss_presente = getattr(inimigo, 'is_boss', False)
                                if not boss_presente:
                                    vitoria = True
                                    estado_campanha[f"derrotado_{encontro.id}"] = True
                                    campanha.em_combate = False

                                    texto_vitoria = (
                                        f"\n\n🏳️ <b>QUEBRA DE MORAL!</b>\n"
                                        f"Os inimigos sobreviventes, gravemente feridos e aterrorizados "
                                        f"com a vossa força, largam as armas e fogem pelas sombras da masmorra!"
                                    )

                                    xp_base = getattr(inimigo, 'xp_recompensa', 50)
                                    xp_total = (xp_base if xp_base is not None else 50) * encontro.quantidade
                                    ouro_base = getattr(inimigo, 'ouro_recompensa', 5)
                                    ouro_total = (ouro_base if ouro_base is not None else 5) * encontro.quantidade

                                    membros_party = db.query(Jogador).filter(Jogador.party_id == jogador.party_id).all()
                                    qtd_membros = len(membros_party)
                                    xp_por_jogador = max(1, xp_total // qtd_membros)
                                    ouro_por_jogador = max(1, ouro_total // qtd_membros)

                                    texto_vitoria += f"\n🏆 O grupo recebe {xp_total} XP e {ouro_total} PO ({xp_por_jogador} XP e {ouro_por_jogador} PO para cada)."

                                    for membro in membros_party:
                                        membro.xp += xp_por_jogador
                                        membro.gold += ouro_por_jogador

                                        if membro.xp >= XP_POR_NIVEL.get(membro.nivel + 1, 999999):
                                            membro.nivel += 1
                                            membro.hp_maximo += HP_POR_CLASSE.get(membro.classe, 8) + membro.mod_con
                                            membro.hp_atual = membro.hp_maximo
                                            membro.slots_magia_max += 1
                                            membro.slots_magia = membro.slots_magia_max
                                            membro.hit_dice_max = (getattr(membro, 'hit_dice_max', 1)) + 1
                                            membro.hit_dice_atual = membro.hit_dice_max

                                            nova_proficiencia = 2 + ((membro.nivel - 1) // 4)
                                            if nova_proficiencia > membro.proficiencia:
                                                membro.proficiencia = nova_proficiencia
                                                membro.modificador_ataque = membro.mod_dano + membro.proficiencia
                                                texto_vitoria += f"\n🌟 <b>{membro.nome.upper()} SUBIU PARA O NÍVEL {membro.nivel}!</b>"
                                            else:
                                                texto_vitoria += f"\n🌟 <b>{membro.nome.upper()} SUBIU PARA O NÍVEL {membro.nivel}!</b>"

                        def aplicar_ataque_inimigo():
                            nonlocal texto_revide, dano_final_revide, hp_grupo
                            vivos_agora = math.ceil(hp_grupo / hp_max_inimigo) if hp_grupo > 0 else 0
                            if vivos_agora == 0: return

                            if hasattr(Jogador, 'acao_preparada'):
                                for membro in db.query(Jogador).filter(Jogador.party_id == jogador.party_id, Jogador.acao_preparada != None).all():
                                    prep = membro.acao_preparada
                                    if prep["tipo"] == "ataque":
                                        dano_original = membro.mod_dano
                                        membro.mod_dano = prep.get("mod_dano", 0)
                                        res_prep = processar_ataque_fisico(membro, ca_alvo)
                                        membro.mod_dano = dano_original
                                        if res_prep.acertou:
                                            texto_revide += f"\n💥 <b>{membro.nome}</b> ataca com ação preparada! Causa {res_prep.dano} de dano."
                                            hp_grupo -= res_prep.dano
                                    membro.acao_preparada = None

                            jogadores_vivos = db.query(Jogador).filter(
                                Jogador.party_id == jogador.party_id,
                                Jogador.hp_atual > 0,
                                Jogador.cena_atual == campanha.cena_atual
                            ).count()

                            limite_ataques = jogadores_vivos + (getattr(encontro, 'multiplicador_ameaca', 1) or 1)
                            atacantes = min(vivos_agora, limite_ataques)

                            mod_inimigo = int(str(inimigo.ataque).replace('+', '')) if '+' in str(inimigo.ataque) else 0
                            texto_revide = f"\n\n⚠️ <b>ATAQUE INIMIGO: {atacantes}x {inimigo.nome} atacam!</b>"
                            if vivos_agora > atacantes: 
                                texto_revide += f" (De {vivos_agora} vivos)\n"
                            else: 
                                texto_revide += "\n"
                            acertos_totais = 0
                            
                            alvo_esquivando = "Esquivando" in (jogador.status_efeitos or [])
                            alvo_cobertura = "Cobertura" in (jogador.status_efeitos or [])
                            alvo_caido = "Caído" in (jogador.status_efeitos or [])
                            inimigo_com_vantagem = _keyword_inimigo_vantagem
                            
                            for i in range(atacantes):
                                d20_inimigo = random.randint(1, 20)
                                if is_durnn_furia: d20_inimigo = max(d20_inimigo, random.randint(1, 20))
                                if inimigo_com_vantagem: d20_inimigo = max(d20_inimigo, random.randint(1, 20))
                                if alvo_caido: d20_inimigo = max(d20_inimigo, random.randint(1, 20))
                                if desvantagem_inimigo: d20_inimigo = min(d20_inimigo, random.randint(1, 20))
                                if alvo_esquivando: d20_inimigo = min(d20_inimigo, random.randint(1, 20))
                                
                                ca_final_jogador = jogador.modificador_defesa + bonus_ca_temporario + (2 if alvo_cobertura else 0)
                                
                                if d20_inimigo + mod_inimigo >= ca_final_jogador or d20_inimigo == 20:
                                    acertos_totais += 1
                                    dano_base = random.randint(1, 4)
                                    if is_durnn_furia: dano_base += 2
                                    if d20_inimigo == 20: dano_base *= 2
                                    dano_final_revide += dano_base
                                    texto_revide += f"🗡️ Atk {i+1}: Hit ({dano_base} dano)\n"
                                else:
                                    texto_revide += f"💨 Atk {i+1}: Miss\n"

                            if acertos_totais > 0:
                                if resistencia_furia:
                                    dano_final_revide = math.floor(dano_final_revide / 2)
                                    texto_revide += f"🛡️ <i>A tua Fúria reduziu o dano sofrido pela metade!</i>\n"
                                texto_revide += f"🩸 <b>Dano total recebido: {dano_final_revide}</b>"
                                
                                if random.randint(1, 100) <= 20 and "Envenenado" not in (jogador.status_efeitos or []):
                                    if any(n in inimigo.nome.lower() for n in ["rato", "aranha", "cobra", "troll", "goblin"]):
                                        efeitos_atuais = list(jogador.status_efeitos or [])
                                        efeitos_atuais.append("Envenenado")
                                        jogador.status_efeitos = efeitos_atuais
                                        texto_revide += "\n🤢 <b>Foste Envenenado pelo ataque inimigo!</b>"
                            else:
                                texto_revide += "🛡️ <b>Esquivaste todos os ataques!</b>"
                            jogador.hp_atual -= dano_final_revide

                        if jogador_primeiro:
                            aplicar_ataque_jogador()
                            if not vitoria and jogador.hp_atual > 0: aplicar_ataque_inimigo()
                        else:
                            if jogador.hp_atual > 0: aplicar_ataque_inimigo()
                            if jogador.hp_atual > 0: aplicar_ataque_jogador()

                        if "Esquivando" in (jogador.status_efeitos or []):
                            efeitos = list(jogador.status_efeitos)
                            efeitos.remove("Esquivando")
                            jogador.status_efeitos = efeitos

                        campanha.estado_salas = estado_campanha

                        resumo_turno = (
                            f"Ataque do Herói: {'Acertou' if res.acertou else 'Errou'}. Dano causado: {dano_causado}. "
                            f"Inimigos mortos neste golpe: {mortos_no_golpe}. "
                            f"Revide dos inimigos: Causaram {dano_final_revide} de dano ao herói. "
                            f"Status Final do Herói: {'Morto/Caiu' if jogador.hp_atual <= 0 else 'Sobreviveu'}."
                        )
                        narracao = await narrar_combate(jogador.nome, message.text, resumo_turno, sala_atual.descricao_visual)

                        if jogador.hp_atual <= 0:
                            nome_final = jogador.nome
                            stats = get_or_create_estatisticas(db, user_id)
                            is_fumble = (res.d20 == 1)

                            dano_total_sofrido = dano_final_revide + dano_veneno
                            texto_golpe_letal = f"🩸 <b>{inimigo.nome}</b> desferiu um golpe letal, causando <b>{dano_total_sofrido} de dano</b>!\n\n" if dano_total_sofrido > 0 else f"🩸 O ataque envenenado de <b>{inimigo.nome}</b> foi letal!\n\n"

                            if is_fumble or stats.intervencoes_divinas >= 1:
                                try: registrar_derrota(db, user_id, intervencao_divina=False)
                                except TypeError: pass
                                    
                                db.query(Jogador).filter(Jogador.telefone == user_id).delete()
                                db.query(Campanha).filter(Campanha.host_id == user_id).delete()
                                db.query(Missao).filter(Missao.jogador_telefone == user_id).delete()
                                
                                motivoTexto = "🎲 <b>O d20 rolou 1. Os deuses não salvam tolos.</b>" if is_fumble else "<b>Os deuses já te salvaram uma vez. Desta vez viraram as costas.</b>"
                                
                                return await message.answer(
                                    f"{narracao}\n\n{texto_golpe_letal}💀 <b>{nome_final.upper()} MORREU PERMANENTEMENTE!</b>\n\n{motivoTexto}\n\nUse <b>/criar</b> para recomeçar a tua lenda.", 
                                    parse_mode="HTML", 
                                    reply_markup=ReplyKeyboardRemove()
                                )
                            else:
                                stats.intervencoes_divinas += 1
                                jogador.hp_atual = 1
                                
                                jogador.descanso_curto_disponivel = True
                                jogador.status_efeitos = []

                                classe_str = jogador.classe.lower()
                                penalidade = ""
                                perder_ouro = any(c in classe_str for c in ['guerreiro', 'bárbaro', 'barbaro', 'patrulheiro', 'ranger', 'mago', 'feiticeiro', 'bruxo', 'monge'])
                                perder_item = any(c in classe_str for c in ['ladino', 'bardo', 'mago', 'feiticeiro', 'bruxo', 'monge'])

                                if any(c in classe_str for c in ['clérigo', 'clerigo', 'paladino']):
                                    penalidade = "Sem penalidade — os deuses protegem os seus servos fiéis."
                                else:
                                    if perder_ouro and perder_item: penalidade = "Perdeste metade do teu ouro E um item do inventário."
                                    elif perder_ouro: penalidade = "Perdeste metade do teu ouro enquanto estavas inconsciente."
                                    elif perder_item: penalidade = "Perdeste um item do inventário enquanto estavas inconsciente."

                                ouro_perdido_qnt = 0
                                if perder_ouro:
                                    ouro_antes = jogador.gold
                                    jogador.gold = math.floor(jogador.gold / 2)
                                    ouro_perdido_qnt = ouro_antes - jogador.gold
                                    stats.ouro_perdido_total += ouro_perdido_qnt

                                try: registrar_derrota(db, user_id, intervencao_divina=True, ouro_perdido=ouro_perdido_qnt)
                                except TypeError: registrar_derrota(db, user_id, intervencao_divina=True)

                                item_perdido_nome = ""
                                if perder_item:
                                    inv_linhas = obter_inventario_limpo(jogador.inventario)
                                    if inv_linhas:
                                        item_perdido_nome = random.choice(inv_linhas)
                                        inv_linhas.remove(item_perdido_nome)
                                        jogador.inventario = inv_linhas
                                        penalidade += f" (O item <b>{item_perdido_nome}</b> caiu e sumiu nas trevas.)"
                                
                                msg_morte = f"{narracao}\n\n{texto_golpe_letal}💀 <b>{nome_final.upper()} CAIU EM COMBATE!</b>\n\n<i>{penalidade}</i>\n\nUm brilho divino desce sobre o teu corpo. Acordas de imediato, a cuspir sangue no chão da masmorra, com a batalha a decorrer à tua volta!\n\n❤️ HP: 1/{jogador.hp_maximo}\n⚠️ <i>Esta foi a tua única chance. Levanta-te e luta, ou ordena um recuo!</i>"
                                
                                return await message.answer(msg_morte, parse_mode="HTML", reply_markup=teclado_saidas(sala_atual))

                        linha_ataque = f"🎲 Dados: d20={getattr(res, 'detalhes_d20', f'[{res.d20}]')}+{jogador.modificador_ataque}={res.total_ataque} vs CA {ca_alvo} {'✅' if res.acertou else '❌'}"
                        if "MAGIA" in intencao: linha_ataque = f"{magia_escolhida['icone']} <b>{magia_escolhida['nome']}</b> {'✅' if res.acertou else '❌'}"

                        linha_dano_jogador = ""
                        if res.acertou and (jogador_primeiro or jogador.hp_atual > 0):
                            linha_dano_jogador = f"\n💥 Dano: {dano_causado} (💀 {mortos_no_golpe} eliminado!)" if mortos_no_golpe > 0 else f"\n💥 Dano: {dano_causado}"
                            linha_dano_jogador += feature_msg
                        elif not res.acertou and (jogador_primeiro or jogador.hp_atual > 0):
                            linha_dano_jogador = f"\n💨 Ataque falhou" + feature_msg
                            
                        bloco_jogador = ""
                        if pode_atacar:
                            bloco_jogador = f"{linha_ataque}{linha_dano_jogador}" if (jogador_primeiro or jogador.hp_atual > 0) else ""
                        bloco_jogador += status_msg
                        
                        if not vitoria and getattr(jogador, 'estilo_combate', '') == "duas_armas":
                            teclado_sec = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="⚔️ Ataque Secundário (sem bónus de dano)", callback_data="ataque_secundario")]
                            ])
                            await message.answer("💨 Podes usar tua ação bônus para um ataque secundário!", reply_markup=teclado_sec)
                        
                        if jogador_primeiro:
                            msg_combate = f"{narracao}\n\n━━━━━━━━━━━━━━━━\n{texto_iniciativa}\n{bloco_jogador}{texto_revide}{texto_vitoria}\n\n❤️ {jogador.nome}: {jogador.hp_atual}/{jogador.hp_maximo} HP\n━━━━━━━━━━━━━━━━"
                        else:
                            msg_combate = f"{narracao}\n\n━━━━━━━━━━━━━━━━\n{texto_iniciativa}{texto_revide}\n\n{bloco_jogador}{texto_vitoria}\n\n❤️ {jogador.nome}: {jogador.hp_atual}/{jogador.hp_maximo} HP\n━━━━━━━━━━━━━━━━"

                        reply_markup_combate = teclado_saidas(sala_atual) if vitoria else None
                        await message.answer(msg_combate, parse_mode="HTML", reply_markup=reply_markup_combate)
                    else:
                        narracao = await narrar_ambiente(jogador.nome, message.text, sala_atual.descricao_visual)
                        await message.answer(f"{narracao}\n\n⚠️ <i>Não há inimigos nem alvos destrutíveis nesta sala.</i>\n{resumo_status(jogador)}", parse_mode="HTML")

                elif "DESCANSO" in intencao or any(p in message.text.lower() for p in ["descansar", "descanso", "curar feridas", "dormir"]):
                    campanha_desc = db.query(Campanha).filter(Campanha.party_id == jogador.party_id).first() if getattr(jogador, 'party_id', None) else None
                    if campanha_desc and campanha_desc.cena_atual != "carvalhal":
                        if jogador.hit_dice_atual > 0:
                            jogador.hit_dice_atual -= 1
                            cura = max(1, (jogador.hp_maximo // 4) + jogador.mod_con)
                            jogador.hp_atual = min(jogador.hp_maximo, jogador.hp_atual + cura)
                            if jogador.classe.lower() == "guerreiro":
                                jogador.slots_magia = min(jogador.slots_magia_max, jogador.slots_magia + 1)
                            await message.answer(f"🏕️ <b>Descanso Curto:</b> Curaste {cura} HP e recuperaste fôlego. Hit Dice: {jogador.hit_dice_atual}/{jogador.hit_dice_max}.\n{resumo_status(jogador)}", parse_mode="HTML")
                        else:
                            await message.answer("⚠️ <b>Exausto!</b> Não tens mais Hit Dice (Dados de Vida) para gastar! Precisas de regressar à Vila de Carvalhal para um Descanso Longo.", parse_mode="HTML")
                    else:
                        jogador.hp_atual = jogador.hp_maximo
                        jogador.slots_magia = jogador.slots_magia_max
                        jogador.hit_dice_atual = getattr(jogador, 'hit_dice_max', 1)
                        jogador.status_efeitos = []
                        await message.answer(f"🛌 <b>Descanso Longo na Vila.</b>\nHP, Magia, Habilidades e Hit Dice totalmente restaurados. Efeitos curados.\n{resumo_status(jogador)}", parse_mode="HTML")

                elif "TESTE" in intencao or "rolar" in message.text.lower():
                    atr = await decidir_atributo_teste(message.text)
                    mod_base = getattr(jogador, f"mod_{atr.lower()}", 0)
                    
                    pericias_do_jogador = BACKGROUND_SKILLS.get(jogador.background, [])
                    texto_teste = message.text.lower()
                    
                    texto_limpo = unicodedata.normalize('NFKD', texto_teste).encode('ASCII', 'ignore').decode('utf-8')
                    
                    usou_pericia = False
                    pericia_usada = ""
                    
                    for p in pericias_do_jogador:
                        p_limpa = unicodedata.normalize('NFKD', p).encode('ASCII', 'ignore').decode('utf-8').lower()
                        if p_limpa in texto_limpo:
                            usou_pericia = True
                            pericia_usada = p
                            break
                    
                    if usou_pericia:
                        mod_final = mod_base + jogador.proficiencia
                        msg_extra = f" (+{jogador.proficiencia} Prof. em {pericia_usada})"
                    else:
                        mod_final = mod_base
                        msg_extra = ""
                    
                    total = random.randint(1, 20) + mod_final
                    
                    narracao = await narrar_ambiente(jogador.nome, message.text, sala_atual.descricao_visual)
                    await message.answer(f"{narracao}\n\n🎲 Teste {atr}: {total}{msg_extra}", parse_mode="HTML")
                    
                else:
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