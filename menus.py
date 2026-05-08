import math
import random
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import get_db_session
from models import Jogador, Campanha, Missao
from ui_utils import (
    obter_inventario_limpo, formatar_inventario_para_display,
    LOJA_CARVALHAL, ARMAS_DB, resumo_status, BACKGROUND_SKILLS, XP_POR_NIVEL
)
from stats_manager import (
    get_or_create_estatisticas, get_rank_jogador, get_ultimas_partidas,
    calcular_taxa_sucesso, calcular_taxa_sucesso_testes
)

router = Router()

@router.message(Command("equipar"))
async def equipar_handler(message: types.Message):
    item_nome = message.text.replace("/equipar", "").strip()
    if not item_nome:
        return await message.answer("⚠️ Digita o nome do item que queres equipar. Ex: <code>/equipar Espada Longa</code> ou <code>/equipar Cota de Malha</code>", parse_mode="HTML")

    user_id = str(message.from_user.id)
    with get_db_session() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == user_id).first()
        if not jogador: return await message.answer("⚠️ Cria um personagem primeiro.")

        inv_limpo = obter_inventario_limpo(jogador.inventario)
        
        if item_nome.lower() in ["desarmado", "soco", "punhos"]:
            item_no_inv = "Desarmado"
        else:
            item_no_inv = next((i for i in inv_limpo if item_nome.lower() in i.lower()), None)
        
        if not item_no_inv:
            return await message.answer(f"❌ Não tens <b>{item_nome}</b> no teu inventário.", parse_mode="HTML")

        arma_dados = None
        nome_oficial_arma = None
        for nome, dados in ARMAS_DB.items():
            if item_nome.lower() in nome.lower():
                arma_dados = dados
                nome_oficial_arma = nome
                break

        armadura_dados = None
        nome_oficial_armadura = None
        for nome, dados in LOJA_CARVALHAL.items():
            if item_nome.lower() in nome.lower() and dados.get("tipo") in ["armadura"]:
                armadura_dados = dados
                nome_oficial_armadura = nome
                break

        if not arma_dados and not armadura_dados:
            return await message.answer(f"❌ <b>{item_no_inv}</b> não é uma arma ou armadura equipável.", parse_mode="HTML")

        resposta = ""

        if arma_dados:
            if jogador.classe.lower() == "monge" and item_no_inv == "Desarmado":
                if jogador.nivel >= 17: jogador.dano_dado = "1d10"
                elif jogador.nivel >= 11: jogador.dano_dado = "1d8"
                elif jogador.nivel >= 5: jogador.dano_dado = "1d6"
                else: jogador.dano_dado = "1d4"
                atr = "DEX"
                nome_oficial_arma = "Artes Marciais (Desarmado)"
            else:
                jogador.dano_dado = arma_dados["dano"]
                atr = arma_dados["atributo"]
            
            mod_escolhido = 0
            tipo_atr = ""
            if atr == "STR":
                mod_escolhido = jogador.mod_str
                tipo_atr = "Força"
            elif atr == "DEX":
                mod_escolhido = jogador.mod_dex
                tipo_atr = "Destreza"
            elif atr == "FINESSE":
                if jogador.mod_dex >= jogador.mod_str:
                    mod_escolhido = jogador.mod_dex
                    tipo_atr = "Destreza (Acuidade)"
                else:
                    mod_escolhido = jogador.mod_str
                    tipo_atr = "Força (Acuidade)"

            jogador.mod_dano = mod_escolhido
            jogador.modificador_ataque = mod_escolhido + jogador.proficiencia
            
            if hasattr(jogador, 'arma_equipada'):
                jogador.arma_equipada = nome_oficial_arma
            
            resposta = (f"⚔️ <b>{nome_oficial_arma} Equipada!</b>\n"
                        f"🎲 Dano: <b>{jogador.dano_dado}</b>\n"
                        f"🎯 Bónus de Ataque: <b>+{jogador.modificador_ataque}</b> ({tipo_atr})")

        elif armadura_dados:
            subtipo = armadura_dados.get("subtipo")
            ca_base = armadura_dados.get("ca_base", 10)
            
            if subtipo == "escudo":
                jogador.modificador_defesa += ca_base
                resposta = f"🛡️ <b>{nome_oficial_armadura} Equipado!</b>\nA tua CA aumentou em +{ca_base} (Total: {jogador.modificador_defesa})."
                
                if hasattr(jogador, 'armadura_equipada') and "Escudo" not in str(jogador.armadura_equipada):
                    jogador.armadura_equipada = f"{jogador.armadura_equipada} & Escudo"
            else:
                if subtipo == "leve":
                    nova_ca = ca_base + jogador.mod_dex
                elif subtipo == "media":
                    nova_ca = ca_base + min(2, jogador.mod_dex)
                elif subtipo == "pesada":
                    nova_ca = ca_base
                else:
                    nova_ca = ca_base
                
                if any("Escudo" in item for item in inv_limpo):
                    nova_ca += 2
                    nome_oficial_armadura += " & Escudo"
                    
                jogador.modificador_defesa = nova_ca
                if hasattr(jogador, 'armadura_equipada'):
                    jogador.armadura_equipada = nome_oficial_armadura
                    
                resposta = f"🛡️ <b>{nome_oficial_armadura} Vestida!</b>\nA tua nova CA é <b>{jogador.modificador_defesa}</b>."

        await message.answer(resposta, parse_mode="HTML")

@router.message(Command("loja"))
async def loja_interativa_handler(message: types.Message):
    with get_db_session() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == str(message.from_user.id)).first()
        campanha = db.query(Campanha).filter(Campanha.party_id == jogador.party_id).first() if jogador and getattr(jogador, 'party_id', None) else None
        
        if not campanha or not jogador: return await message.answer("⚠️ Cria um personagem e entra numa /party primeiro.")
        if campanha.cena_atual != "carvalhal": return await message.answer("⚠️ Estás no meio de uma masmorra! A loja fica na vila.")
        
        reputacao = (jogador.reputacao or {}).get("carvalhal", 0)
        fator_preco = 1.0
        if reputacao >= 50:
            fator_preco = 0.8
        elif reputacao >= 25:
            fator_preco = 0.9
        
        texto = f"🛒 <b>EMPÓRIO DE CARVALHAL</b>\n💰 <b>Teu Ouro:</b> {jogador.gold} PO\n"
        if fator_preco < 1.0:
            texto += f"⭐ <b>Desconto de Reputação:</b> {int((1-fator_preco)*100)}%\n"
        texto += "<i>Clica no item para comprar:</i>\n"
        
        botoes = []
        for k, v in LOJA_CARVALHAL.items():
            preco_final = max(1, math.floor(v['preco'] * fator_preco))
            item_safe = k[:20].strip()
            icone = "🧪" if v["tipo"] == "pocao" else "⚔️" if v["tipo"] == "arma" else "🛡️"
            botoes.append([InlineKeyboardButton(text=f"{icone} {k} - {preco_final} PO", callback_data=f"buy_{item_safe}")])

        teclado = InlineKeyboardMarkup(inline_keyboard=botoes)
        await message.answer(texto, parse_mode="HTML", reply_markup=teclado)

@router.callback_query(F.data.startswith("buy_"))
async def comprar_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    item_nome_parcial = callback.data.replace("buy_", "")
    
    with get_db_session() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == user_id).first()
        if not jogador: return await callback.answer("⚠️ Erro de jogador.", show_alert=True)
        
        item_encontrado, nome_oficial = None, None
        for k, v in LOJA_CARVALHAL.items():
            if item_nome_parcial.lower() in k.lower():
                item_encontrado, nome_oficial = v, k
                break
                
        if not item_encontrado: return await callback.answer("❌ Item não encontrado na loja.", show_alert=True)
        
        reputacao = (jogador.reputacao or {}).get("carvalhal", 0)
        fator_preco = 1.0
        if reputacao >= 50: fator_preco = 0.8
        elif reputacao >= 25: fator_preco = 0.9
        preco_final = max(1, math.floor(item_encontrado["preco"] * fator_preco))
        
        if jogador.gold < preco_final: return await callback.answer(f"💸 Faltam moedas! Custa {preco_final} PO.", show_alert=True)
        
        jogador.gold -= preco_final
        inv_linhas = obter_inventario_limpo(jogador.inventario)
        inv_linhas.append(nome_oficial)
        jogador.inventario = inv_linhas
        
        await callback.message.edit_text(f"🛍️ <b>Compraste: {nome_oficial}!</b> (-{preco_final} PO)\n💰 Ouro Restante: <b>{jogador.gold} PO</b>\n<i>Usa /inventario para equipar.</i>", parse_mode="HTML")
        await callback.answer(f"Comprado: {nome_oficial}")

@router.message(Command("vender"))
async def vender_interativo_handler(message: types.Message):
    with get_db_session() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == str(message.from_user.id)).first()
        campanha = db.query(Campanha).filter(Campanha.party_id == jogador.party_id).first() if jogador and getattr(jogador, 'party_id', None) else None
        
        if not campanha or campanha.cena_atual != "carvalhal": return await message.answer("⚠️ Só podes vender itens na Vila.")
        
        inv_linhas = obter_inventario_limpo(jogador.inventario)
        if not inv_linhas: return await message.answer("🎒 A tua mochila está vazia.")
        
        texto = f"⚖️ <b>MERCADO DE CARVALHAL</b>\n💰 <b>Teu Ouro:</b> {jogador.gold} PO\n<i>O que desejas vender?</i>\n"
        botoes = []
        itens_unicos = set(inv_linhas)
        
        for item in itens_unicos:
            preco_base = next((v["preco"] for k, v in LOJA_CARVALHAL.items() if k.lower() in item.lower() or item.lower() in k.lower()), 2)
            valor_venda = max(1, math.floor(preco_base / 2))
            qtd = inv_linhas.count(item)
            item_safe = item[:20].strip()
            
            botoes.append([InlineKeyboardButton(text=f"Vender {item} ({qtd}x) - +{valor_venda} PO", callback_data=f"sell_{item_safe}")])

        teclado = InlineKeyboardMarkup(inline_keyboard=botoes)
        await message.answer(texto, parse_mode="HTML", reply_markup=teclado)

@router.callback_query(F.data.startswith("sell_"))
async def vender_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    item_nome_parcial = callback.data.replace("sell_", "")
    
    with get_db_session() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == user_id).first()
        inv_linhas = obter_inventario_limpo(jogador.inventario)
        
        item_para_vender = next((i for i in inv_linhas if item_nome_parcial.lower() in i.lower()), None)
        if not item_para_vender: return await callback.answer("❌ Já não tens este item.", show_alert=True)
        
        preco_base = next((v["preco"] for k, v in LOJA_CARVALHAL.items() if k.lower() in item_para_vender.lower() or item_para_vender.lower() in k.lower()), 2)
        valor_venda = max(1, math.floor(preco_base / 2))
        
        inv_linhas.remove(item_para_vender)
        jogador.inventario = inv_linhas
        jogador.gold += valor_venda
        
        await callback.message.edit_text(f"🤝 <b>Negócio Fechado!</b>\nVendeste <b>{item_para_vender}</b>.\n🪙 +{valor_venda} PO | 💰 Atual: {jogador.gold} PO", parse_mode="HTML")
        await callback.answer(f"Vendido por {valor_venda} PO")

@router.message(Command("inventario"))
async def inventario_handler(message: types.Message):
    with get_db_session() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == str(message.from_user.id)).first()
        if not jogador: return await message.answer("⚠️ Cria um personagem primeiro com /criar.")

        inv_limpo = obter_inventario_limpo(jogador.inventario)
        texto_inventario = formatar_inventario_para_display(inv_limpo)
        
        botoes = []
        itens_unicos = set(inv_limpo)
        
        for item in itens_unicos:
            is_arma = any(item.lower() in k.lower() for k in ARMAS_DB.keys())
            is_armadura = any(item.lower() in k.lower() and v.get("tipo") in ["armadura"] for k, v in LOJA_CARVALHAL.items())
            is_pocao = any(item.lower() in k.lower() and v.get("tipo") == "pocao" for k, v in LOJA_CARVALHAL.items())
            
            item_safe = item[:20].strip() 
            
            if is_arma or is_armadura:
                botoes.append([InlineKeyboardButton(text=f"⚔️ Equipar {item}", callback_data=f"inveq_{item_safe}")])
            elif is_pocao:
                if "antídoto" in item.lower() or "antidoto" in item.lower():
                    botoes.append([InlineKeyboardButton(text=f"🧪 Beber {item}", callback_data=f"invuso_antidoto")])
                else:
                    botoes.append([InlineKeyboardButton(text=f"🧪 Beber {item}", callback_data=f"invuso_pocao")])

        teclado = InlineKeyboardMarkup(inline_keyboard=botoes) if botoes else None

        await message.answer(
            f"🎒 <b>INVENTÁRIO - {jogador.nome}</b>\n━━━━━━━━━━━━━━━━━━━━\n{texto_inventario}\n━━━━━━━━━━━━━━━━━━━━\n💰 <b>Ouro:</b> {jogador.gold} PO", 
            parse_mode="HTML",
            reply_markup=teclado
        )

@router.callback_query(F.data.startswith("inveq_") | F.data.startswith("invuso_"))
async def inventario_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    comando = callback.data
    
    with get_db_session() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == user_id).first()
        if not jogador: return await callback.answer("⚠️ Personagem não encontrado.", show_alert=True)
        
        inv_limpo = obter_inventario_limpo(jogador.inventario)
        
        if comando.startswith("invuso_"):
            tipo_uso = comando.replace("invuso_", "")
            
            if tipo_uso == "antidoto":
                antidoto = next((i for i in inv_limpo if "antídoto" in i.lower() or "antidoto" in i.lower()), None)
                if not antidoto: return await callback.answer("❌ Não tens mais este item!", show_alert=True)
                
                inv_limpo.remove(antidoto)
                jogador.inventario = inv_limpo
                efeitos = list(jogador.status_efeitos) if jogador.status_efeitos else []
                if "Envenenado" in efeitos: efeitos.remove("Envenenado")
                jogador.status_efeitos = efeitos
                
                await callback.message.answer(f"🧪 Bebeste o {antidoto}. O veneno foi neutralizado!\n{resumo_status(jogador)}", parse_mode="HTML")
                await callback.message.delete()
                return await callback.answer()
                
            elif tipo_uso == "pocao":
                pocao = next((i for i in inv_limpo if i in LOJA_CARVALHAL and LOJA_CARVALHAL[i]["tipo"] == "pocao" and "antídoto" not in i.lower()), None)
                if not pocao: return await callback.answer("❌ Não tens mais este item!", show_alert=True)
                
                inv_limpo.remove(pocao)
                jogador.inventario = inv_limpo
                cura = sum(random.randint(1, 4) for _ in range(2)) + 2
                jogador.hp_atual = min(jogador.hp_maximo, jogador.hp_atual + cura)
                
                await callback.message.answer(f"🧪 Bebeste a {pocao} e recuperaste HP!\n{resumo_status(jogador)}", parse_mode="HTML")
                await callback.message.delete()
                return await callback.answer()

        elif comando.startswith("inveq_"):
            item_nome_parcial = comando.replace("inveq_", "")
            item_no_inv = next((i for i in inv_limpo if item_nome_parcial.lower() in i.lower()), None)
            
            if not item_no_inv: return await callback.answer("❌ Não tens mais este item!", show_alert=True)

            arma_dados = None
            nome_oficial_arma = None
            for nome, dados in ARMAS_DB.items():
                if item_no_inv.lower() in nome.lower():
                    arma_dados = dados
                    nome_oficial_arma = nome
                    break

            armadura_dados = None
            nome_oficial_armadura = None
            for nome, dados in LOJA_CARVALHAL.items():
                if item_no_inv.lower() in nome.lower() and dados.get("tipo") in ["armadura"]:
                    armadura_dados = dados
                    nome_oficial_armadura = nome
                    break

            if not arma_dados and not armadura_dados:
                return await callback.answer("❌ Item não equipável.", show_alert=True)

            resposta = ""

            if arma_dados:
                if jogador.classe.lower() == "monge" and item_no_inv == "Desarmado":
                    if jogador.nivel >= 17: jogador.dano_dado = "1d10"
                    elif jogador.nivel >= 11: jogador.dano_dado = "1d8"
                    elif jogador.nivel >= 5: jogador.dano_dado = "1d6"
                    else: jogador.dano_dado = "1d4"
                    atr = "DEX"
                    nome_oficial_arma = "Artes Marciais (Desarmado)"
                else:
                    jogador.dano_dado = arma_dados["dano"]
                    atr = arma_dados["atributo"]
                
                mod_escolhido = 0
                if atr == "STR": mod_escolhido = jogador.mod_str
                elif atr == "DEX": mod_escolhido = jogador.mod_dex
                elif atr == "FINESSE": mod_escolhido = max(jogador.mod_str, jogador.mod_dex)

                jogador.mod_dano = mod_escolhido
                jogador.modificador_ataque = mod_escolhido + jogador.proficiencia
                if hasattr(jogador, 'arma_equipada'): jogador.arma_equipada = nome_oficial_arma
                
                resposta = f"⚔️ <b>{nome_oficial_arma} Equipada!</b>\n🎲 Dano: <b>{jogador.dano_dado}</b>\n🎯 Bónus: <b>+{jogador.modificador_ataque}</b>"

            elif armadura_dados:
                subtipo = armadura_dados.get("subtipo")
                ca_base = armadura_dados.get("ca_base", 10)
                
                if subtipo == "escudo":
                    jogador.modificador_defesa += ca_base
                    if hasattr(jogador, 'armadura_equipada') and "Escudo" not in str(jogador.armadura_equipada):
                        jogador.armadura_equipada = f"{jogador.armadura_equipada} & Escudo"
                else:
                    if subtipo == "leve": nova_ca = ca_base + jogador.mod_dex
                    elif subtipo == "media": nova_ca = ca_base + min(2, jogador.mod_dex)
                    else: nova_ca = ca_base
                    
                    if any("Escudo" in item for item in inv_limpo):
                        nova_ca += 2
                        nome_oficial_armadura += " & Escudo"
                        
                    jogador.modificador_defesa = nova_ca
                    if hasattr(jogador, 'armadura_equipada'): jogador.armadura_equipada = nome_oficial_armadura
                        
                resposta = f"🛡️ <b>Armadura Vestida!</b> Nova CA: <b>{jogador.modificador_defesa}</b>."

            await callback.message.answer(resposta, parse_mode="HTML")
            await callback.message.delete()
            await callback.answer("Equipado com sucesso!")

@router.message(Command("missoes", "quests"))
async def missoes_handler(message: types.Message):
    with get_db_session() as db:
        missoes = db.query(Missao).filter(Missao.jogador_telefone == str(message.from_user.id)).all()
        if not missoes:
            return await message.answer("📜 Não tens missões ativas no momento.", parse_mode="HTML")
        texto = "📜 <b>DIÁRIO DE MISSÕES</b>\n\n"
        for m in missoes:
            status = "✅ Concluída" if m.concluida else "⏳ Em andamento"
            texto += f"• <b>{m.titulo}</b> ({m.npc_nome})\n  └ <i>{m.descricao}</i>\n  └ Status: {status}\n\n"
        await message.answer(texto, parse_mode="HTML")

@router.message(Command("perfil", "hp", "ficha"))
async def perfil_handler(message: types.Message):
    with get_db_session() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == str(message.from_user.id)).first()
        if jogador:
            coracao = "❤️" if jogador.hp_atual > (jogador.hp_maximo / 2) else "⚠️"
            arma_eq = getattr(jogador, 'arma_equipada', 'Desarmado')
            armadura_eq = getattr(jogador, 'armadura_equipada', 'Trajes Comuns')
            
            pericias_bg = BACKGROUND_SKILLS.get(jogador.background, [])
            texto_pericias = ", ".join(pericias_bg) if pericias_bg else "Nenhuma"

            status_str = ""
            if hasattr(jogador, 'status_efeitos') and jogador.status_efeitos:
                status_str = f"\n⚠️ <b>Status Ativos:</b> {', '.join(jogador.status_efeitos)}"

            texto = (f"👤 <b>{jogador.nome}</b> (Nível {jogador.nivel} | {jogador.raca} {jogador.classe})\n"
                     f"<b>Background:</b> {jogador.background}\n"
                     f"🧠 <b>Perícias:</b> {texto_pericias} (+{jogador.proficiencia})\n"
                     f"━━━━━━━━━━━━━━━━━━━━\n"
                     f"{coracao} <b>HP:</b> {jogador.hp_atual}/{jogador.hp_maximo} | 🛡️ <b>CA:</b> {jogador.modificador_defesa} | ✨ <b>Usos:</b> {jogador.slots_magia}/{jogador.slots_magia_max}{status_str}\n"
                     f"🌟 <b>XP:</b> {jogador.xp}\n"
                     f"🎲 <b>Hit Dice:</b> {jogador.hit_dice_atual}/{getattr(jogador, 'hit_dice_max', 1)}\n"
                     f"━━━━━━━━━━━━━━━━━━━━\n"
                     f"⚔️ <b>Arma Ativa:</b> {arma_eq} ({jogador.dano_dado})\n"
                     f"🛡️ <b>Armadura Ativa:</b> {armadura_eq}\n"
                     f"━━━━━━━━━━━━━━━━━━━━\n"
                     f"<b>ATRIBUTOS:</b>\n"
                     f"STR: {jogador.str_val} ({jogador.mod_str:+d}) | DEX: {jogador.dex_val} ({jogador.mod_dex:+d})\n"
                     f"CON: {jogador.con_val} ({jogador.mod_con:+d}) | INT: {jogador.int_val} ({jogador.mod_int:+d})\n"
                     f"WIS: {jogador.wis_val} ({jogador.mod_wis:+d}) | CHA: {jogador.cha_val} ({jogador.mod_cha:+d})\n"
                     f"━━━━━━━━━━━━━━━━━━━━\n"
                     f"💰 <b>Ouro:</b> {jogador.gold} PO")
            await message.answer(texto, parse_mode="HTML")

@router.message(Command("dashboard", "stats", "estatisticas"))
async def dashboard_handler(message: types.Message):
    with get_db_session() as db:
        jogador = db.query(Jogador).filter(Jogador.telefone == str(message.from_user.id)).first()
        if not jogador: return await message.answer("⚠️ Use /criar para começar.")
        stats = get_or_create_estatisticas(db, str(message.from_user.id))
        rank = get_rank_jogador(db, str(message.from_user.id))
        ultimas_partidas = get_ultimas_partidas(db, str(message.from_user.id), limite=3)
        taxa_acerto = calcular_taxa_sucesso(stats)
        
        total_ataques = stats.total_ataques_acertados + stats.total_ataques_errados
        progresso = min(100, int(((jogador.xp - XP_POR_NIVEL.get(jogador.nivel, 0)) / (XP_POR_NIVEL.get(jogador.nivel + 1, 355000) - XP_POR_NIVEL.get(jogador.nivel, 0))) * 100)) if (XP_POR_NIVEL.get(jogador.nivel + 1, 355000) - XP_POR_NIVEL.get(jogador.nivel, 0)) > 0 else 100
        barras = int(progresso / 10)
        barra_progresso = "█" * barras + "░" * (10 - barras)
        texto = (f"📊 <b>DASHBOARD DE {jogador.nome.upper()}</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                 f"📈 <b>PROGRESSO</b>\nNível: {jogador.nivel}\nXP: {jogador.xp} [{barra_progresso}] {progresso}%\nOuro: {jogador.gold} PO\n\n"
                 f"🏆 <b>RANKING</b>\nPosição: #{rank['posicao']} de {rank['total_jogadores']}\n\n"
                 f"⚔️ <b>ESTATÍSTICAS</b>\nKills: {stats.inimigos_derrotados}\nAtaques: {stats.total_ataques_acertados}/{total_ataques} ({taxa_acerto:.1f}%)\nCríticos: {stats.criticos_acertados} | Dano: {stats.danos_causados_total}\n\n")
        if ultimas_partidas:
            texto += "📜 <b>HISTÓRICO</b>\n" + "".join([f"{'🏆' if p.resultado=='vitoria' else '💀'} {p.resultado.title()} - {p.inimigos_derrotados} kills\n" for p in ultimas_partidas])
        await message.answer(texto, parse_mode="HTML")